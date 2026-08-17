import uuid
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, delete, and_, or_, exists, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.modules.assignments.models import (
    Assignment,
    AssignmentAttachment,
    AssignmentStatus,
    AssignmentSubmission,
    SubmissionStatus,
    SubmissionAttachment
)
from app.modules.subjects.models import Subject, SubjectTeacher, SubjectStatus
from app.modules.organizations.models import (
    Workspace,
    WorkspaceMember,
    WorkspaceStatus,
    OrganizationMember,
    OrganizationMemberStatus,
    Role
)
from app.modules.users.models import User


class AssignmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Assignment CRUD ─────────────────────────────────────────

    async def create_assignment(
        self,
        subject_id: uuid.UUID,
        title: str,
        description: Optional[str],
        status: AssignmentStatus,
        due_at: Optional[datetime],
        created_by: Optional[uuid.UUID]
    ) -> Assignment:
        assignment = Assignment(
            assignment_subject_id=subject_id,
            assignment_title=title,
            assignment_description=description,
            assignment_status=status,
            assignment_due_at=due_at,
            assignment_created_by=created_by
        )
        self.db.add(assignment)
        try:
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            raise e
        return assignment

    async def get_assignment_by_id(self, assignment_id: uuid.UUID) -> Optional[Assignment]:
        stmt = (
            select(Assignment)
            .where(Assignment.assignment_id == assignment_id)
            .options(selectinload(Assignment.subject))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_assignments_by_subject(
        self,
        subject_id: uuid.UUID,
        status_filter: Optional[AssignmentStatus] = None,
        include_drafts: bool = True,
        include_archived: bool = False
    ) -> List[Assignment]:
        stmt = (
            select(Assignment)
            .where(Assignment.assignment_subject_id == subject_id)
            .options(selectinload(Assignment.subject))
        )

        if status_filter is not None:
            if status_filter == AssignmentStatus.DRAFT and not include_drafts:
                return []
            if status_filter == AssignmentStatus.ARCHIVED and not include_archived:
                return []
            stmt = stmt.where(Assignment.assignment_status == status_filter)
        else:
            if not include_drafts:
                stmt = stmt.where(Assignment.assignment_status != AssignmentStatus.DRAFT)
            if not include_archived:
                stmt = stmt.where(Assignment.assignment_status != AssignmentStatus.ARCHIVED)

        stmt = stmt.order_by(Assignment.assignment_created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_assignment(
        self,
        assignment: Assignment,
        title: Optional[str] = None,
        description: Optional[str] = None,
        due_at: Optional[datetime] = None
    ) -> Assignment:
        if title is not None:
            assignment.assignment_title = title
        if description is not None:
            assignment.assignment_description = description
        if due_at is not None:
            assignment.assignment_due_at = due_at

        self.db.add(assignment)
        try:
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            raise e
        return assignment

    async def set_assignment_status(self, assignment: Assignment, status: AssignmentStatus) -> Assignment:
        assignment.assignment_status = status
        self.db.add(assignment)
        await self.db.flush()
        return assignment

    async def archive_assignment(self, assignment: Assignment) -> Assignment:
        assignment.assignment_status = AssignmentStatus.ARCHIVED
        self.db.add(assignment)
        await self.db.flush()
        return assignment

    # ── Global Assignment Listing ───────────────────────────────

    async def list_global_assignments_for_teacher_or_admin(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        is_org_admin: bool,
        status_filter: Optional[AssignmentStatus] = None
    ) -> List[Assignment]:
        """
        List all assignments accessible to an Admin or Teacher across an organization.
        - Org Admin sees all assignments across all workspaces/subjects in the org.
        - Teacher sees assignments for subjects they are assigned to (or subjects in their workspaces).
        """
        stmt = (
            select(Assignment)
            .join(Subject, Assignment.assignment_subject_id == Subject.subject_id)
            .join(Workspace, Subject.subject_workspace_id == Workspace.workspace_id)
            .where(
                Workspace.workspace_organization_id == org_id,
                Workspace.workspace_status != WorkspaceStatus.ARCHIVED,
                Subject.subject_status != SubjectStatus.ARCHIVED
            )
            .options(
                selectinload(Assignment.subject).selectinload(Subject.workspace)
            )
        )

        if not is_org_admin:
            # Filter by subjects where user is assigned teacher OR workspace member
            is_teacher_subquery = exists().where(
                and_(
                    SubjectTeacher.subject_teacher_subject_id == Subject.subject_id,
                    SubjectTeacher.subject_teacher_user_id == user_id
                )
            )
            stmt = stmt.where(is_teacher_subquery)

        if status_filter is not None:
            stmt = stmt.where(Assignment.assignment_status == status_filter)

        stmt = stmt.order_by(Assignment.assignment_created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_global_assignments_for_student(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        status_filter: Optional[AssignmentStatus] = None
    ) -> List[Assignment]:
        """
        List all published and closed assignments for a student across all their enrolled workspaces.
        Drafts and archived assignments are completely excluded.
        """
        stmt = (
            select(Assignment)
            .join(Subject, Assignment.assignment_subject_id == Subject.subject_id)
            .join(Workspace, Subject.subject_workspace_id == Workspace.workspace_id)
            .where(
                Workspace.workspace_organization_id == org_id,
                Workspace.workspace_status == WorkspaceStatus.ACTIVE,
                Subject.subject_status == SubjectStatus.ACTIVE,
                Assignment.assignment_status.in_([AssignmentStatus.PUBLISHED, AssignmentStatus.CLOSED]),
                or_(
                    exists().where(
                        and_(
                            WorkspaceMember.workspace_member_workspace_id == Workspace.workspace_id,
                            WorkspaceMember.workspace_member_user_id == user_id
                        )
                    ),
                    exists().where(
                        and_(
                            OrganizationMember.organization_member_organization_id == org_id,
                            OrganizationMember.organization_member_user_id == user_id,
                            OrganizationMember.organization_member_status == OrganizationMemberStatus.ACTIVE
                        )
                    )
                )
            )
            .options(
                selectinload(Assignment.subject).selectinload(Subject.workspace)
            )
        )

        if status_filter is not None:
            if status_filter in (AssignmentStatus.PUBLISHED, AssignmentStatus.CLOSED):
                stmt = stmt.where(Assignment.assignment_status == status_filter)
            else:
                return []

        stmt = stmt.order_by(Assignment.assignment_due_at.asc().nulls_last(), Assignment.assignment_created_at.desc())
        result = await self.db.execute(stmt)
        # Deduplicate if joins produce duplicates
        seen = set()
        deduped = []
        for a in result.scalars().all():
            if a.assignment_id not in seen:
                seen.add(a.assignment_id)
                deduped.append(a)
        return deduped

    # ── Assignment Attachments ──────────────────────────────────

    async def create_attachment(
        self,
        attachment_id: uuid.UUID,
        assignment_id: uuid.UUID,
        s3_key: str,
        original_filename: str,
        content_type: str,
        size: int,
        created_by: Optional[uuid.UUID]
    ) -> AssignmentAttachment:
        attachment = AssignmentAttachment(
            attachment_id=attachment_id,
            attachment_assignment_id=assignment_id,
            attachment_s3_key=s3_key,
            attachment_original_filename=original_filename,
            attachment_content_type=content_type,
            attachment_size=size,
            attachment_created_by=created_by
        )
        self.db.add(attachment)
        try:
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            raise e
        return attachment

    async def get_attachment_by_id(self, attachment_id: uuid.UUID) -> Optional[AssignmentAttachment]:
        stmt = select(AssignmentAttachment).where(AssignmentAttachment.attachment_id == attachment_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_attachments_by_assignment(self, assignment_id: uuid.UUID) -> List[AssignmentAttachment]:
        stmt = (
            select(AssignmentAttachment)
            .where(AssignmentAttachment.attachment_assignment_id == assignment_id)
            .order_by(AssignmentAttachment.attachment_created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_assignment_attachments(self, assignment_id: uuid.UUID) -> int:
        stmt = (
            select(func.count(AssignmentAttachment.attachment_id))
            .where(AssignmentAttachment.attachment_assignment_id == assignment_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def delete_attachment(self, attachment: AssignmentAttachment) -> None:
        await self.db.delete(attachment)
        await self.db.flush()

    # ── Student Submissions & Attachments ───────────────────────

    async def get_submission(
        self,
        assignment_id: uuid.UUID,
        student_id: uuid.UUID
    ) -> Optional[AssignmentSubmission]:
        stmt = (
            select(AssignmentSubmission)
            .where(
                AssignmentSubmission.submission_assignment_id == assignment_id,
                AssignmentSubmission.submission_student_id == student_id
            )
            .options(
                selectinload(AssignmentSubmission.attachments),
                selectinload(AssignmentSubmission.student),
                selectinload(AssignmentSubmission.grader)
            )
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_submission_by_id(self, submission_id: uuid.UUID) -> Optional[AssignmentSubmission]:
        stmt = (
            select(AssignmentSubmission)
            .where(AssignmentSubmission.submission_id == submission_id)
            .options(
                selectinload(AssignmentSubmission.attachments),
                selectinload(AssignmentSubmission.student),
                selectinload(AssignmentSubmission.grader),
                selectinload(AssignmentSubmission.assignment)
            )
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_submissions_by_assignment(self, assignment_id: uuid.UUID) -> List[AssignmentSubmission]:
        stmt = (
            select(AssignmentSubmission)
            .where(AssignmentSubmission.submission_assignment_id == assignment_id)
            .options(
                selectinload(AssignmentSubmission.attachments),
                selectinload(AssignmentSubmission.student),
                selectinload(AssignmentSubmission.grader)
            )
            .order_by(AssignmentSubmission.submission_created_at.desc())
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_submission(
        self,
        assignment_id: uuid.UUID,
        student_id: uuid.UUID,
        status: SubmissionStatus,
        submitted_at: Optional[datetime]
    ) -> AssignmentSubmission:
        submission = AssignmentSubmission(
            submission_assignment_id=assignment_id,
            submission_student_id=student_id,
            submission_status=status,
            submission_submitted_at=submitted_at
        )
        self.db.add(submission)
        try:
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            raise e
        return submission

    async def create_submission_attachment(
        self,
        attachment_id: uuid.UUID,
        submission_id: uuid.UUID,
        s3_key: str,
        original_filename: str,
        content_type: str,
        size: int
    ) -> SubmissionAttachment:
        att = SubmissionAttachment(
            attachment_id=attachment_id,
            attachment_submission_id=submission_id,
            attachment_s3_key=s3_key,
            attachment_original_filename=original_filename,
            attachment_content_type=content_type,
            attachment_size=size
        )
        self.db.add(att)
        try:
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            raise e
        return att

    async def list_submission_attachments(self, submission_id: uuid.UUID) -> List[SubmissionAttachment]:
        stmt = (
            select(SubmissionAttachment)
            .where(SubmissionAttachment.attachment_submission_id == submission_id)
            .order_by(SubmissionAttachment.attachment_created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_submission_attachments_by_submission(self, submission_id: uuid.UUID) -> None:
        stmt = delete(SubmissionAttachment).where(SubmissionAttachment.attachment_submission_id == submission_id)
        await self.db.execute(stmt)
        await self.db.flush()

    async def get_submission_attachment_by_id(self, attachment_id: uuid.UUID) -> Optional[SubmissionAttachment]:
        stmt = (
            select(SubmissionAttachment)
            .where(SubmissionAttachment.attachment_id == attachment_id)
            .options(
                selectinload(SubmissionAttachment.submission)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def count_submission_attachments(self, submission_id: uuid.UUID) -> int:
        stmt = (
            select(func.count(SubmissionAttachment.attachment_id))
            .where(SubmissionAttachment.attachment_submission_id == submission_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_submission_metrics(self, assignment_id: uuid.UUID) -> Dict[str, int]:
        """
        Compute total submissions, graded count, and pending grading count.
        """
        stmt = (
            select(
                func.count(AssignmentSubmission.submission_id).label("total"),
                func.count(AssignmentSubmission.submission_id).filter(
                    AssignmentSubmission.submission_status == SubmissionStatus.GRADED
                ).label("graded"),
                func.count(AssignmentSubmission.submission_id).filter(
                    AssignmentSubmission.submission_status.in_([SubmissionStatus.SUBMITTED, SubmissionStatus.LATE])
                ).label("pending")
            )
            .where(AssignmentSubmission.submission_assignment_id == assignment_id)
        )
        result = await self.db.execute(stmt)
        row = result.first()
        if row:
            return {
                "total": row.total or 0,
                "graded": row.graded or 0,
                "pending": row.pending or 0
            }
        return {"total": 0, "graded": 0, "pending": 0}

    # ── Hierarchy and Authorization Lookups ─────────────────────

    async def get_subject(self, subject_id: uuid.UUID) -> Optional[Subject]:
        stmt = select(Subject).where(Subject.subject_id == subject_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_workspace(self, workspace_id: uuid.UUID) -> Optional[Workspace]:
        stmt = select(Workspace).where(Workspace.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def is_user_subject_teacher(self, subject_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        stmt = select(exists().where(
            and_(
                SubjectTeacher.subject_teacher_subject_id == subject_id,
                SubjectTeacher.subject_teacher_user_id == user_id
            )
        ))
        result = await self.db.execute(stmt)
        return bool(result.scalar())

    async def is_user_workspace_member(self, user_id: uuid.UUID, workspace_id: uuid.UUID) -> bool:
        stmt = select(exists().where(
            and_(
                WorkspaceMember.workspace_member_workspace_id == workspace_id,
                WorkspaceMember.workspace_member_user_id == user_id
            )
        ))
        result = await self.db.execute(stmt)
        return bool(result.scalar())

    async def is_user_org_admin(self, user_id: uuid.UUID, org_id: uuid.UUID) -> bool:
        stmt = (
            select(OrganizationMember)
            .join(Role, OrganizationMember.organization_member_role_id == Role.role_id)
            .where(
                OrganizationMember.organization_member_organization_id == org_id,
                OrganizationMember.organization_member_user_id == user_id,
                OrganizationMember.organization_member_status == OrganizationMemberStatus.ACTIVE,
                Role.role_name.in_(["Owner", "Admin"])
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first() is not None

    async def is_user_any_subject_teacher(self, org_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        stmt = select(exists().where(
            and_(
                SubjectTeacher.subject_teacher_user_id == user_id,
                SubjectTeacher.subject_teacher_subject_id == Subject.subject_id,
                Subject.subject_workspace_id == Workspace.workspace_id,
                Workspace.workspace_organization_id == org_id
            )
        ))
        result = await self.db.execute(stmt)
        return bool(result.scalar())

    async def is_user_teacher_or_admin_role(self, org_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        stmt = (
            select(OrganizationMember)
            .join(Role, OrganizationMember.organization_member_role_id == Role.role_id)
            .where(
                OrganizationMember.organization_member_organization_id == org_id,
                OrganizationMember.organization_member_user_id == user_id,
                OrganizationMember.organization_member_status == OrganizationMemberStatus.ACTIVE,
                Role.role_name.in_(["Owner", "Admin", "Teacher"])
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first() is not None
