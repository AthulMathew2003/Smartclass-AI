import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.organizations.models import Workspace, WorkspaceStatus
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.workspace_schemas import (
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
    WorkspaceResponse
)
from app.core.exceptions import ConflictException, NotFoundException, ForbiddenException


class WorkspaceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = OrganizationRepository(db)

    async def list_workspaces(self, org_id: uuid.UUID) -> List[WorkspaceResponse]:
        """Fetch all workspaces registered under an organization."""
        workspaces = await self.repo.get_workspaces(org_id)
        responses = []
        for ws in workspaces:
            m_count = await self.repo.count_workspace_members(ws.workspace_id)
            c_count = await self.repo.count_workspace_subjects(ws.workspace_id)
            responses.append(
                WorkspaceResponse(
                    workspace_id=ws.workspace_id,
                    workspace_organization_id=ws.workspace_organization_id,
                    workspace_name=ws.workspace_name,
                    workspace_description=ws.workspace_description,
                    workspace_banner=ws.workspace_banner,
                    workspace_status=ws.workspace_status,
                    workspace_created_by=ws.workspace_created_by,
                    workspace_created_at=ws.workspace_created_at,
                    workspace_updated_at=ws.workspace_updated_at,
                    member_count=m_count,
                    subject_count=c_count
                )
            )
        return responses

    async def get_workspace(self, workspace_id: uuid.UUID, org_id: uuid.UUID) -> WorkspaceResponse:
        """Fetch details of a single workspace within an active organization context."""
        ws = await self.repo.get_workspace_by_id(workspace_id)
        if not ws or ws.workspace_organization_id != org_id:
            raise ForbiddenException("Access denied to this workspace.")

        m_count = await self.repo.count_workspace_members(ws.workspace_id)
        c_count = await self.repo.count_workspace_subjects(ws.workspace_id)
        return WorkspaceResponse(
            workspace_id=ws.workspace_id,
            workspace_organization_id=ws.workspace_organization_id,
            workspace_name=ws.workspace_name,
            workspace_description=ws.workspace_description,
            workspace_banner=ws.workspace_banner,
            workspace_status=ws.workspace_status,
            workspace_created_by=ws.workspace_created_by,
            workspace_created_at=ws.workspace_created_at,
            workspace_updated_at=ws.workspace_updated_at,
            member_count=m_count,
            subject_count=c_count
        )

    async def create_workspace(
        self,
        org_id: uuid.UUID,
        created_by_user_id: uuid.UUID,
        payload: WorkspaceCreateRequest
    ) -> WorkspaceResponse:
        """Create a new workspace under the active organization."""
        if await self.repo.exists_workspace_name(org_id, payload.workspace_name):
            raise ConflictException(f"A workspace named '{payload.workspace_name}' already exists in this organization.")

        ws = await self.repo.create_workspace(
            org_id=org_id,
            name=payload.workspace_name,
            created_by=created_by_user_id,
            description=payload.workspace_description
        )

        return WorkspaceResponse(
            workspace_id=ws.workspace_id,
            workspace_organization_id=ws.workspace_organization_id,
            workspace_name=ws.workspace_name,
            workspace_description=ws.workspace_description,
            workspace_banner=ws.workspace_banner,
            workspace_status=ws.workspace_status,
            workspace_created_by=ws.workspace_created_by,
            workspace_created_at=ws.workspace_created_at,
            workspace_updated_at=ws.workspace_updated_at,
            member_count=0,
            subject_count=0
        )

    async def update_workspace(
        self,
        workspace_id: uuid.UUID,
        org_id: uuid.UUID,
        payload: WorkspaceUpdateRequest
    ) -> WorkspaceResponse:
        """Update workspace metadata or status within the active organization."""
        ws = await self.repo.get_workspace_by_id(workspace_id)
        if not ws or ws.workspace_organization_id != org_id:
            raise ForbiddenException("Access denied to this workspace.")

        if payload.workspace_name is not None and payload.workspace_name.strip().lower() != ws.workspace_name.lower():
            if await self.repo.exists_workspace_name(org_id, payload.workspace_name, exclude_workspace_id=workspace_id):
                raise ConflictException(f"A workspace named '{payload.workspace_name}' already exists in this organization.")

        updated_ws = await self.repo.update_workspace(
            workspace=ws,
            name=payload.workspace_name,
            description=payload.workspace_description,
            status=payload.workspace_status
        )

        m_count = await self.repo.count_workspace_members(updated_ws.workspace_id)
        c_count = await self.repo.count_workspace_subjects(updated_ws.workspace_id)
        return WorkspaceResponse(
            workspace_id=updated_ws.workspace_id,
            workspace_organization_id=updated_ws.workspace_organization_id,
            workspace_name=updated_ws.workspace_name,
            workspace_description=updated_ws.workspace_description,
            workspace_banner=updated_ws.workspace_banner,
            workspace_status=updated_ws.workspace_status,
            workspace_created_by=updated_ws.workspace_created_by,
            workspace_created_at=updated_ws.workspace_created_at,
            workspace_updated_at=updated_ws.workspace_updated_at,
            member_count=m_count,
            subject_count=c_count
        )

    async def archive_workspace(self, workspace_id: uuid.UUID, org_id: uuid.UUID) -> WorkspaceResponse:
        """Soft-delete/archive a workspace within the active organization context."""
        ws = await self.repo.get_workspace_by_id(workspace_id)
        if not ws or ws.workspace_organization_id != org_id:
            raise ForbiddenException("Access denied to this workspace.")

        archived_ws = await self.repo.update_workspace(
            workspace=ws,
            status=WorkspaceStatus.ARCHIVED
        )

        m_count = await self.repo.count_workspace_members(archived_ws.workspace_id)
        c_count = await self.repo.count_workspace_subjects(archived_ws.workspace_id)
        return WorkspaceResponse(
            workspace_id=archived_ws.workspace_id,
            workspace_organization_id=archived_ws.workspace_organization_id,
            workspace_name=archived_ws.workspace_name,
            workspace_description=archived_ws.workspace_description,
            workspace_banner=archived_ws.workspace_banner,
            workspace_status=archived_ws.workspace_status,
            workspace_created_by=archived_ws.workspace_created_by,
            workspace_created_at=archived_ws.workspace_created_at,
            workspace_updated_at=archived_ws.workspace_updated_at,
            member_count=m_count,
            subject_count=c_count
        )

    async def list_workspace_members(self, workspace_id: uuid.UUID, org_id: uuid.UUID):
        """List all members assigned to a workspace within the active organization."""
        ws = await self.repo.get_workspace_by_id(workspace_id)
        if not ws or ws.workspace_organization_id != org_id:
            raise ForbiddenException("Access denied to this workspace.")

        members_data = await self.repo.get_workspace_members(workspace_id)
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
