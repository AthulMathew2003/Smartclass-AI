import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, and_, or_, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.modules.subjects.models import (
    Subject,
    SubjectTeacher,
    SubjectMaterial,
    SubjectMaterialStatus
)
from app.modules.organizations.models import (
    Workspace,
    WorkspaceMember,
    OrganizationMember,
    OrganizationMemberStatus,
    Role
)


class SubjectMaterialRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_material(
        self,
        subject_id: uuid.UUID,
        title: str,
        description: Optional[str],
        category: str,
        original_filename: str,
        content_type: str,
        file_size: int,
        s3_key: str,
        uploaded_by: Optional[uuid.UUID],
        status: SubjectMaterialStatus = SubjectMaterialStatus.ACTIVE,
        material_id: Optional[uuid.UUID] = None
    ) -> SubjectMaterial:
        material = SubjectMaterial(
            material_id=material_id or uuid.uuid4(),
            material_subject_id=subject_id,
            material_title=title,
            material_description=description,
            material_category=category,
            material_original_filename=original_filename,
            material_content_type=content_type,
            material_file_size=file_size,
            material_s3_key=s3_key,
            material_status=status,
            material_uploaded_by=uploaded_by
        )
        self.db.add(material)
        try:
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            raise e
        return material

    async def get_material_by_id(self, material_id: uuid.UUID) -> Optional[SubjectMaterial]:
        stmt = (
            select(SubjectMaterial)
            .where(SubjectMaterial.material_id == material_id)
            .options(
                selectinload(SubjectMaterial.subject).selectinload(Subject.workspace),
                selectinload(SubjectMaterial.uploader)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_materials_for_subject(
        self,
        subject_id: uuid.UUID,
        status_filter: Optional[SubjectMaterialStatus] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        include_archived: bool = False
    ) -> List[SubjectMaterial]:
        stmt = (
            select(SubjectMaterial)
            .where(SubjectMaterial.material_subject_id == subject_id)
            .options(
                selectinload(SubjectMaterial.subject).selectinload(Subject.workspace),
                selectinload(SubjectMaterial.uploader)
            )
        )

        if status_filter is not None:
            if status_filter == SubjectMaterialStatus.ARCHIVED and not include_archived:
                return []
            stmt = stmt.where(SubjectMaterial.material_status == status_filter)
        else:
            if not include_archived:
                stmt = stmt.where(SubjectMaterial.material_status == SubjectMaterialStatus.ACTIVE)

        if category and category.strip() and category.strip().lower() != "all":
            stmt = stmt.where(SubjectMaterial.material_category.ilike(category.strip()))

        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    SubjectMaterial.material_title.ilike(term),
                    SubjectMaterial.material_description.ilike(term),
                    SubjectMaterial.material_original_filename.ilike(term),
                    SubjectMaterial.material_category.ilike(term)
                )
            )

        stmt = stmt.order_by(SubjectMaterial.material_created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_material(
        self,
        material: SubjectMaterial,
        title: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None
    ) -> SubjectMaterial:
        if title is not None:
            material.material_title = title.strip()
        if description is not None:
            material.material_description = description.strip() or None
        if category is not None:
            material.material_category = category.strip()

        await self.db.flush()
        return material

    async def archive_material(self, material: SubjectMaterial) -> SubjectMaterial:
        material.material_status = SubjectMaterialStatus.ARCHIVED
        await self.db.flush()
        return material

    async def delete_material_record(self, material: SubjectMaterial) -> None:
        """Physical delete (used for unconfirmed upload cleanup or hard rollback)."""
        await self.db.delete(material)
        await self.db.flush()

    # ── Hierarchy and Authorization Lookups ─────────────────────

    async def get_subject(self, subject_id: uuid.UUID) -> Optional[Subject]:
        stmt = (
            select(Subject)
            .where(Subject.subject_id == subject_id)
            .options(selectinload(Subject.workspace))
        )
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
