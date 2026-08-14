import uuid
from typing import List
from fastapi import APIRouter, Depends, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.users.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.organizations.models import Organization
from app.modules.rbac.dependencies import get_current_organization, require_permission
from app.modules.rbac.constants import AssignmentPermission
from app.modules.assignments.service import AssignmentService
from app.modules.assignments.schemas import (
    AssignmentCreateRequest,
    AssignmentUpdateRequest,
    AssignmentResponse
)

router = APIRouter()


@router.get("", response_model=List[AssignmentResponse])
async def list_assignments(
    subject_id: uuid.UUID = Query(..., description="Subject ID to list assignments for"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.READ))
):
    """List accessible assignments for a subject."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.list_assignments(
        org_id=org.organization_id,
        subject_id=subject_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )


@router.post("", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    payload: AssignmentCreateRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.CREATE))
):
    """Create a new assignment for a subject (Teachers/Admins only)."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.create_assignment(
        org_id=org.organization_id,
        created_by_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        payload=payload
    )
    await db.commit()
    return res


@router.get("/{assignment_id}", response_model=AssignmentResponse)
async def get_assignment(
    assignment_id: uuid.UUID,
    subject_id: uuid.UUID = Query(..., description="Subject ID"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.READ))
):
    """Retrieve details of a single assignment."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.get_assignment(
        org_id=org.organization_id,
        subject_id=subject_id,
        assignment_id=assignment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )


@router.patch("/{assignment_id}", response_model=AssignmentResponse)
async def update_assignment(
    assignment_id: uuid.UUID,
    payload: AssignmentUpdateRequest,
    subject_id: uuid.UUID = Query(..., description="Subject ID"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.UPDATE))
):
    """Update an assignment's details or status."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.update_assignment(
        org_id=org.organization_id,
        subject_id=subject_id,
        assignment_id=assignment_id,
        payload=payload,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )
    await db.commit()
    return res


@router.delete("/{assignment_id}", response_model=AssignmentResponse)
async def delete_assignment(
    assignment_id: uuid.UUID,
    subject_id: uuid.UUID = Query(..., description="Subject ID"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.DELETE))
):
    """Soft-delete (archive) an assignment."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.archive_assignment(
        org_id=org.organization_id,
        subject_id=subject_id,
        assignment_id=assignment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )
    await db.commit()
    return res
