import uuid
from typing import List, Optional
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.organizations.models import Role, OrganizationMember, OrganizationMemberStatus, Organization, OrganizationStatus
from app.modules.rbac.models import Permission, RolePermission


class RBACRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_role_permissions(self, role_id: uuid.UUID) -> List[Permission]:
        """Fetch all permissions associated with a specific role ID."""
        stmt = (
            select(Permission)
            .join(RolePermission, Permission.permission_id == RolePermission.permission_id)
            .where(RolePermission.role_id == role_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_permissions_by_user(self, user_id: uuid.UUID, organization_id: uuid.UUID) -> List[str]:
        """Resolve all permission names mapped to the user's role in the organization."""
        # Find active organization membership
        stmt = (
            select(OrganizationMember)
            .where(
                OrganizationMember.organization_member_user_id == user_id,
                OrganizationMember.organization_member_organization_id == organization_id
            )
        )
        mem_res = await self.db.execute(stmt)
        mem = mem_res.scalars().first()
        if not mem or mem.organization_member_status != OrganizationMemberStatus.ACTIVE:
            return []

        # Check if Organization itself is active
        org_res = await self.db.execute(select(Organization).where(Organization.organization_id == organization_id))
        org = org_res.scalars().first()
        if not org or org.organization_status != OrganizationStatus.ACTIVE:
            return []

        # Fetch permissions for user's role
        return [p.permission_name for p in await self.get_role_permissions(mem.organization_member_role_id)]

    async def user_has_permission(self, user_id: uuid.UUID, organization_id: uuid.UUID, permission: str) -> bool:
        """Resolve if the user has a specific permission string in the organization context."""
        user_perms = await self.get_permissions_by_user(user_id, organization_id)
        return permission in user_perms

    async def get_system_role(self, name: str) -> Optional[Role]:
        """Retrieve a global system role by name."""
        stmt = (
            select(Role)
            .where(
                Role.role_organization_id.is_(None),
                Role.role_is_system.is_(True),
                Role.role_name == name
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_all_permissions(self) -> List[Permission]:
        """Retrieve all available system permissions ordered by permission_name."""
        stmt = select(Permission).order_by(Permission.permission_name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_permissions_grouped(self) -> List[Permission]:
        """Fetch all system permissions ordered by permission name."""
        stmt = select(Permission).order_by(Permission.permission_name.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_role_by_id(self, role_id: uuid.UUID) -> Optional[Role]:
        """Fetch a single role by ID."""
        return await self.db.get(Role, role_id)

    async def get_roles_for_organization(self, organization_id: uuid.UUID) -> List[Role]:
        """Fetch system roles (org_id is null) plus custom roles for the specific org."""
        stmt = (
            select(Role)
            .where(
                (Role.role_organization_id == None) | (Role.role_organization_id == organization_id)
            )
            .order_by(Role.role_is_system.desc(), Role.role_name.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_role_members(self, role_id: uuid.UUID, organization_id: uuid.UUID) -> int:
        """Count active members assigned to a specific role in an organization."""
        stmt = (
            select(OrganizationMember)
            .where(
                OrganizationMember.organization_member_role_id == role_id,
                OrganizationMember.organization_member_organization_id == organization_id
            )
        )
        result = await self.db.execute(stmt)
        return len(result.scalars().all())

    async def create_custom_role(
        self,
        organization_id: uuid.UUID,
        name: str,
        description: Optional[str],
        permission_ids: List[uuid.UUID]
    ) -> Role:
        """Create a custom role for an organization and link its permissions."""
        role = Role(
            role_organization_id=organization_id,
            role_name=name,
            role_description=description,
            role_is_system=False
        )
        self.db.add(role)
        await self.db.flush()

        unique_permission_ids = list(dict.fromkeys(permission_ids))
        for pid in unique_permission_ids:
            rp = RolePermission(role_id=role.role_id, permission_id=pid)
            self.db.add(rp)

        await self.db.flush()
        return role

    async def update_custom_role(
        self,
        role: Role,
        name: Optional[str],
        description: Optional[str],
        permission_ids: Optional[List[uuid.UUID]]
    ) -> Role:
        """Update a custom role's metadata and permission mappings."""
        if name is not None:
            role.role_name = name
        if description is not None:
            role.role_description = description

        if permission_ids is not None:
            # Bulk delete existing role permissions in database
            await self.db.execute(delete(RolePermission).where(RolePermission.role_id == role.role_id))
            await self.db.flush()

            # Insert new deduplicated role permissions
            unique_permission_ids = list(dict.fromkeys(permission_ids))
            for pid in unique_permission_ids:
                rp = RolePermission(role_id=role.role_id, permission_id=pid)
                self.db.add(rp)

        await self.db.flush()
        return role

    async def delete_custom_role(self, role: Role) -> None:
        """Delete a custom role."""
        await self.db.execute(delete(RolePermission).where(RolePermission.role_id == role.role_id))
        await self.db.delete(role)
