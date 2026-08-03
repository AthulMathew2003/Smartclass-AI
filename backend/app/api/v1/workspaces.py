import uuid
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.modules.organizations.dependencies import get_active_organization_id
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.member_schemas import WorkspaceResponse, MemberResponse, WorkspaceBrief

router = APIRouter()


@router.get("", response_model=List[WorkspaceResponse])
async def list_workspaces(
    org_id: uuid.UUID = Depends(get_active_organization_id),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all workspaces registered under the active organization."""
    repo = OrganizationRepository(db)
    workspaces = await repo.get_workspaces(org_id)
    return [
        WorkspaceResponse(
            workspace_id=ws.workspace_id,
            workspace_name=ws.workspace_name,
            workspace_description=ws.workspace_description,
            workspace_status=ws.workspace_status
        )
        for ws in workspaces
    ]


@router.get("/{workspace_id}/members")
async def list_workspace_members(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """List all members assigned to a specific workspace."""
    repo = OrganizationRepository(db)
    members_data = await repo.get_workspace_members(workspace_id)
    
    return [
        {
            "user_id": user.user_id,
            "email": user.user_email,
            "first_name": user.user_first_name,
            "last_name": user.user_last_name,
            "role_name": role.role_name
        }
        for user, role in members_data
    ]
