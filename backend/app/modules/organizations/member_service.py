import uuid
import secrets
from typing import List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.models import User, UserStatus
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService
from app.modules.users.profile_photo import ProfilePhotoService
from app.modules.organizations.models import Organization, OrganizationMember, Role, OrganizationMemberStatus, WorkspaceStatus
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.member_schemas import (
    MemberCreateRequest,
    MemberUpdateRequest,
    MemberResponse,
    MemberCreateResponse,
    ProfilePhotoUploadInfo,
    WorkspaceBrief
)
from app.core.exceptions import ConflictException, NotFoundException, ForbiddenException


class MemberService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = OrganizationRepository(db)
        self.user_repo = UserRepository(db)
        self.user_service = UserService(db)
        self.photo_service = ProfilePhotoService()

    def _build_member_response(
        self,
        user: User,
        member: OrganizationMember,
        role: Role,
        ws_briefs: List[WorkspaceBrief],
    ) -> MemberResponse:
        """Build a MemberResponse with resolved profile_image_url."""
        return MemberResponse(
            user_id=user.user_id,
            email=user.user_email,
            first_name=user.user_first_name,
            last_name=user.user_last_name,
            phone=user.user_phone,
            profile_image_url=self.photo_service.resolve_photo_url(user.user_profile_image),
            organization_member_id=member.organization_member_id,
            status=member.organization_member_status,
            role_id=role.role_id,
            role_name=role.role_name,
            workspaces=ws_briefs
        )

    async def _get_workspace_briefs(self, org_id: uuid.UUID, user_id: uuid.UUID) -> List[WorkspaceBrief]:
        """Fetch workspace assignments for a user in an organization."""
        workspaces = await self.repo.get_user_workspace_assignments(org_id, user_id)
        return [
            WorkspaceBrief(workspace_id=w.workspace_id, workspace_name=w.workspace_name)
            for w in workspaces
        ]

    async def _validate_workspace_assignments(self, org_id: uuid.UUID, workspace_ids: List[uuid.UUID]):
        unique_ws_ids = set(workspace_ids)
        if not unique_ws_ids:
            return

        workspaces = await self.repo.get_workspaces_by_ids(unique_ws_ids)
        if len(workspaces) != len(unique_ws_ids):
            raise NotFoundException("One or more workspaces do not exist.")
        
        for ws in workspaces:
            if ws.workspace_organization_id != org_id:
                raise ForbiddenException(f"Workspace '{ws.workspace_name}' belongs to another organization.")
            if ws.workspace_status != WorkspaceStatus.ACTIVE:
                raise ConflictException(f"Workspace '{ws.workspace_name}' is archived and cannot be assigned.")

    async def check_email(self, email: str) -> dict:
        """Check if a user exists globally in SmartClass AI by their email address."""
        user = await self.user_repo.get_by_email(email)
        if user:
            return {
                "exists": True,
                "first_name": user.user_first_name,
                "last_name": user.user_last_name,
                "phone": user.user_phone
            }
        return {"exists": False}

    async def list_members(
        self,
        org_id: uuid.UUID,
        search: Optional[str] = None,
        role_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        workspace_id: Optional[uuid.UUID] = None
    ) -> List[MemberResponse]:
        """List all members of an organization, including their assigned workspaces and role names."""
        db_members = await self.repo.get_organization_members(org_id, search, role_id, status, workspace_id)
        
        responses = []
        for user, member, role in db_members:
            ws_briefs = await self._get_workspace_briefs(org_id, user.user_id)
            responses.append(self._build_member_response(user, member, role, ws_briefs))
        return responses

    async def get_member(self, org_id: uuid.UUID, member_id: uuid.UUID) -> MemberResponse:
        """Retrieve details of a single organization member."""
        data = await self.repo.get_organization_member_by_id(org_id, member_id)
        if not data:
            raise NotFoundException("Member not found in this organization.")
        
        user, member, role = data
        ws_briefs = await self._get_workspace_briefs(org_id, user.user_id)
        return self._build_member_response(user, member, role, ws_briefs)

    async def create_member(self, org_id: uuid.UUID, payload: MemberCreateRequest) -> MemberCreateResponse:
        """
        Atomically add a user to the organization.
        Creates a new user record with a temporary password if they don't exist globally.
        If photo content_type and file_size are provided, generates an S3 upload URL.
        """
        # 1. Resolve or Create User
        user = await self.user_repo.get_by_email(payload.email)
        is_new_user = False
        
        if user:
            # Check if already a member of this organization
            existing = await self.repo.get_organization_member_by_user_id(org_id, user.user_id)
            if existing:
                raise ConflictException("User is already a member of this organization.")
            
            # Optionally update user's profile details if not set
            if not user.user_first_name or not user.user_last_name:
                await self.user_repo.update(
                    user,
                    user_first_name=payload.first_name,
                    user_last_name=payload.last_name,
                    user_phone=payload.phone or user.user_phone
                )
        else:
            # Generate a secure temporary password
            temp_pass = f"Smart-{secrets.token_hex(4)}!"
            user = await self.user_service.create_user(
                email=payload.email,
                password=temp_pass,
                first_name=payload.first_name,
                last_name=payload.last_name,
                phone=payload.phone
            )
            is_new_user = True

        try:
            async with self.db.begin_nested():
                # 2. Validate workspaces
                await self._validate_workspace_assignments(org_id, payload.workspace_ids)

                # 3. Add Organization Membership
                member = await self.repo.create_organization_member(
                    org_id=org_id,
                    user_id=user.user_id,
                    role_id=payload.role_id
                )

                # 4. Add Workspace Assignments
                unique_ws_ids = set(payload.workspace_ids)
                for ws_id in unique_ws_ids:
                    await self.repo.create_workspace_member(
                        workspace_id=ws_id,
                        user_id=user.user_id,
                        role_id=payload.role_id
                    )

                # Fetch role name
                role = await self.db.get(Role, payload.role_id)
                role_name = role.role_name if role else "Member"

                ws_briefs = await self._get_workspace_briefs(org_id, user.user_id)

                # Note: In a production setup we would email the temporary password to the user.
                # Since email isn't set up yet, we will log it / output it.
                if is_new_user:
                    print(f"Generated temporary password for {payload.email}: {temp_pass}")

                # 5. Generate profile photo upload URL if photo info is provided
                photo_upload_info: Optional[ProfilePhotoUploadInfo] = None
                content_type = getattr(payload, "content_type", None)
                file_size = getattr(payload, "file_size", None)
                if content_type and file_size:
                    upload_data = self.photo_service.request_upload(
                        user_id=user.user_id,
                        content_type=content_type,
                        file_size=file_size,
                    )
                    photo_upload_info = ProfilePhotoUploadInfo(
                        key=upload_data["key"],
                        upload_url=upload_data["upload_url"],
                        expires_in=upload_data["expires_in"],
                    )

                return MemberCreateResponse(
                    user_id=user.user_id,
                    email=user.user_email,
                    first_name=user.user_first_name,
                    last_name=user.user_last_name,
                    phone=user.user_phone,
                    profile_image_url=self.photo_service.resolve_photo_url(user.user_profile_image),
                    organization_member_id=member.organization_member_id,
                    status=member.organization_member_status,
                    role_id=payload.role_id,
                    role_name=role_name,
                    workspaces=ws_briefs,
                    profile_photo_upload=photo_upload_info,
                )
        except Exception as e:
            raise e

    async def update_member(
        self,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
        payload: MemberUpdateRequest
    ) -> MemberResponse:
        """Update a member's local profile info and organization role."""
        data = await self.repo.get_organization_member_by_id(org_id, member_id)
        if not data:
            raise NotFoundException("Member not found in this organization.")

        user, member, role = data
        
        # Verify they are not attempting to demote the organization owner
        org = await self.db.get(Organization, org_id)
        if org.organization_owner_user_id == user.user_id and payload.role_id != role.role_id:
            raise ForbiddenException("Cannot modify the role of the organization owner.")

        # Update User fields
        await self.user_repo.update(
            user,
            user_first_name=payload.first_name,
            user_last_name=payload.last_name,
            user_phone=payload.phone
        )

        # Update Membership Role
        member.organization_member_role_id = payload.role_id
        self.db.add(member)
        await self.db.flush()

        # Reload updated fields
        role_new = await self.db.get(Role, payload.role_id)
        role_name = role_new.role_name if role_new else "Member"
        ws_briefs = await self._get_workspace_briefs(org_id, user.user_id)

        return self._build_member_response(user, member, role_new, ws_briefs)

    async def update_member_status(
        self,
        org_id: uuid.UUID,
        member_id: uuid.UUID,
        status: str
    ) -> MemberResponse:
        """Suspend or activate an organization member."""
        data = await self.repo.get_organization_member_by_id(org_id, member_id)
        if not data:
            raise NotFoundException("Member not found in this organization.")

        user, member, role = data
        org = await self.db.get(Organization, org_id)
        if org.organization_owner_user_id == user.user_id:
            raise ForbiddenException("Cannot suspend or modify the status of the organization owner.")

        member.organization_member_status = OrganizationMemberStatus(status)
        self.db.add(member)
        await self.db.flush()

        ws_briefs = await self._get_workspace_briefs(org_id, user.user_id)
        return self._build_member_response(user, member, role, ws_briefs)

    async def delete_member(self, org_id: uuid.UUID, member_id: uuid.UUID):
        """Soft-delete an organization member by deleting their membership rows (leaving User profile intact)."""
        data = await self.repo.get_organization_member_by_id(org_id, member_id)
        if not data:
            raise NotFoundException("Member not found in this organization.")

        user, member, role = data
        org = await self.db.get(Organization, org_id)
        if org.organization_owner_user_id == user.user_id:
            raise ForbiddenException("Cannot delete the organization owner's membership.")

        # Delete from organization and workspace memberships
        await self.repo.delete_user_workspace_memberships(org_id, user.user_id)
        await self.db.delete(member)
        await self.db.flush()

    async def assign_workspaces(self, org_id: uuid.UUID, user_id: uuid.UUID, workspace_ids: List[uuid.UUID]):
        """Synchronize a user's assigned workspaces."""
        # Check active membership
        data = await self.repo.get_organization_member_by_user_id(org_id, user_id)
        if not data:
            raise NotFoundException("User is not a member of this organization.")
        user, member_obj, role = data

        try:
            async with self.db.begin_nested():
                # Validate new workspace assignments
                await self._validate_workspace_assignments(org_id, workspace_ids)

                # Clear existing
                await self.repo.delete_user_workspace_memberships(org_id, user_id)
                # Assign new
                unique_ws_ids = set(workspace_ids)
                for ws_id in unique_ws_ids:
                    await self.repo.create_workspace_member(
                        workspace_id=ws_id,
                        user_id=user_id,
                        role_id=member_obj.organization_member_role_id
                    )
        except Exception as e:
            raise e
