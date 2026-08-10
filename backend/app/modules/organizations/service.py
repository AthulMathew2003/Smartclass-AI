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


from fastapi import HTTPException
from app.modules.organizations.constants import SystemRole

class OrganizationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = OrganizationRepository(db)
        self.user_repo = UserRepository(db)

    async def get_user_organization_status(self, user: User, active_org_id: Optional[uuid.UUID] = None):
        """Check if the user owns any organization, returning onboarding status."""
        stmt = select(Organization).where(Organization.organization_owner_user_id == user.user_id)
        res = await self.db.execute(stmt)
        org = res.scalars().first()
        return {"has_organization": org is not None}

    async def complete_onboarding(self, user: User, payload: OnboardingRequest) -> Organization:
        """
        Atomically complete organization onboarding for the user.
        Raises ConflictException if organization/slug already exists or user already owns an organization.
        """
        # 1. Double check uniqueness
        if await self.repo.exists_by_name(payload.org_name):
            raise ConflictException("Organization name is already taken.")
        if await self.repo.exists_by_slug(payload.org_slug):
            raise ConflictException("Organization URL slug is already taken.")

        # 2. Check if user already owns an organization
        stmt = select(Organization).where(Organization.organization_owner_user_id == user.user_id)
        res = await self.db.execute(stmt)
        if res.scalars().first():
            raise ConflictException("User already owns an organization.")

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

                # Retrieve the Owner system role from database
                role_stmt = select(Role).where(
                    Role.role_organization_id.is_(None),
                    Role.role_is_system.is_(True),
                    Role.role_name == SystemRole.OWNER
                )
                role_res = await self.db.execute(role_stmt)
                owner_role = role_res.scalars().first()
                if not owner_role:
                    raise HTTPException(status_code=500, detail=f"System role '{SystemRole.OWNER}' is missing. Database is not initialized correctly.")

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
