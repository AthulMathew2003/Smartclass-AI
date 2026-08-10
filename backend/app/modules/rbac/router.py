import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.modules.organizations.dependencies import get_active_organization_id
from app.modules.users.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.rbac.service import RBACService
from app.modules.rbac.schemas import (
    PermissionGroupResponse,
    RoleResponse,
    RoleCreateRequest,
    RoleUpdateRequest,
    MyPermissionsResponse
)
from app.modules.rbac.dependencies import require_permission
from app.modules.rbac.constants import MemberPermission, OrganizationPermission

router = APIRouter()


@router.get("/me/permissions", response_model=MyPermissionsResponse)
async def get_my_permissions(
    current_user: User = Depends(get_current_user),
    org_id: uuid.UUID = Depends(get_active_organization_id),
    db: AsyncSession = Depends(get_db)
):
    """Return the authenticated user's effective permissions for the active organization."""
    service = RBACService(db)
    permissions = await service.get_user_permissions(current_user.user_id, org_id)
    return MyPermissionsResponse(
        organization_id=org_id,
        permissions=permissions
    )


@router.get("/permissions", response_model=List[PermissionGroupResponse])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_active_organization_id),
    _=Depends(require_permission(MemberPermission.READ))
):
    """List all available system permissions grouped by domain category."""
    service = RBACService(db)
    return await service.list_permissions_grouped()


@router.get("", response_model=List[RoleResponse])
async def list_roles(
    org_id: uuid.UUID = Depends(get_active_organization_id),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(MemberPermission.READ))
):
    """List all system and custom roles for the active organization context."""
    service = RBACService(db)
    return await service.list_roles(org_id)


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role_details(
    role_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_active_organization_id),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(MemberPermission.READ))
):
    """Fetch details and permissions of a single role."""
    service = RBACService(db)
    return await service.get_role(role_id, org_id)


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_role(
    payload: RoleCreateRequest,
    org_id: uuid.UUID = Depends(get_active_organization_id),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(MemberPermission.UPDATE))
):
    """Create a new custom role for the active organization."""
    service = RBACService(db)
    role_res = await service.create_custom_role(org_id, payload)
    await db.commit()
    return role_res


@router.patch("/{role_id}", response_model=RoleResponse)
async def update_custom_role(
    role_id: uuid.UUID,
    payload: RoleUpdateRequest,
    org_id: uuid.UUID = Depends(get_active_organization_id),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(MemberPermission.UPDATE))
):
    """Update custom role metadata and permission assignments."""
    service = RBACService(db)
    role_res = await service.update_custom_role(role_id, org_id, payload)
    await db.commit()
    return role_res


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_role(
    role_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_active_organization_id),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(MemberPermission.DELETE))
):
    """Delete a custom role if no active organization members are currently assigned to it."""
    service = RBACService(db)
    await service.delete_custom_role(role_id, org_id)
    await db.commit()
