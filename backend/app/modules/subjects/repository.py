import uuid
from typing import List, Optional
from sqlalchemy import select, and_, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.modules.subjects.models import Subject, SubjectTeacher, SubjectStatus
from app.modules.organizations.models import (
    OrganizationMember, OrganizationMemberStatus,
    WorkspaceMember, Workspace, Role
)


class SubjectRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_subject(self, workspace_id: uuid.UUID, name: str, description: Optional[str], created_by: uuid.UUID) -> Subject:
        subject = Subject(
            subject_workspace_id=workspace_id,
            subject_name=name,
            subject_description=description,
            subject_created_by=created_by,
            subject_status=SubjectStatus.ACTIVE
        )
        self.db.add(subject)
        try:
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            raise e
        return subject

    async def get_subject_by_id(self, subject_id: uuid.UUID) -> Optional[Subject]:
        stmt = select(Subject).where(Subject.subject_id == subject_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_subjects_by_workspace(self, workspace_id: uuid.UUID) -> List[Subject]:
        stmt = select(Subject).where(Subject.subject_workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_subject(self, subject: Subject, name: Optional[str] = None, description: Optional[str] = None) -> Subject:
        if name is not None:
            subject.subject_name = name
        if description is not None:
            subject.subject_description = description

        self.db.add(subject)
        try:
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            raise e
        return subject

    async def archive_subject(self, subject: Subject) -> Subject:
        subject.subject_status = SubjectStatus.ARCHIVED
        self.db.add(subject)
        await self.db.flush()
        return subject

    # ── Subject Teacher operations ──────────────────────────────────────

    async def get_subject_teachers(self, subject_id: uuid.UUID) -> List[SubjectTeacher]:
        stmt = select(SubjectTeacher).where(SubjectTeacher.subject_teacher_subject_id == subject_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_subject_teacher(self, subject_id: uuid.UUID, user_id: uuid.UUID) -> Optional[SubjectTeacher]:
        stmt = select(SubjectTeacher).where(
            and_(
                SubjectTeacher.subject_teacher_subject_id == subject_id,
                SubjectTeacher.subject_teacher_user_id == user_id
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def add_subject_teacher(self, subject_id: uuid.UUID, user_id: uuid.UUID) -> SubjectTeacher:
        teacher = SubjectTeacher(
            subject_teacher_subject_id=subject_id,
            subject_teacher_user_id=user_id
        )
        self.db.add(teacher)
        try:
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            raise e
        return teacher

    async def remove_subject_teacher(self, teacher: SubjectTeacher) -> None:
        await self.db.delete(teacher)
        await self.db.flush()

    # ── Workspace / Org membership checks ───────────────────────────────

    async def is_user_workspace_member(self, user_id: uuid.UUID, workspace_id: uuid.UUID) -> bool:
        stmt = select(exists().where(
            and_(
                WorkspaceMember.workspace_member_workspace_id == workspace_id,
                WorkspaceMember.workspace_member_user_id == user_id
            )
        ))
        result = await self.db.execute(stmt)
        return result.scalar()

    async def is_user_active_organization_member(self, user_id: uuid.UUID, org_id: uuid.UUID) -> bool:
        stmt = select(exists().where(
            and_(
                OrganizationMember.organization_member_organization_id == org_id,
                OrganizationMember.organization_member_user_id == user_id,
                OrganizationMember.organization_member_status == OrganizationMemberStatus.ACTIVE
            )
        ))
        result = await self.db.execute(stmt)
        return result.scalar()

    async def is_user_teacher_in_workspace(self, user_id: uuid.UUID, workspace_id: uuid.UUID) -> bool:
        """
        Check if the user has a Teacher role in the given workspace.
        Validates through WorkspaceMember → Role, keeping tenant boundary intact.
        """
        stmt = (
            select(WorkspaceMember)
            .join(Role, WorkspaceMember.workspace_member_role_id == Role.role_id)
            .where(
                WorkspaceMember.workspace_member_workspace_id == workspace_id,
                WorkspaceMember.workspace_member_user_id == user_id,
                Role.role_name == "Teacher"
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first() is not None

    async def exists_subject_name(self, workspace_id: uuid.UUID, name: str, exclude_subject_id: Optional[uuid.UUID] = None) -> bool:
        stmt = select(exists().where(
            and_(
                Subject.subject_workspace_id == workspace_id,
                Subject.subject_name.ilike(name)
            )
        ))
        if exclude_subject_id:
            stmt = stmt.where(Subject.subject_id != exclude_subject_id)
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

    async def get_workspace(self, workspace_id: uuid.UUID) -> Optional[Workspace]:
        stmt = select(Workspace).where(Workspace.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
