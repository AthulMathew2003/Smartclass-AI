import uuid
from typing import Optional
from fastapi import Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.modules.users.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.models import OrganizationMemberStatus
from app.core.exceptions import ForbiddenException, ConflictException


async def get_active_organization_id(
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-Id"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> uuid.UUID:
    """
    Resolve the active organization context for the request.
    Validates X-Organization-Id headers or falls back to the user's first active membership.
    """
    repo = OrganizationRepository(db)
    
    if x_organization_id:
        try:
            org_uuid = uuid.UUID(x_organization_id)
        except ValueError:
            raise ForbiddenException("Invalid organization ID format.")
            
        # Verify user belongs to this organization
        data = await repo.get_organization_member_by_user_id(org_uuid, current_user.user_id)
        if not data:
            raise ForbiddenException("Access denied to this organization.")
            
        user, membership, role = data
        if membership.organization_member_status == OrganizationMemberStatus.SUSPENDED:
            raise ForbiddenException("Your membership in this organization has been suspended.")
            
        return org_uuid

    # Fallback to first active membership
    memberships = await repo.list_memberships(current_user.user_id)
    if not memberships:
        raise ConflictException("No active organization membership found.")
        
    return memberships[0].organization_member_organization_id
