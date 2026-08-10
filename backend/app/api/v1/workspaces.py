import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.modules.users.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.organizations.dependencies import get_active_organization_id
from app.modules.organizations.workspace_service import WorkspaceService
from app.modules.organizations.workspace_schemas import (
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
    WorkspaceResponse
)
from app.modules.rbac.dependencies import require_permission
from app.modules.rbac.constants import WorkspacePermission

router = APIRouter()


@router.get("", response_model=List[WorkspaceResponse])
async def list_workspaces(
    org_id: uuid.UUID = Depends(get_active_organization_id),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(WorkspacePermission.READ))
):
    """Retrieve all workspaces registered under the active organization."""
    service = WorkspaceService(db)
    return await service.list_workspaces(org_id)


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreateRequest,
    current_user: User = Depends(get_current_user),
    org_id: uuid.UUID = Depends(get_active_organization_id),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(WorkspacePermission.CREATE))
):
    """Create a new workspace under the active organization."""
    service = WorkspaceService(db)
    workspace_res = await service.create_workspace(org_id, current_user.user_id, payload)
    await db.commit()
    return workspace_res


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_active_organization_id),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(WorkspacePermission.READ))
):
    """Fetch details of a single workspace within the active organization context."""
    service = WorkspaceService(db)
    return await service.get_workspace(workspace_id, org_id)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdateRequest,
    org_id: uuid.UUID = Depends(get_active_organization_id),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(WorkspacePermission.UPDATE))
):
    """Update workspace metadata or status within the active organization context."""
    service = WorkspaceService(db)
    workspace_res = await service.update_workspace(workspace_id, org_id, payload)
    await db.commit()
    return workspace_res


@router.delete("/{workspace_id}", response_model=WorkspaceResponse)
async def archive_workspace(
    workspace_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_active_organization_id),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(WorkspacePermission.DELETE))
):
    """Archive (soft-delete) a workspace within the active organization context."""
    service = WorkspaceService(db)
    workspace_res = await service.archive_workspace(workspace_id, org_id)
    await db.commit()
    return workspace_res


@router.get("/{workspace_id}/members")
async def list_workspace_members(
    workspace_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_active_organization_id),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(WorkspacePermission.READ))
):
    """List all members assigned to a specific workspace."""
    service = WorkspaceService(db)
    return await service.list_workspace_members(workspace_id, org_id)
