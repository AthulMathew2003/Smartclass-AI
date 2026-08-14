import uuid
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assignments.models import Assignment, AssignmentStatus
from app.modules.assignments.repository import AssignmentRepository
from app.modules.assignments.schemas import (
    AssignmentCreateRequest,
    AssignmentUpdateRequest,
    AssignmentResponse
)
from app.modules.subjects.models import Subject, SubjectStatus
from app.modules.organizations.models import Workspace, WorkspaceStatus
from app.core.exceptions import ConflictException, NotFoundException, ForbiddenException


class AssignmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AssignmentRepository(db)

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

        # Check if the user is a workspace member
        is_ws_member = await self.repo.is_user_workspace_member(user_id, workspace_id)
        if not is_ws_member:
            raise ForbiddenException("Access denied. You are not a member of this workspace.")

        # Check if the user is assigned to the subject
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

    # ── Assignment Operations ───────────────────────────────────

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

        status = payload.assignment_status or AssignmentStatus.DRAFT
        assignment = await self.repo.create_assignment(
            subject_id=subject.subject_id,
            title=payload.assignment_title.strip(),
            description=payload.assignment_description,
            status=status,
            due_at=payload.assignment_due_at,
            created_by=created_by_user_id
        )
        return AssignmentResponse.model_validate(assignment)

    async def list_assignments(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        status_filter: Optional[AssignmentStatus] = None
    ) -> List[AssignmentResponse]:
        """
        List assignments for a subject.
        - Teachers & Org Admins see all assignments including DRAFT and ARCHIVED (or filtered).
        - Students / non-teachers see only published and closed assignments.
        """
        subject, workspace = await self._verify_subject_hierarchy(subject_id, org_id, allow_archived_parent=True)
        await self._verify_workspace_access(requesting_user_id, workspace.workspace_id, is_org_admin)

        is_teacher = is_org_admin or (await self.repo.is_user_subject_teacher(subject.subject_id, requesting_user_id))
        assignments = await self.repo.list_assignments_by_subject(
            subject_id=subject.subject_id,
            status_filter=status_filter,
            include_drafts=is_teacher,
            include_archived=is_teacher
        )
        return [AssignmentResponse.model_validate(a) for a in assignments]

    async def get_assignment(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        assignment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> AssignmentResponse:
        """
        Retrieve a single assignment.
        - Drafts and archived are invisible to students / non-teachers.
        """
        subject, workspace = await self._verify_subject_hierarchy(subject_id, org_id, allow_archived_parent=True)
        await self._verify_workspace_access(requesting_user_id, workspace.workspace_id, is_org_admin)

        assignment = await self.repo.get_assignment_by_id(assignment_id)
        if not assignment or assignment.assignment_subject_id != subject.subject_id:
            raise NotFoundException("Assignment not found.")

        is_teacher = is_org_admin or (await self.repo.is_user_subject_teacher(subject.subject_id, requesting_user_id))

        if assignment.assignment_status in (AssignmentStatus.DRAFT, AssignmentStatus.ARCHIVED) and not is_teacher:
            raise NotFoundException("Assignment not found.")

        return AssignmentResponse.model_validate(assignment)

    async def update_assignment(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        assignment_id: uuid.UUID,
        payload: AssignmentUpdateRequest,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> AssignmentResponse:
        """Update an existing assignment's metadata (title, description, due_at)."""
        subject, workspace = await self._verify_subject_hierarchy(subject_id, org_id)
        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        assignment = await self.repo.get_assignment_by_id(assignment_id)
        if not assignment or assignment.assignment_subject_id != subject.subject_id:
            raise NotFoundException("Assignment not found.")

        if assignment.assignment_status == AssignmentStatus.ARCHIVED:
            raise ConflictException("Archived assignments cannot be modified.")

        title = payload.assignment_title.strip() if payload.assignment_title is not None else None
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
        subject_id: uuid.UUID,
        assignment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> AssignmentResponse:
        """Publish a DRAFT assignment (DRAFT -> PUBLISHED)."""
        subject, workspace = await self._verify_subject_hierarchy(subject_id, org_id)
        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        assignment = await self.repo.get_assignment_by_id(assignment_id)
        if not assignment or assignment.assignment_subject_id != subject.subject_id:
            raise NotFoundException("Assignment not found.")

        if assignment.assignment_status == AssignmentStatus.ARCHIVED:
            raise ConflictException("Archived assignments cannot be published.")

        if assignment.assignment_status == AssignmentStatus.PUBLISHED:
            raise ConflictException("Assignment is already published.")

        if assignment.assignment_status != AssignmentStatus.DRAFT:
            raise ConflictException(f"Cannot publish assignment with status '{assignment.assignment_status.value}'.")

        published = await self.repo.set_assignment_status(assignment, AssignmentStatus.PUBLISHED)
        return AssignmentResponse.model_validate(published)

    async def close_assignment(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        assignment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> AssignmentResponse:
        """Close an open assignment (PUBLISHED -> CLOSED)."""
        subject, workspace = await self._verify_subject_hierarchy(subject_id, org_id)
        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        assignment = await self.repo.get_assignment_by_id(assignment_id)
        if not assignment or assignment.assignment_subject_id != subject.subject_id:
            raise NotFoundException("Assignment not found.")

        if assignment.assignment_status == AssignmentStatus.ARCHIVED:
            raise ConflictException("Archived assignments cannot be closed.")

        if assignment.assignment_status == AssignmentStatus.CLOSED:
            raise ConflictException("Assignment is already closed.")

        if assignment.assignment_status != AssignmentStatus.PUBLISHED:
            raise ConflictException("Only published assignments can be closed.")

        closed = await self.repo.set_assignment_status(assignment, AssignmentStatus.CLOSED)
        return AssignmentResponse.model_validate(closed)

    async def archive_assignment(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        assignment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> AssignmentResponse:
        """Soft-delete (archive) an assignment."""
        subject, workspace = await self._verify_subject_hierarchy(subject_id, org_id)
        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        assignment = await self.repo.get_assignment_by_id(assignment_id)
        if not assignment or assignment.assignment_subject_id != subject.subject_id:
            raise NotFoundException("Assignment not found.")

        if assignment.assignment_status == AssignmentStatus.ARCHIVED:
            raise ConflictException("Assignment is already archived.")

        archived = await self.repo.archive_assignment(assignment)
        return AssignmentResponse.model_validate(archived)
