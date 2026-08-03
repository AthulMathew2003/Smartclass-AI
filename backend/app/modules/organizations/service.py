import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.organizations.models import Organization, Workspace, WorkspaceMember, Role, OrganizationMember
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.schemas import OnboardingRequest, OrganizationBrief
from app.core.exceptions import ConflictException


class OrganizationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = OrganizationRepository(db)
        self.user_repo = UserRepository(db)

    async def get_user_organization_status(self, user: User, active_org_id: Optional[uuid.UUID] = None):
        """Check if the user is associated with any active organization, listing all memberships."""
        memberships = await self.repo.get_all_memberships_by_user_id(user.user_id)
        if not memberships:
            return {"has_organization": False, "multiple_organizations": False}

        # Build brief details of all organizations they belong to
        org_briefs = []
        for m in memberships:
            org = await self.db.get(Organization, m.organization_member_organization_id)
            role = await self.db.get(Role, m.organization_member_role_id)
            if org:
                org_briefs.append(
                    OrganizationBrief(
                        organization_id=org.organization_id,
                        organization_name=org.organization_name,
                        organization_slug=org.organization_slug,
                        role_name=role.role_name if role else "Member"
                    )
                )

        # Select the active organization context
        active_membership = None
        if active_org_id:
            # Match requested active organization
            active_membership = next(
                (m for m in memberships if m.organization_member_organization_id == active_org_id),
                None
            )
        
        # Default to first membership if none specified or not matched
        if not active_membership:
            active_membership = memberships[0]

        active_org = await self.db.get(Organization, active_membership.organization_member_organization_id)
        active_role = await self.db.get(Role, active_membership.organization_member_role_id)
        
        # Query workspace
        ws_stmt = select(Workspace).join(WorkspaceMember).where(
            WorkspaceMember.workspace_member_user_id == user.user_id,
            Workspace.workspace_organization_id == active_org.organization_id
        )
        ws_res = await self.db.execute(ws_stmt)
        workspace = ws_res.scalars().first()

        return {
            "has_organization": True,
            "multiple_organizations": len(memberships) > 1,
            "organizations": org_briefs,
            "organization_id": active_org.organization_id,
            "organization_name": active_org.organization_name,
            "workspace_id": workspace.workspace_id if workspace else None,
            "workspace_name": workspace.workspace_name if workspace else None,
            "role": active_role.role_name if active_role else "Member"
        }

    async def complete_onboarding(self, user: User, payload: OnboardingRequest) -> Organization:
        """
        Atomically complete organization onboarding for the user.
        Raises ConflictException if organization/slug already exists or user has an organization.
        """
        # 1. Double check uniqueness
        if await self.repo.exists_by_name(payload.org_name):
            raise ConflictException("Organization name is already taken.")
        if await self.repo.exists_by_slug(payload.org_slug):
            raise ConflictException("Organization URL slug is already taken.")

        # 2. Check if user already has an organization
        existing_membership = await self.repo.get_membership_by_user_id(user.user_id)
        if existing_membership:
            raise ConflictException("User already belongs to an organization.")

        try:
            # Wrap all operations inside a sub-transaction (savepoint)
            async with self.db.begin_nested():
                # Update user profile
                await self.user_repo.update(
                    user,
                    user_first_name=payload.owner_first_name,
                    user_last_name=payload.owner_last_name,
                    user_phone=payload.owner_phone
                )

                # Create Organization
                org = await self.repo.create_organization(
                    name=payload.org_name,
                    slug=payload.org_slug,
                    owner_user_id=user.user_id,
                    logo=payload.org_logo,
                    description=payload.org_description
                )

                # Seed Default Roles
                owner_role = await self.repo.create_role(org.organization_id, "Owner", "Organization Owner", is_system=True)
                await self.repo.create_role(org.organization_id, "Admin", "Administrator", is_system=True)
                await self.repo.create_role(org.organization_id, "Teacher", "Faculty Member", is_system=True)
                await self.repo.create_role(org.organization_id, "Student", "Student Scholar", is_system=True)

                # Link user as Organization Owner Member
                await self.repo.create_organization_member(
                    org_id=org.organization_id,
                    user_id=user.user_id,
                    role_id=owner_role.role_id
                )

                # Create first Workspace
                workspace = await self.repo.create_workspace(
                    org_id=org.organization_id,
                    name=payload.workspace_name,
                    created_by=user.user_id
                )

                # Link user as Workspace Member (Owner role)
                await self.repo.create_workspace_member(
                    workspace_id=workspace.workspace_id,
                    user_id=user.user_id,
                    role_id=owner_role.role_id
                )

                return org

        except Exception as e:
            # begin_nested() will rollback automatically on context exit if an exception is raised
            raise e
