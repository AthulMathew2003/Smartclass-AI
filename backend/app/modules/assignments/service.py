import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.storage import S3StorageService
from app.modules.assignments.models import (
    Assignment,
    AssignmentAttachment,
    AssignmentStatus,
    AssignmentSubmission,
    SubmissionStatus,
    SubmissionAttachment
)
from app.modules.assignments.repository import AssignmentRepository
from app.modules.assignments.schemas import (
    AssignmentCreateRequest,
    AssignmentUpdateRequest,
    AssignmentResponse,
    SubmissionSummaryResponse,
    AttachmentUploadUrlRequest,
    AttachmentUploadUrlResponse,
    AttachmentConfirmRequest,
    AttachmentResponse,
    AttachmentDownloadUrlResponse,
    SubmissionResponse,
    SubmissionAttachmentResponse,
    SubmissionFileUploadUrlRequest,
    SubmissionFileUploadUrlResponse,
    SubmissionFileConfirmRequest,
    StudentSubmitRequest,
    GradeSubmissionRequest,
    ReturnSubmissionRequest
)
from app.modules.assignments.attachments import (
    validate_attachment_request,
    sanitize_filename,
    generate_attachment_s3_key,
    generate_submission_attachment_s3_key
)
from app.modules.users.models import User
from app.modules.subjects.models import Subject, SubjectStatus
from app.modules.organizations.models import Workspace, WorkspaceStatus
from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    ForbiddenException,
    StorageException,
    ValidationException
)


class AssignmentService:
    def __init__(self, db: AsyncSession, storage: Optional[S3StorageService] = None):
        self.db = db
        self.repo = AssignmentRepository(db)
        self.storage = storage or S3StorageService()

    # ── Hierarchy and Context Verification ──────────────────────

    async def _verify_subject_hierarchy(
        self,
        subject_id: uuid.UUID,
        org_id: uuid.UUID,
        allow_archived_parent: bool = False
    ) -> Tuple[Subject, Workspace]:
        """
        Verify that:
        1. The subject exists.
        2. The subject belongs to a workspace.
        3. The workspace belongs to the given active organization.
        4. Neither the subject nor the workspace is archived (unless allow_archived_parent is True).
        """
        subject = await self.repo.get_subject(subject_id)
        if not subject:
            raise NotFoundException("Subject not found.")

        if not allow_archived_parent and subject.subject_status == SubjectStatus.ARCHIVED:
            raise ConflictException("Subject is archived.")

        workspace = await self.repo.get_workspace(subject.subject_workspace_id)
        if not workspace or workspace.workspace_organization_id != org_id:
            raise NotFoundException("Subject not found in the current organization.")

        if not allow_archived_parent and workspace.workspace_status == WorkspaceStatus.ARCHIVED:
            raise ConflictException("Workspace is archived.")

        return subject, workspace

    async def _verify_assignment_hierarchy(
        self,
        assignment_id: uuid.UUID,
        org_id: uuid.UUID,
        allow_archived_parent: bool = False
    ) -> Tuple[Assignment, Subject, Workspace]:
        """
        Verify that:
        1. The assignment exists.
        2. The assignment's subject belongs to a workspace.
        3. The workspace belongs to the active organization.
        """
        assignment = await self.repo.get_assignment_by_id(assignment_id)
        if not assignment:
            raise NotFoundException("Assignment not found.")

        subject, workspace = await self._verify_subject_hierarchy(
            assignment.assignment_subject_id,
            org_id,
            allow_archived_parent=allow_archived_parent
        )
        return assignment, subject, workspace

    async def _verify_teacher_or_admin(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        workspace_id: uuid.UUID,
        is_org_admin: bool
    ) -> None:
        """
        Verify that the user is an Organization Owner/Admin OR an assigned teacher of the subject.
        """
        if is_org_admin:
            return

        is_ws_member = await self.repo.is_user_workspace_member(user_id, workspace_id)
        if not is_ws_member:
            raise ForbiddenException("Access denied. You are not a member of this workspace.")

        is_assigned_teacher = await self.repo.is_user_subject_teacher(subject_id, user_id)
        if not is_assigned_teacher:
            raise ForbiddenException("Access denied. You are not assigned to this subject.")

    async def _verify_workspace_access(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        is_org_admin: bool
    ) -> None:
        """
        Verify that the user is an Organization Owner/Admin OR a member of the workspace.
        """
        if is_org_admin:
            return

        is_ws_member = await self.repo.is_user_workspace_member(user_id, workspace_id)
        if not is_ws_member:
            raise ForbiddenException("Access denied. You are not a member of this workspace.")

    # ── Assignment CRUD Operations ──────────────────────────────

    async def create_assignment(
        self,
        org_id: uuid.UUID,
        created_by_user_id: uuid.UUID,
        is_org_admin: bool,
        payload: AssignmentCreateRequest
    ) -> AssignmentResponse:
        """Create a new assignment for a subject (starts as DRAFT)."""
        subject, workspace = await self._verify_subject_hierarchy(payload.subject_id, org_id)
        await self._verify_teacher_or_admin(
            created_by_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        title = payload.assignment_title.strip()
        if not title:
            raise ValidationException("Assignment title cannot be empty or whitespace only.")
        if len(title) > 255:
            raise ValidationException("Assignment title must be 255 characters or fewer.")

        now_utc = datetime.now(timezone.utc)
        if payload.assignment_due_at is not None:
            due_at = payload.assignment_due_at
            if due_at.tzinfo is None:
                due_at = due_at.replace(tzinfo=timezone.utc)
            if due_at < now_utc:
                raise ValidationException("Due date cannot be in the past when creating an assignment.")

        status = payload.assignment_status or AssignmentStatus.DRAFT
        assignment = await self.repo.create_assignment(
            subject_id=subject.subject_id,
            title=title,
            description=payload.assignment_description,
            status=status,
            due_at=payload.assignment_due_at,
            created_by=created_by_user_id
        )
        return AssignmentResponse.model_validate(assignment)

    async def list_assignments(
        self,
        org_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        subject_id: Optional[uuid.UUID] = None,
        workspace_id: Optional[uuid.UUID] = None,
        status_filter: Optional[AssignmentStatus] = None,
        search: Optional[str] = None
    ) -> List[AssignmentResponse]:
        """
        List accessible assignments.
        - If subject_id is supplied: list assignments for that specific subject.
        - If subject_id is omitted (Global View):
          - Teachers / Org Admins see assignments they are authorized to manage with aggregated submission metrics.
          - Students see published/closed assignments from all their enrolled workspaces with personal submission status.
        """
        if subject_id is not None:
            subject, workspace = await self._verify_subject_hierarchy(subject_id, org_id, allow_archived_parent=True)
            await self._verify_workspace_access(requesting_user_id, workspace.workspace_id, is_org_admin)

            is_teacher = is_org_admin or (await self.repo.is_user_subject_teacher(subject.subject_id, requesting_user_id))
            assignments = await self.repo.list_assignments_by_subject(
                subject_id=subject.subject_id,
                status_filter=status_filter,
                include_drafts=is_teacher,
                include_archived=is_teacher,
                search=search
            )

            responses = []
            for a in assignments:
                resp = AssignmentResponse.model_validate(a)
                resp.subject_name = subject.subject_name
                resp.workspace_id = workspace.workspace_id
                resp.workspace_name = workspace.workspace_name
                if is_teacher:
                    metrics = await self.repo.get_submission_metrics(a.assignment_id)
                    resp.submission_count = metrics["total"]
                    resp.graded_count = metrics["graded"]
                    resp.pending_count = metrics["pending"]
                else:
                    sub = await self.repo.get_submission(a.assignment_id, requesting_user_id)
                    if sub:
                        resp.student_submission = SubmissionSummaryResponse.model_validate(sub)
                responses.append(resp)
            return responses

        # Global list across organization
        is_teacher = (
            is_org_admin
            or (await self.repo.is_user_any_subject_teacher(org_id, requesting_user_id))
            or (await self.repo.is_user_teacher_or_admin_role(org_id, requesting_user_id))
        )
        is_teacher_or_admin = is_teacher

        if is_teacher:
            assignments = await self.repo.list_global_assignments_for_teacher_or_admin(
                org_id=org_id,
                user_id=requesting_user_id,
                is_org_admin=is_org_admin,
                status_filter=status_filter,
                workspace_id=workspace_id,
                search=search
            )
        else:
            assignments = await self.repo.list_global_assignments_for_student(
                org_id=org_id,
                user_id=requesting_user_id,
                status_filter=status_filter,
                workspace_id=workspace_id,
                search=search
            )

        responses = []
        for a in assignments:
            resp = AssignmentResponse.model_validate(a)
            if a.subject:
                resp.subject_name = a.subject.subject_name
                if a.subject.workspace:
                    resp.workspace_id = a.subject.workspace.workspace_id
                    resp.workspace_name = a.subject.workspace.workspace_name

            if is_teacher_or_admin:
                metrics = await self.repo.get_submission_metrics(a.assignment_id)
                resp.submission_count = metrics["total"]
                resp.graded_count = metrics["graded"]
                resp.pending_count = metrics["pending"]
            else:
                sub = await self.repo.get_submission(a.assignment_id, requesting_user_id)
                if sub:
                    resp.student_submission = SubmissionSummaryResponse.model_validate(sub)

            responses.append(resp)
        return responses

    async def get_assignment(
        self,
        org_id: uuid.UUID,
        assignment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        subject_id: Optional[uuid.UUID] = None
    ) -> AssignmentResponse:
        """
        Retrieve a single assignment.
        - Drafts and archived are invisible to students.
        """
        assignment, subject, workspace = await self._verify_assignment_hierarchy(
            assignment_id,
            org_id,
            allow_archived_parent=True
        )
        if subject_id is not None and subject.subject_id != subject_id:
            raise NotFoundException("Assignment not found for the specified subject.")

        await self._verify_workspace_access(requesting_user_id, workspace.workspace_id, is_org_admin)

        is_teacher = is_org_admin or (await self.repo.is_user_subject_teacher(subject.subject_id, requesting_user_id))

        if assignment.assignment_status in (AssignmentStatus.DRAFT, AssignmentStatus.ARCHIVED) and not is_teacher:
            raise NotFoundException("Assignment not found.")

        resp = AssignmentResponse.model_validate(assignment)
        resp.subject_name = subject.subject_name
        resp.workspace_id = workspace.workspace_id
        resp.workspace_name = workspace.workspace_name
        if is_teacher:
            metrics = await self.repo.get_submission_metrics(assignment.assignment_id)
            resp.submission_count = metrics["total"]
            resp.graded_count = metrics["graded"]
            resp.pending_count = metrics["pending"]
        else:
            sub = await self.repo.get_submission(assignment.assignment_id, requesting_user_id)
            if sub:
                resp.student_submission = SubmissionSummaryResponse.model_validate(sub)
        return resp

    async def update_assignment(
        self,
        org_id: uuid.UUID,
        assignment_id: uuid.UUID,
        payload: AssignmentUpdateRequest,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        subject_id: Optional[uuid.UUID] = None
    ) -> AssignmentResponse:
        """Update an existing assignment's metadata (title, description, due_at)."""
        assignment, subject, workspace = await self._verify_assignment_hierarchy(assignment_id, org_id)
        if subject_id is not None and subject.subject_id != subject_id:
            raise NotFoundException("Assignment not found for the specified subject.")

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        if assignment.assignment_status == AssignmentStatus.ARCHIVED:
            raise ConflictException("Archived assignments cannot be modified.")

        if assignment.assignment_status == AssignmentStatus.CLOSED:
            raise ConflictException("Closed assignments cannot be modified.")

        now_utc = datetime.now(timezone.utc)
        title = None
        if payload.assignment_title is not None:
            title = payload.assignment_title.strip()
            if not title:
                raise ValidationException("Assignment title cannot be empty or whitespace only.")
            if len(title) > 255:
                raise ValidationException("Assignment title must be 255 characters or fewer.")

        if payload.assignment_due_at is not None:
            due_at = payload.assignment_due_at
            if due_at.tzinfo is None:
                due_at = due_at.replace(tzinfo=timezone.utc)
            # When editing a published assignment, do not allow changing due_at to a past time
            if assignment.assignment_status == AssignmentStatus.PUBLISHED and due_at < now_utc:
                raise ValidationException("Cannot change due date to a past time for a published assignment.")

        updated = await self.repo.update_assignment(
            assignment=assignment,
            title=title,
            description=payload.assignment_description,
            due_at=payload.assignment_due_at
        )
        return AssignmentResponse.model_validate(updated)

    async def publish_assignment(
        self,
        org_id: uuid.UUID,
        assignment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        subject_id: Optional[uuid.UUID] = None
    ) -> AssignmentResponse:
        """Publish a DRAFT assignment (DRAFT -> PUBLISHED)."""
        assignment, subject, workspace = await self._verify_assignment_hierarchy(assignment_id, org_id)
        if subject_id is not None and subject.subject_id != subject_id:
            raise NotFoundException("Assignment not found for the specified subject.")

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        if assignment.assignment_status == AssignmentStatus.ARCHIVED:
            raise ConflictException("Archived assignments cannot be published.")

        if assignment.assignment_status == AssignmentStatus.PUBLISHED:
            raise ConflictException("Assignment is already published.")

        if assignment.assignment_status != AssignmentStatus.DRAFT:
            raise ConflictException(f"Cannot publish assignment with status '{assignment.assignment_status.value}'.")

        # Validate assignment data before publishing
        if not assignment.assignment_title or not assignment.assignment_title.strip():
            raise ValidationException("Cannot publish assignment without a valid title.")

        now_utc = datetime.now(timezone.utc)
        if assignment.assignment_due_at is not None:
            due_at = assignment.assignment_due_at
            if due_at.tzinfo is None:
                due_at = due_at.replace(tzinfo=timezone.utc)
            if due_at < now_utc:
                raise ValidationException("Cannot publish an assignment with a due date in the past.")

        published = await self.repo.set_assignment_status(assignment, AssignmentStatus.PUBLISHED)
        return AssignmentResponse.model_validate(published)

    async def close_assignment(
        self,
        org_id: uuid.UUID,
        assignment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        subject_id: Optional[uuid.UUID] = None
    ) -> AssignmentResponse:
        """Close an open assignment (PUBLISHED -> CLOSED)."""
        assignment, subject, workspace = await self._verify_assignment_hierarchy(assignment_id, org_id)
        if subject_id is not None and subject.subject_id != subject_id:
            raise NotFoundException("Assignment not found for the specified subject.")

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        if assignment.assignment_status == AssignmentStatus.ARCHIVED:
            raise ConflictException("Archived assignments cannot be closed.")

        if assignment.assignment_status == AssignmentStatus.CLOSED:
            raise ConflictException("Assignment is already closed.")

        if assignment.assignment_status != AssignmentStatus.PUBLISHED:
            raise ConflictException("Only published assignments can be closed.")

        closed = await self.repo.set_assignment_status(assignment, AssignmentStatus.CLOSED)
        return AssignmentResponse.model_validate(closed)

    async def delete_assignment(
        self,
        org_id: uuid.UUID,
        assignment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        subject_id: Optional[uuid.UUID] = None
    ) -> None:
        """Permanently delete (hard delete) an assignment, its S3 files, and all associated submissions."""
        assignment, subject, workspace = await self._verify_assignment_hierarchy(
            assignment_id,
            org_id,
            allow_archived_parent=True
        )
        if subject_id is not None and subject.subject_id != subject_id:
            raise NotFoundException("Assignment not found for the specified subject.")

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        # 1. Delete all assignment reference files in S3
        attachments = await self.repo.list_attachments_by_assignment(assignment.assignment_id)
        for att in attachments:
            try:
                self.storage.delete_object(att.attachment_s3_key)
            except Exception:
                pass

        # 2. Delete all submission files in S3
        submissions = await self.repo.list_submissions_by_assignment(assignment.assignment_id)
        for sub in submissions:
            if sub.attachments:
                for sub_att in sub.attachments:
                    try:
                        self.storage.delete_object(sub_att.attachment_s3_key)
                    except Exception:
                        pass

        # 3. Hard delete from database
        await self.repo.delete_assignment(assignment)

    async def archive_assignment(
        self,
        org_id: uuid.UUID,
        assignment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        subject_id: Optional[uuid.UUID] = None
    ) -> AssignmentResponse:
        """Soft-delete (archive) an assignment."""
        assignment, subject, workspace = await self._verify_assignment_hierarchy(assignment_id, org_id)
        if subject_id is not None and subject.subject_id != subject_id:
            raise NotFoundException("Assignment not found for the specified subject.")

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        if assignment.assignment_status == AssignmentStatus.ARCHIVED:
            raise ConflictException("Assignment is already archived.")

        archived = await self.repo.archive_assignment(assignment)
        return AssignmentResponse.model_validate(archived)

    # ── Teacher Assignment Attachment Operations ────────────────

    async def request_attachment_upload_url(
        self,
        org_id: uuid.UUID,
        assignment_id: uuid.UUID,
        payload: AttachmentUploadUrlRequest,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        subject_id: Optional[uuid.UUID] = None
    ) -> AttachmentUploadUrlResponse:
        assignment, subject, workspace = await self._verify_assignment_hierarchy(assignment_id, org_id)
        if subject_id is not None and subject.subject_id != subject_id:
            raise NotFoundException("Assignment not found for the specified subject.")

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        if assignment.assignment_status in (AssignmentStatus.ARCHIVED, AssignmentStatus.CLOSED):
            raise ConflictException("Cannot add attachments to closed or archived assignments.")

        count = await self.repo.count_assignment_attachments(assignment.assignment_id)
        if count >= settings.ASSIGNMENT_MAX_ATTACHMENTS_COUNT:
            raise ValidationException(f"Maximum of {settings.ASSIGNMENT_MAX_ATTACHMENTS_COUNT} attachments per assignment reached.")

        validate_attachment_request(payload.content_type, payload.file_size, payload.filename)

        attachment_id = uuid.uuid4()
        s3_key = generate_attachment_s3_key(assignment.assignment_id, attachment_id, payload.content_type)
        upload_url = self.storage.generate_upload_url(
            key=s3_key,
            content_type=payload.content_type.strip(),
            expires_in=900
        )

        return AttachmentUploadUrlResponse(
            attachment_id=attachment_id,
            s3_key=s3_key,
            upload_url=upload_url,
            expires_in=900
        )

    async def confirm_attachment_upload(
        self,
        org_id: uuid.UUID,
        assignment_id: uuid.UUID,
        payload: AttachmentConfirmRequest,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        subject_id: Optional[uuid.UUID] = None
    ) -> AttachmentResponse:
        assignment, subject, workspace = await self._verify_assignment_hierarchy(assignment_id, org_id)
        if subject_id is not None and subject.subject_id != subject_id:
            raise NotFoundException("Assignment not found for the specified subject.")

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        if assignment.assignment_status in (AssignmentStatus.ARCHIVED, AssignmentStatus.CLOSED):
            raise ConflictException("Cannot add attachments to closed or archived assignments.")

        expected_prefix = f"assignments/{assignment.assignment_id}/attachments/"
        if not payload.s3_key.startswith(expected_prefix):
            raise ValidationException("Invalid S3 key for this assignment.")

        validate_attachment_request(payload.content_type, payload.file_size, payload.original_filename)
        clean_filename = sanitize_filename(payload.original_filename)

        if not self.storage.object_exists(payload.s3_key):
            raise StorageException("Attachment file not found in storage. Upload may have failed or expired.")

        attachment = await self.repo.create_attachment(
            attachment_id=payload.attachment_id,
            assignment_id=assignment.assignment_id,
            s3_key=payload.s3_key,
            original_filename=clean_filename,
            content_type=payload.content_type.strip(),
            size=payload.file_size,
            created_by=requesting_user_id
        )
        return AttachmentResponse.model_validate(attachment)

    async def list_attachments(
        self,
        org_id: uuid.UUID,
        assignment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        subject_id: Optional[uuid.UUID] = None
    ) -> List[AttachmentResponse]:
        assignment, subject, workspace = await self._verify_assignment_hierarchy(
            assignment_id,
            org_id,
            allow_archived_parent=True
        )
        if subject_id is not None and subject.subject_id != subject_id:
            raise NotFoundException("Assignment not found for the specified subject.")

        await self._verify_workspace_access(requesting_user_id, workspace.workspace_id, is_org_admin)

        is_teacher = is_org_admin or (await self.repo.is_user_subject_teacher(subject.subject_id, requesting_user_id))
        if assignment.assignment_status in (AssignmentStatus.DRAFT, AssignmentStatus.ARCHIVED) and not is_teacher:
            raise NotFoundException("Assignment not found.")

        attachments = await self.repo.list_attachments_by_assignment(assignment.assignment_id)
        return [AttachmentResponse.model_validate(a) for a in attachments]

    async def get_attachment_download_url(
        self,
        org_id: uuid.UUID,
        assignment_id: uuid.UUID,
        attachment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        subject_id: Optional[uuid.UUID] = None
    ) -> AttachmentDownloadUrlResponse:
        assignment, subject, workspace = await self._verify_assignment_hierarchy(
            assignment_id,
            org_id,
            allow_archived_parent=True
        )
        if subject_id is not None and subject.subject_id != subject_id:
            raise NotFoundException("Assignment not found for the specified subject.")

        await self._verify_workspace_access(requesting_user_id, workspace.workspace_id, is_org_admin)

        is_teacher = is_org_admin or (await self.repo.is_user_subject_teacher(subject.subject_id, requesting_user_id))
        if assignment.assignment_status in (AssignmentStatus.DRAFT, AssignmentStatus.ARCHIVED) and not is_teacher:
            raise NotFoundException("Assignment not found.")

        attachment = await self.repo.get_attachment_by_id(attachment_id)
        if not attachment or attachment.attachment_assignment_id != assignment.assignment_id:
            raise NotFoundException("Attachment not found.")

        download_url = self.storage.generate_download_url(
            key=attachment.attachment_s3_key,
            expires_in=900
        )

        return AttachmentDownloadUrlResponse(
            attachment_id=attachment.attachment_id,
            original_filename=attachment.attachment_original_filename,
            download_url=download_url,
            expires_in=900
        )

    async def delete_attachment(
        self,
        org_id: uuid.UUID,
        assignment_id: uuid.UUID,
        attachment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        subject_id: Optional[uuid.UUID] = None
    ) -> None:
        assignment, subject, workspace = await self._verify_assignment_hierarchy(assignment_id, org_id)
        if subject_id is not None and subject.subject_id != subject_id:
            raise NotFoundException("Assignment not found for the specified subject.")

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        if assignment.assignment_status in (AssignmentStatus.ARCHIVED, AssignmentStatus.CLOSED):
            raise ConflictException("Cannot modify attachments for closed or archived assignments.")

        attachment = await self.repo.get_attachment_by_id(attachment_id)
        if not attachment or attachment.attachment_assignment_id != assignment.assignment_id:
            raise NotFoundException("Attachment not found.")

        try:
            self.storage.delete_object(attachment.attachment_s3_key)
        except Exception:
            pass

        await self.repo.delete_attachment(attachment)

    # ── Student Submission & Multi-Version Resubmission ─────────

    async def submit_assignment(
        self,
        org_id: uuid.UUID,
        assignment_id: uuid.UUID,
        student_id: uuid.UUID,
        payload: StudentSubmitRequest,
        is_org_admin: bool = False
    ) -> SubmissionResponse:
        """
        Submit or resubmit an assignment.
        - Verifies workspace membership and assignment visibility.
        - Rejects submissions to draft/archived/closed assignments.
        - Calculates status (submitted vs late).
        """
        assignment, subject, workspace = await self._verify_assignment_hierarchy(assignment_id, org_id)
        await self._verify_workspace_access(student_id, workspace.workspace_id, is_org_admin)

        if assignment.assignment_status in (AssignmentStatus.DRAFT, AssignmentStatus.ARCHIVED):
            raise NotFoundException("Assignment not found.")

        if assignment.assignment_status == AssignmentStatus.CLOSED:
            raise ConflictException("Submissions are closed for this assignment.")

        now_utc = datetime.now(timezone.utc)
        sub_status = SubmissionStatus.SUBMITTED
        if assignment.assignment_due_at is not None:
            due_at = assignment.assignment_due_at
            if due_at.tzinfo is None:
                due_at = due_at.replace(tzinfo=timezone.utc)
            if now_utc > due_at:
                sub_status = SubmissionStatus.LATE

        # Check existing submission
        existing_sub = await self.repo.get_submission(assignment.assignment_id, student_id)

        if existing_sub is None:
            # Initial submission
            submission = await self.repo.create_submission(
                assignment_id=assignment.assignment_id,
                student_id=student_id,
                status=sub_status,
                submitted_at=now_utc
            )
        else:
            # Resubmission / Replacement: delete old S3 objects and DB attachment rows
            if existing_sub.attachments:
                for old_att in list(existing_sub.attachments):
                    try:
                        self.storage.delete_object(old_att.attachment_s3_key)
                    except Exception:
                        pass
                    await self.db.delete(old_att)
                existing_sub.attachments.clear()

            existing_sub.submission_status = sub_status
            existing_sub.submission_submitted_at = now_utc
            # Reset active grading state on new submission
            existing_sub.submission_grade = None
            existing_sub.submission_feedback = None
            existing_sub.submission_graded_by = None
            existing_sub.submission_graded_at = None
            self.db.add(existing_sub)
            await self.db.flush()
            submission = existing_sub

        # Attach confirmed new files directly to this submission
        if payload.files:
            if len(payload.files) > settings.ASSIGNMENT_MAX_ATTACHMENTS_COUNT:
                raise ValidationException(f"Cannot attach more than {settings.ASSIGNMENT_MAX_ATTACHMENTS_COUNT} files.")

            for f in payload.files:
                validate_attachment_request(f.content_type, f.file_size, f.original_filename)
                clean_name = sanitize_filename(f.original_filename)
                expected_prefix = f"submissions/{assignment.assignment_id}/{student_id}/"
                if not f.s3_key.startswith(expected_prefix):
                    raise ValidationException("Invalid S3 key for this submission.")

                if not self.storage.object_exists(f.s3_key):
                    raise StorageException(f"Submission file '{clean_name}' not found in storage.")

                await self.repo.create_submission_attachment(
                    attachment_id=f.attachment_id,
                    submission_id=submission.submission_id,
                    s3_key=f.s3_key,
                    original_filename=clean_name,
                    content_type=f.content_type.strip(),
                    size=f.file_size
                )

        await self.db.flush()
        # Fetch refreshed submission with attachments
        refreshed = await self.repo.get_submission(assignment.assignment_id, student_id)
        return await self._format_submission_response(refreshed or submission)

    async def request_submission_file_upload_url(
        self,
        org_id: uuid.UUID,
        assignment_id: uuid.UUID,
        student_id: uuid.UUID,
        payload: SubmissionFileUploadUrlRequest,
        is_org_admin: bool = False
    ) -> SubmissionFileUploadUrlResponse:
        """
        Request a presigned upload URL for a student submission file.
        """
        assignment, subject, workspace = await self._verify_assignment_hierarchy(assignment_id, org_id)
        await self._verify_workspace_access(student_id, workspace.workspace_id, is_org_admin)

        if assignment.assignment_status in (AssignmentStatus.DRAFT, AssignmentStatus.ARCHIVED):
            raise NotFoundException("Assignment not found.")

        if assignment.assignment_status == AssignmentStatus.CLOSED:
            raise ConflictException("Submissions are closed for this assignment.")

        validate_attachment_request(payload.content_type, payload.file_size, payload.filename)

        attachment_id = uuid.uuid4()
        s3_key = generate_submission_attachment_s3_key(
            assignment_id=assignment.assignment_id,
            student_id=student_id,
            attachment_id=attachment_id,
            content_type=payload.content_type
        )

        upload_url = self.storage.generate_upload_url(
            key=s3_key,
            content_type=payload.content_type.strip(),
            expires_in=900
        )

        return SubmissionFileUploadUrlResponse(
            attachment_id=attachment_id,
            s3_key=s3_key,
            upload_url=upload_url,
            expires_in=900
        )

    async def get_submission(
        self,
        org_id: uuid.UUID,
        assignment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        target_student_id: Optional[uuid.UUID] = None
    ) -> Optional[SubmissionResponse]:
        """
        Get submission details.
        - Students can only view their own submission.
        - Teachers / Org Admins can view any student's submission via target_student_id.
        """
        assignment, subject, workspace = await self._verify_assignment_hierarchy(
            assignment_id,
            org_id,
            allow_archived_parent=True
        )
        await self._verify_workspace_access(requesting_user_id, workspace.workspace_id, is_org_admin)

        is_teacher = is_org_admin or (await self.repo.is_user_subject_teacher(subject.subject_id, requesting_user_id))

        if target_student_id is not None and target_student_id != requesting_user_id:
            if not is_teacher:
                raise ForbiddenException("Access denied. You cannot view another student's submission.")
            student_id = target_student_id
        else:
            student_id = requesting_user_id

        if assignment.assignment_status in (AssignmentStatus.DRAFT, AssignmentStatus.ARCHIVED) and not is_teacher:
            raise NotFoundException("Assignment not found.")

        sub = await self.repo.get_submission(assignment.assignment_id, student_id)
        if not sub:
            return None
        return await self._format_submission_response(sub)

    async def list_submissions_for_teacher(
        self,
        org_id: uuid.UUID,
        assignment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> List[SubmissionResponse]:
        """
        List all student submissions for an assignment (Teachers & Org Admins only).
        """
        assignment, subject, workspace = await self._verify_assignment_hierarchy(
            assignment_id,
            org_id,
            allow_archived_parent=True
        )
        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        submissions = await self.repo.list_submissions_by_assignment(assignment.assignment_id)
        resps = []
        for s in submissions:
            resps.append(await self._format_submission_response(s))
        return resps

    async def get_submission_attachment_download_url(
        self,
        org_id: uuid.UUID,
        assignment_id: uuid.UUID,
        attachment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> AttachmentDownloadUrlResponse:
        """
        Generate presigned download URL for a student submission attachment.
        - Authorized only for the submitting student OR assigned teacher / Org Admin.
        """
        assignment, subject, workspace = await self._verify_assignment_hierarchy(
            assignment_id,
            org_id,
            allow_archived_parent=True
        )
        await self._verify_workspace_access(requesting_user_id, workspace.workspace_id, is_org_admin)

        attachment = await self.repo.get_submission_attachment_by_id(attachment_id)
        if not attachment:
            raise NotFoundException("Submission attachment not found.")

        # Verify submission ownership
        submission = attachment.submission
        if not submission or submission.submission_assignment_id != assignment.assignment_id:
            raise NotFoundException("Submission attachment not found.")

        is_teacher = is_org_admin or (await self.repo.is_user_subject_teacher(subject.subject_id, requesting_user_id))
        is_owner = submission.submission_student_id == requesting_user_id

        if not is_teacher and not is_owner:
            raise ForbiddenException("Access denied. You cannot access another student's submission files.")

        download_url = self.storage.generate_download_url(
            key=attachment.attachment_s3_key,
            expires_in=900
        )

        return AttachmentDownloadUrlResponse(
            attachment_id=attachment.attachment_id,
            original_filename=attachment.attachment_original_filename,
            download_url=download_url,
            expires_in=900
        )

    # ── Teacher Grading Operations ──────────────────────────────

    async def grade_submission(
        self,
        org_id: uuid.UUID,
        assignment_id: uuid.UUID,
        submission_id: uuid.UUID,
        payload: GradeSubmissionRequest,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> SubmissionResponse:
        """Grade a student submission."""
        assignment, subject, workspace = await self._verify_assignment_hierarchy(assignment_id, org_id)
        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        submission = await self.repo.get_submission_by_id(submission_id)
        if not submission or submission.submission_assignment_id != assignment.assignment_id:
            raise NotFoundException("Submission not found.")

        if payload.grade < 0 or payload.grade > 100:
            raise ValidationException("Grade must be between 0 and 100.")

        now_utc = datetime.now(timezone.utc)
        submission.submission_grade = payload.grade
        submission.submission_feedback = payload.feedback
        submission.submission_status = SubmissionStatus.GRADED
        submission.submission_graded_by = requesting_user_id
        submission.submission_graded_at = now_utc
        self.db.add(submission)

        await self.db.flush()
        return await self._format_submission_response(submission)

    async def return_submission(
        self,
        org_id: uuid.UUID,
        assignment_id: uuid.UUID,
        submission_id: uuid.UUID,
        payload: ReturnSubmissionRequest,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> SubmissionResponse:
        """Return a student submission."""
        assignment, subject, workspace = await self._verify_assignment_hierarchy(assignment_id, org_id)
        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        submission = await self.repo.get_submission_by_id(submission_id)
        if not submission or submission.submission_assignment_id != assignment.assignment_id:
            raise NotFoundException("Submission not found.")

        now_utc = datetime.now(timezone.utc)
        submission.submission_status = SubmissionStatus.RETURNED
        if payload.feedback:
            submission.submission_feedback = payload.feedback
        self.db.add(submission)

        await self.db.flush()
        return await self._format_submission_response(submission)

    async def _format_submission_response(
        self,
        sub: AssignmentSubmission
    ) -> SubmissionResponse:
        """Helper to format full submission with attachments."""
        att_resps = []
        if sub.attachments:
            for a in sub.attachments:
                att_resps.append(SubmissionAttachmentResponse(
                    attachment_id=a.attachment_id,
                    submission_id=a.attachment_submission_id,
                    original_filename=a.attachment_original_filename,
                    content_type=a.attachment_content_type,
                    size=a.attachment_size,
                    created_at=a.attachment_created_at
                ))

        student_name = None
        student_email = None
        if "student" in sub.__dict__ and sub.student:
            student_name = f"{sub.student.user_first_name} {sub.student.user_last_name}".strip()
            student_email = sub.student.user_email
        elif sub.submission_student_id:
            user = await self.db.get(User, sub.submission_student_id)
            if user:
                student_name = f"{user.user_first_name} {user.user_last_name}".strip()
                student_email = user.user_email

        return SubmissionResponse(
            submission_id=sub.submission_id,
            submission_assignment_id=sub.submission_assignment_id,
            submission_student_id=sub.submission_student_id,
            submission_status=sub.submission_status,
            submission_submitted_at=sub.submission_submitted_at,
            submission_grade=float(sub.submission_grade) if sub.submission_grade is not None else None,
            submission_feedback=sub.submission_feedback,
            submission_graded_by=sub.submission_graded_by,
            submission_graded_at=sub.submission_graded_at,
            submission_created_at=sub.submission_created_at,
            submission_updated_at=sub.submission_updated_at,
            student_name=student_name,
            student_email=student_email,
            attachments=att_resps
        )
