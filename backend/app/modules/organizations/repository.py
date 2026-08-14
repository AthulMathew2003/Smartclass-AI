import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select, exists, and_, delete, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.models import User
from app.modules.organizations.models import (
    Organization,
    Workspace,
    Role,
    OrganizationMember,
    WorkspaceMember,
    OrganizationStatus,
    WorkspaceStatus,
    OrganizationMemberStatus
)


class OrganizationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def exists_by_name(self, name: str) -> bool:
        """Check if an organization exists with the given name (case-insensitive)."""
        stmt = select(exists().where(
            Organization.organization_name.ilike(name.strip())
        ))
        result = await self.db.execute(stmt)
        return bool(result.scalar())

    async def exists_by_slug(self, slug: str) -> bool:
        """Check if an organization exists with the given URL-friendly slug (case-insensitive)."""
        stmt = select(exists().where(
            Organization.organization_slug == slug.lower().strip()
        ))
        result = await self.db.execute(stmt)
        return bool(result.scalar())

    async def get_membership(self, user_id: uuid.UUID, org_id: uuid.UUID) -> Optional[OrganizationMember]:
        """Fetch a user's membership within a specific organization."""
        stmt = (
            select(OrganizationMember)
            .where(
                OrganizationMember.organization_member_user_id == user_id,
                OrganizationMember.organization_member_organization_id == org_id,
                OrganizationMember.organization_member_status == OrganizationMemberStatus.ACTIVE
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_memberships(self, user_id: uuid.UUID) -> List[OrganizationMember]:
        """Return all active organization memberships the user belongs to."""
        stmt = (
            select(OrganizationMember)
            .where(
                OrganizationMember.organization_member_user_id == user_id,
                OrganizationMember.organization_member_status == OrganizationMemberStatus.ACTIVE
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())



    async def get_organization_members(
        self,
        org_id: uuid.UUID,
        search: Optional[str] = None,
        role_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        workspace_id: Optional[uuid.UUID] = None
    ) -> List[Tuple[User, OrganizationMember, Role]]:
        """Fetch organization member profiles along with their user identities and roles, applying filters."""
        stmt = (
            select(User, OrganizationMember, Role)
            .join(OrganizationMember, User.user_id == OrganizationMember.organization_member_user_id)
            .join(Role, OrganizationMember.organization_member_role_id == Role.role_id)
            .where(OrganizationMember.organization_member_organization_id == org_id)
        )

        if role_id:
            stmt = stmt.where(OrganizationMember.organization_member_role_id == role_id)
        if status:
            stmt = stmt.where(OrganizationMember.organization_member_status == status)
        if workspace_id:
            stmt = stmt.join(WorkspaceMember, User.user_id == WorkspaceMember.workspace_member_user_id).where(WorkspaceMember.workspace_member_workspace_id == workspace_id)
        if search:
            search_pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    User.user_email.ilike(search_pattern),
                    User.user_first_name.ilike(search_pattern),
                    User.user_last_name.ilike(search_pattern)
                )
            )

        result = await self.db.execute(stmt)
        return list(result.all())

    async def get_organization_member_by_id(
        self,
        org_id: uuid.UUID,
        member_id: uuid.UUID
    ) -> Optional[Tuple[User, OrganizationMember, Role]]:
        """Retrieve a specific member's profile details."""
        stmt = (
            select(User, OrganizationMember, Role)
            .join(OrganizationMember, User.user_id == OrganizationMember.organization_member_user_id)
            .join(Role, OrganizationMember.organization_member_role_id == Role.role_id)
            .where(
                OrganizationMember.organization_member_organization_id == org_id,
                OrganizationMember.organization_member_id == member_id
            )
        )
        result = await self.db.execute(stmt)
        return result.first()

    async def get_organization_member_by_user_id(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[Tuple[User, OrganizationMember, Role]]:
        """Retrieve a user's membership details for a specific organization."""
        stmt = (
            select(User, OrganizationMember, Role)
            .join(OrganizationMember, User.user_id == OrganizationMember.organization_member_user_id)
            .join(Role, OrganizationMember.organization_member_role_id == Role.role_id)
            .where(
                OrganizationMember.organization_member_organization_id == org_id,
                OrganizationMember.organization_member_user_id == user_id
            )
        )
        result = await self.db.execute(stmt)
        return result.first()

    async def get_workspaces(self, org_id: uuid.UUID) -> List[Workspace]:
        """Fetch all workspaces registered under an organization."""
        stmt = select(Workspace).where(Workspace.workspace_organization_id == org_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_workspace_by_id(self, workspace_id: uuid.UUID) -> Optional[Workspace]:
        """Fetch a single workspace by ID."""
        return await self.db.get(Workspace, workspace_id)

    async def get_user_workspace_assignments(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> List[Workspace]:
        """Fetch all workspaces a user is assigned to within a specific organization."""
        stmt = (
            select(Workspace)
            .join(WorkspaceMember, Workspace.workspace_id == WorkspaceMember.workspace_member_workspace_id)
            .where(
                Workspace.workspace_organization_id == org_id,
                WorkspaceMember.workspace_member_user_id == user_id
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_user_workspace_memberships(self, org_id: uuid.UUID, user_id: uuid.UUID):
        """Remove a user from all workspaces in an organization (prior to re-assignment)."""
        workspaces_subquery = (
            select(Workspace.workspace_id)
            .where(Workspace.workspace_organization_id == org_id)
        )
        # SQLAlchemy execute delete
        stmt = (
            delete(WorkspaceMember)
            .where(
                and_(
                    WorkspaceMember.workspace_member_user_id == user_id,
                    WorkspaceMember.workspace_member_workspace_id.in_(workspaces_subquery)
                )
            )
        )
        await self.db.execute(stmt)

    async def get_workspace_members(self, workspace_id: uuid.UUID) -> List[Tuple[User, Role]]:
        """List all members assigned to a workspace."""
        stmt = (
            select(User, Role)
            .join(WorkspaceMember, User.user_id == WorkspaceMember.workspace_member_user_id)
            .join(Role, WorkspaceMember.workspace_member_role_id == Role.role_id)
            .where(WorkspaceMember.workspace_member_workspace_id == workspace_id)
        )
        result = await self.db.execute(stmt)
        return list(result.all())

    async def get_roles(self, org_id: uuid.UUID) -> List[Role]:
        """Fetch all available roles for an organization (including global system roles)."""
        stmt = (
            select(Role)
            .where(
                or_(
                    Role.role_organization_id == org_id,
                    Role.role_organization_id.is_(None)
                )
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_organization(
        self,
        name: str,
        slug: str,
        owner_user_id: uuid.UUID,
        logo: Optional[str] = None,
        description: Optional[str] = None
    ) -> Organization:
        """Create a new organization profile."""
        org = Organization(
            organization_name=name.strip(),
            organization_slug=slug.lower().strip(),
            organization_logo=logo,
            organization_description=description,
            organization_owner_user_id=owner_user_id,
            organization_status=OrganizationStatus.ACTIVE
        )
        self.db.add(org)
        await self.db.flush()
        return org

    async def create_role(
        self,
        org_id: Optional[uuid.UUID],
        name: str,
        description: Optional[str] = None,
        is_system: bool = False
    ) -> Role:
        """Create an organization role."""
        role = Role(
            role_organization_id=org_id,
            role_name=name.strip(),
            role_description=description,
            role_is_system=is_system
        )
        self.db.add(role)
        await self.db.flush()
        return role

    async def create_organization_member(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        role_id: uuid.UUID
    ) -> OrganizationMember:
        """Associate a user with an organization under a specific role."""
        member = OrganizationMember(
            organization_member_organization_id=org_id,
            organization_member_user_id=user_id,
            organization_member_role_id=role_id,
            organization_member_status=OrganizationMemberStatus.ACTIVE
        )
        self.db.add(member)
        await self.db.flush()
        return member

    async def get_workspaces_by_ids(self, workspace_ids: set[uuid.UUID]) -> List[Workspace]:
        """Fetch multiple workspaces by their IDs."""
        stmt = select(Workspace).where(Workspace.workspace_id.in_(workspace_ids))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_workspace(
        self,
        org_id: uuid.UUID,
        name: str,
        created_by: uuid.UUID,
        description: Optional[str] = None
    ) -> Workspace:
        """Create a new workspace under an organization."""
        ws = Workspace(
            workspace_organization_id=org_id,
            workspace_name=name.strip(),
            workspace_description=description,
            workspace_status=WorkspaceStatus.ACTIVE,
            workspace_created_by=created_by
        )
        self.db.add(ws)
        await self.db.flush()
        return ws

    async def create_workspace_member(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        role_id: uuid.UUID
    ) -> WorkspaceMember:
        """Add a member to a workspace under a specific role."""
        member = WorkspaceMember(
            workspace_member_workspace_id=workspace_id,
            workspace_member_user_id=user_id,
            workspace_member_role_id=role_id
        )
        self.db.add(member)
        await self.db.flush()
        return member

    async def exists_workspace_name(
        self,
        org_id: uuid.UUID,
        name: str,
        exclude_workspace_id: Optional[uuid.UUID] = None
    ) -> bool:
        """Check if a workspace name exists within an organization (case-insensitive)."""
        stmt = select(Workspace).where(
            Workspace.workspace_organization_id == org_id,
            func.lower(Workspace.workspace_name) == name.strip().lower()
        )
        if exclude_workspace_id:
            stmt = stmt.where(Workspace.workspace_id != exclude_workspace_id)
        result = await self.db.execute(stmt)
        return result.scalars().first() is not None

    async def count_workspace_members(self, workspace_id: uuid.UUID) -> int:
        """Count total members assigned to a workspace."""
        stmt = select(WorkspaceMember).where(WorkspaceMember.workspace_member_workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        return len(result.scalars().all())

    async def count_workspace_subjects(self, workspace_id: uuid.UUID) -> int:
        """Count total active subjects in a workspace."""
        from app.modules.subjects.models import Subject, SubjectStatus
        stmt = select(Subject).where(
            Subject.subject_workspace_id == workspace_id,
            Subject.subject_status == SubjectStatus.ACTIVE
        )
        result = await self.db.execute(stmt)
        return len(result.scalars().all())

    async def update_workspace(
        self,
        workspace: Workspace,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[WorkspaceStatus] = None
    ) -> Workspace:
        """Update metadata or status of a workspace."""
        if name is not None:
            workspace.workspace_name = name.strip()
        if description is not None:
            workspace.workspace_description = description
        if status is not None:
            workspace.workspace_status = status

        await self.db.flush()
        return workspace

