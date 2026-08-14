import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, and_, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.modules.assignments.models import Assignment, AssignmentStatus
from app.modules.subjects.models import Subject, SubjectTeacher
from app.modules.organizations.models import (
    Workspace,
    WorkspaceMember,
    OrganizationMember,
    OrganizationMemberStatus,
    Role
)


class AssignmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

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
        stmt = select(Assignment).where(Assignment.assignment_id == assignment_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_assignments_by_subject(
        self,
        subject_id: uuid.UUID,
        include_drafts: bool = True,
        include_archived: bool = False
    ) -> List[Assignment]:
        stmt = select(Assignment).where(Assignment.assignment_subject_id == subject_id)
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
        status: Optional[AssignmentStatus] = None,
        due_at: Optional[datetime] = None
    ) -> Assignment:
        if title is not None:
            assignment.assignment_title = title
        if description is not None:
            assignment.assignment_description = description
        if status is not None:
            assignment.assignment_status = status
        if due_at is not None:
            assignment.assignment_due_at = due_at

        self.db.add(assignment)
        try:
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            raise e
        return assignment

    async def archive_assignment(self, assignment: Assignment) -> Assignment:
        assignment.assignment_status = AssignmentStatus.ARCHIVED
        self.db.add(assignment)
        await self.db.flush()
        return assignment

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
        return result.scalar()

    async def is_user_workspace_member(self, user_id: uuid.UUID, workspace_id: uuid.UUID) -> bool:
        stmt = select(exists().where(
            and_(
                WorkspaceMember.workspace_member_workspace_id == workspace_id,
                WorkspaceMember.workspace_member_user_id == user_id
            )
        ))
        result = await self.db.execute(stmt)
        return result.scalar()

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
