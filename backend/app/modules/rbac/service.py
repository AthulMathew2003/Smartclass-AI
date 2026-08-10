import uuid
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.rbac.repository import RBACRepository
from app.modules.rbac.schemas import (
    PermissionResponse,
    PermissionGroupResponse,
    RoleResponse,
    RoleCreateRequest,
    RoleUpdateRequest
)
from app.core.exceptions import NotFoundException, ConflictException, ForbiddenException


class RBACService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RBACRepository(db)

    async def get_user_permissions(self, user_id: uuid.UUID, organization_id: uuid.UUID) -> List[str]:
        """Fetch all permissions for a user in the organization context."""
        return await self.repo.get_permissions_by_user(user_id, organization_id)

    async def has_permission(self, user_id: uuid.UUID, organization_id: uuid.UUID, permission: str) -> bool:
        """Verify if a user has a specific permission in the organization."""
        return await self.repo.user_has_permission(user_id, organization_id, permission)

    async def list_permissions_grouped(self) -> List[PermissionGroupResponse]:
        """List all system permissions grouped by module category."""
        all_perms = await self.repo.get_all_permissions()
        groups: Dict[str, List[PermissionResponse]] = {}

        for p in all_perms:
            cat = p.permission_name.split(".")[0].capitalize()
            perm_resp = PermissionResponse(
                permission_id=p.permission_id,
                permission_name=p.permission_name,
                permission_description=p.permission_description,
                category=cat
            )
            groups.setdefault(cat, []).append(perm_resp)

        return [
            PermissionGroupResponse(category=cat, permissions=perms)
            for cat, perms in groups.items()
        ]

    async def list_roles(self, organization_id: uuid.UUID) -> List[RoleResponse]:
        """List all system and custom roles for an organization along with permissions and member counts."""
        roles = await self.repo.get_roles_for_organization(organization_id)
        role_responses = []

        for role in roles:
            perms = await self.repo.get_role_permissions(role.role_id)
            mem_count = await self.repo.count_role_members(role.role_id, organization_id)
            perm_responses = [
                PermissionResponse(
                    permission_id=p.permission_id,
                    permission_name=p.permission_name,
                    permission_description=p.permission_description,
                    category=p.permission_name.split(".")[0].capitalize()
                )
                for p in perms
            ]

            role_responses.append(
                RoleResponse(
                    role_id=role.role_id,
                    role_name=role.role_name,
                    role_description=role.role_description,
                    role_is_system=role.role_is_system,
                    role_organization_id=role.role_organization_id,
                    member_count=mem_count,
                    permissions=perm_responses
                )
            )

        return role_responses

    async def get_role(self, role_id: uuid.UUID, organization_id: uuid.UUID) -> RoleResponse:
        """Fetch details of a single role."""
        role = await self.repo.get_role_by_id(role_id)
        if not role:
            raise NotFoundException("Role not found.")

        # Ensure role belongs to this org or is a system role
        if not role.role_is_system and role.role_organization_id != organization_id:
            raise ForbiddenException("Access denied to this role.")

        perms = await self.repo.get_role_permissions(role.role_id)
        mem_count = await self.repo.count_role_members(role.role_id, organization_id)
        perm_responses = [
            PermissionResponse(
                permission_id=p.permission_id,
                permission_name=p.permission_name,
                permission_description=p.permission_description,
                category=p.permission_name.split(".")[0].capitalize()
            )
            for p in perms
        ]

        return RoleResponse(
            role_id=role.role_id,
            role_name=role.role_name,
            role_description=role.role_description,
            role_is_system=role.role_is_system,
            role_organization_id=role.role_organization_id,
            member_count=mem_count,
            permissions=perm_responses
        )

    async def create_custom_role(self, organization_id: uuid.UUID, payload: RoleCreateRequest) -> RoleResponse:
        """Create a custom role for the active organization."""
        # Check name uniqueness among custom roles in this org and system roles
        existing_roles = await self.repo.get_roles_for_organization(organization_id)
        if any(r.role_name.lower() == payload.role_name.lower() for r in existing_roles):
            raise ConflictException(f"A role named '{payload.role_name}' already exists in this organization.")

        role = await self.repo.create_custom_role(
            organization_id=organization_id,
            name=payload.role_name,
            description=payload.role_description,
            permission_ids=payload.permission_ids
        )

        return await self.get_role(role.role_id, organization_id)

    async def update_custom_role(self, role_id: uuid.UUID, organization_id: uuid.UUID, payload: RoleUpdateRequest) -> RoleResponse:
        """Update metadata or permissions of a custom role."""
        role = await self.repo.get_role_by_id(role_id)
        if not role:
            raise NotFoundException("Role not found.")

        if role.role_is_system:
            raise ForbiddenException("System roles cannot be modified.")

        if role.role_organization_id != organization_id:
            raise ForbiddenException("Access denied to this role.")

        if payload.role_name is not None and payload.role_name.lower() != role.role_name.lower():
            existing_roles = await self.repo.get_roles_for_organization(organization_id)
            if any(r.role_name.lower() == payload.role_name.lower() for r in existing_roles if r.role_id != role_id):
                raise ConflictException(f"A role named '{payload.role_name}' already exists in this organization.")

        updated_role = await self.repo.update_custom_role(
            role=role,
            name=payload.role_name,
            description=payload.role_description,
            permission_ids=payload.permission_ids
        )

        return await self.get_role(updated_role.role_id, organization_id)

    async def delete_custom_role(self, role_id: uuid.UUID, organization_id: uuid.UUID) -> None:
        """Delete a custom role if no active members are assigned."""
        role = await self.repo.get_role_by_id(role_id)
        if not role:
            raise NotFoundException("Role not found.")

        if role.role_is_system:
            raise ForbiddenException("System roles cannot be deleted.")

        if role.role_organization_id != organization_id:
            raise ForbiddenException("Access denied to this role.")

        mem_count = await self.repo.count_role_members(role_id, organization_id)
        if mem_count > 0:
            raise ConflictException(f"Cannot delete role '{role.role_name}' because {mem_count} member(s) are currently assigned to it.")

        await self.repo.delete_custom_role(role)
