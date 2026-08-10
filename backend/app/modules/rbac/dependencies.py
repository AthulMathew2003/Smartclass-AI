import uuid
from fastapi import Request, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.modules.users.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.organizations.models import Organization, OrganizationMemberStatus
from app.modules.organizations.repository import OrganizationRepository
from app.modules.rbac.service import RBACService


async def get_current_organization(
    x_organization_id: str = Header(..., alias="X-Organization-Id"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Organization:
    """
    Resolve the active organization context for the request.
    Validates X-Organization-Id header and membership active status.
    """
    try:
        org_uuid = uuid.UUID(x_organization_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid organization ID format.")

    repo = OrganizationRepository(db)
    data = await repo.get_organization_member_by_user_id(org_uuid, current_user.user_id)
    if not data:
        raise HTTPException(status_code=403, detail="Access denied to this organization.")

    user, membership, role = data
    if membership.organization_member_status == OrganizationMemberStatus.SUSPENDED:
        raise HTTPException(status_code=403, detail="Your membership in this organization has been suspended.")

    org = await db.get(Organization, org_uuid)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")
        
    if org.organization_status != "active": # Assuming OrganizationStatus.ACTIVE is "active"
        raise HTTPException(status_code=403, detail="This organization has been suspended.")
        
    return org


async def get_request_permissions(
    request: Request,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db)
) -> list[str]:
    """Fetch and cache user permissions in the current request state for tenant isolation."""
    if not hasattr(request.state, "permissions_cache"):
        service = RBACService(db)
        perms = await service.get_user_permissions(current_user.user_id, org.organization_id)
        request.state.permissions_cache = perms
    return request.state.permissions_cache


def require_permission(permission: str):
    """FastAPI dependency to enforce role-permission access control."""
    async def dependency(
        permissions: list[str] = Depends(get_request_permissions)
    ) -> None:
        if permission not in permissions:
            raise HTTPException(status_code=403, detail="Access denied. Insufficient permissions.")
    return dependency
