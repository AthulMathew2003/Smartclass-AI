import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.organizations.models import Workspace, WorkspaceStatus
from app.modules.organizations.repository import OrganizationRepository
from app.modules.users.profile_photo import ProfilePhotoService
from app.modules.organizations.workspace_schemas import (
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
    WorkspaceResponse,
    WorkspaceStudentItem,
    WorkspaceStudentsData,
    WorkspaceStudentsResponse
)
from app.core.exceptions import ConflictException, NotFoundException, ForbiddenException


class WorkspaceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = OrganizationRepository(db)
        self.photo_service = ProfilePhotoService()

    async def list_workspaces(self, org_id: uuid.UUID) -> List[WorkspaceResponse]:
        """Fetch all workspaces registered under an organization using aggregated counts."""
        workspaces = await self.repo.get_workspaces(org_id)
        if not workspaces:
            return []

        member_counts, student_counts, subject_counts = await self.repo.get_workspace_counts_by_org(org_id)

        responses = []
        for ws in workspaces:
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
                    member_count=member_counts.get(ws.workspace_id, 0),
                    student_count=student_counts.get(ws.workspace_id, 0),
                    subject_count=subject_counts.get(ws.workspace_id, 0)
                )
            )
        return responses

    async def get_workspace(self, workspace_id: uuid.UUID, org_id: uuid.UUID) -> WorkspaceResponse:
        """Fetch details of a single workspace within an active organization context."""
        ws = await self.repo.get_workspace_by_id(workspace_id)
        if not ws or ws.workspace_organization_id != org_id:
            raise ForbiddenException("Access denied to this workspace.")

        m_count = await self.repo.count_workspace_members(ws.workspace_id)
        s_count = await self.repo.count_workspace_students(ws.workspace_id)
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
            student_count=s_count,
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
            student_count=0,
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
        s_count = await self.repo.count_workspace_students(updated_ws.workspace_id)
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
            student_count=s_count,
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
        s_count = await self.repo.count_workspace_students(archived_ws.workspace_id)
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
            student_count=s_count,
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

    async def get_workspace_students(
        self,
        workspace_id: uuid.UUID,
        org_id: uuid.UUID,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> WorkspaceStudentsResponse:
        """Fetch paginated students belonging to a workspace under the active organization."""
        ws = await self.repo.get_workspace_by_id(workspace_id)
        if not ws or ws.workspace_organization_id != org_id:
            raise ForbiddenException("Access denied to this workspace.")

        page = max(1, page)
        page_size = max(1, min(100, page_size))

        student_rows, total = await self.repo.get_workspace_students(
            workspace_id=workspace_id,
            search=search,
            page=page,
            page_size=page_size
        )

        total_pages = max(1, (total + page_size - 1) // page_size) if total > 0 else 1

        items = []
        for user, ws_member, org_member in student_rows:
            full_name = f"{user.user_first_name or ''} {user.user_last_name or ''}".strip()
            items.append(
                WorkspaceStudentItem(
                    id=user.user_id,
                    name=full_name or user.user_email,
                    first_name=user.user_first_name,
                    last_name=user.user_last_name,
                    email=user.user_email,
                    avatar_url=self.photo_service.resolve_photo_url(user.user_profile_image),
                    status=org_member.organization_member_status.value if (org_member and hasattr(org_member.organization_member_status, "value")) else (org_member.organization_member_status if org_member else (user.user_status.value if hasattr(user.user_status, "value") else str(user.user_status))),
                    joined_at=ws_member.workspace_member_joined_at
                )
            )

        return WorkspaceStudentsResponse(
            success=True,
            message="Workspace students retrieved successfully",
            data=WorkspaceStudentsData(
                items=items,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages
            ),
            request_id=str(uuid.uuid4())
        )

