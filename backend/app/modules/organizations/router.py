import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, Header, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.modules.users.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.service import OrganizationService
from app.modules.organizations.member_service import MemberService
from app.modules.organizations.dependencies import get_active_organization_id
from app.modules.organizations.schemas import OnboardingRequest, OrganizationStatusResponse, UserMembershipBrief
from app.modules.organizations.models import Organization, Role, Workspace, WorkspaceMember
from app.modules.organizations.member_schemas import (
    MemberCreateRequest,
    MemberUpdateRequest,
    MemberStatusUpdateRequest,
    MemberResponse
)
from sqlalchemy import select
from app.modules.rbac.dependencies import require_permission
from app.modules.rbac.constants import MemberPermission

router = APIRouter()


@router.get("/check-name")
async def check_name(name: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Check if an organization name is available (not taken)."""
    repo = OrganizationRepository(db)
    exists_flag = await repo.exists_by_name(name)
    return {"available": not exists_flag}


@router.get("/check-slug")
async def check_slug(slug: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Check if an organization URL slug is available (not taken)."""
    repo = OrganizationRepository(db)
    exists_flag = await repo.exists_by_slug(slug)
    return {"available": not exists_flag}


@router.get("/status", response_model=OrganizationStatusResponse)
async def get_organization_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve the owner onboarding status of the authenticated user."""
    service = OrganizationService(db)
    return await service.get_user_organization_status(current_user)


@router.get("/memberships", response_model=List[UserMembershipBrief])
async def get_user_memberships(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all active organization memberships for the authenticated user."""
    repo = OrganizationRepository(db)
    memberships = await repo.list_memberships(current_user.user_id)
    org_briefs = []
    for m in memberships:
        org = await db.get(Organization, m.organization_member_organization_id)
        role = await db.get(Role, m.organization_member_role_id)
        if org:
            # Query workspace
            ws_stmt = select(Workspace).join(WorkspaceMember).where(
                WorkspaceMember.workspace_member_user_id == current_user.user_id,
                Workspace.workspace_organization_id == org.organization_id
            )
            ws_res = await db.execute(ws_stmt)
            workspace = ws_res.scalars().first()

            org_briefs.append(
                UserMembershipBrief(
                    organization_id=org.organization_id,
                    organization_name=org.organization_name,
                    organization_slug=org.organization_slug,
                    role_name=role.role_name if role else "Member",
                    workspace_name=workspace.workspace_name if workspace else None
                )
            )
    return org_briefs


@router.post("/onboarding")
async def complete_onboarding(
    payload: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Atomically create organization profile, seed roles, create default workspace, and bind owner roles."""
    service = OrganizationService(db)
    await service.complete_onboarding(current_user, payload)
    await db.commit()
    return {"success": True, "message": "Organization onboarding completed successfully."}


@router.get("/roles")
async def get_organization_roles(
    org_id: uuid.UUID = Depends(get_active_organization_id),
    db: AsyncSession = Depends(get_db)
):
    """List all roles associated with the active organization (system roles + custom roles)."""
    repo = OrganizationRepository(db)
    roles = await repo.get_roles(org_id)
    return [{"role_id": r.role_id, "role_name": r.role_name} for r in roles]


@router.get("/members/check-email")
async def check_member_email(
    email: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(MemberPermission.READ))
):
    """Check if a user is already registered in the system (supporting quick auto-fill)."""
    service = MemberService(db)
    return await service.check_email(email)


@router.get("/members", response_model=List[MemberResponse])
async def list_members(
    search: Optional[str] = Query(None),
    role_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    workspace_id: Optional[uuid.UUID] = Query(None),
    org_id: uuid.UUID = Depends(get_active_organization_id),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(MemberPermission.READ))
):
    """List members belonging to the active organization tenant."""
    service = MemberService(db)
    return await service.list_members(org_id, search, role_id, status, workspace_id)


@router.get("/members/{member_id}", response_model=MemberResponse)
async def get_member_details(
    member_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_active_organization_id),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(MemberPermission.READ))
):
    """Fetch details of a specific member inside the active organization."""
    service = MemberService(db)
    return await service.get_member(org_id, member_id)


@router.post("/members", response_model=MemberResponse)
async def add_member(
    payload: MemberCreateRequest,
    org_id: uuid.UUID = Depends(get_active_organization_id),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(MemberPermission.CREATE))
):
    """Create a new member (reusing profile if the user exists, creating new user profile + temp password if they don't)."""
    service = MemberService(db)
    member_info = await service.create_member(org_id, payload)
    await db.commit()
    return member_info


@router.patch("/members/{member_id}", response_model=MemberResponse)
async def update_member(
    member_id: uuid.UUID,
    payload: MemberUpdateRequest,
    org_id: uuid.UUID = Depends(get_active_organization_id),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(MemberPermission.UPDATE))
):
    """Update local member profiles and roles."""
    service = MemberService(db)
    member_info = await service.update_member(org_id, member_id, payload)
    await db.commit()
    return member_info


@router.patch("/members/{member_id}/status", response_model=MemberResponse)
async def update_member_status(
    member_id: uuid.UUID,
    payload: MemberStatusUpdateRequest,
    org_id: uuid.UUID = Depends(get_active_organization_id),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(MemberPermission.UPDATE))
):
    """Suspend or reactivate a member."""
    service = MemberService(db)
    member_info = await service.update_member_status(org_id, member_id, payload.status)
    await db.commit()
    return member_info


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_member(
    member_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_active_organization_id),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(MemberPermission.DELETE))
):
    """Soft-delete a member by deleting their memberships inside the organization."""
    service = MemberService(db)
    await service.delete_member(org_id, member_id)
    await db.commit()


@router.patch("/members/{user_id}/workspaces")
async def assign_user_workspaces(
    user_id: uuid.UUID,
    workspace_ids: List[uuid.UUID] = Body(...),
    org_id: uuid.UUID = Depends(get_active_organization_id),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(MemberPermission.UPDATE))
):
    """Modify workspace assignments for a user."""
    service = MemberService(db)
    await service.assign_workspaces(org_id, user_id, workspace_ids)
    await db.commit()
    return {"success": True, "message": "Workspaces synchronized successfully."}
