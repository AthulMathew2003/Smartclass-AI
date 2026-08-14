import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.users.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.organizations.models import Organization
from app.modules.rbac.dependencies import get_current_organization, require_permission
from app.modules.rbac.constants import AssignmentPermission
from app.modules.assignments.models import AssignmentStatus
from app.modules.assignments.service import AssignmentService
from app.modules.assignments.schemas import (
    AssignmentCreateRequest,
    AssignmentUpdateRequest,
    AssignmentResponse,
    AttachmentUploadUrlRequest,
    AttachmentUploadUrlResponse,
    AttachmentConfirmRequest,
    AttachmentResponse,
    AttachmentDownloadUrlResponse
)

router = APIRouter()


@router.get("", response_model=List[AssignmentResponse])
async def list_assignments(
    subject_id: uuid.UUID = Query(..., description="Subject ID to list assignments for"),
    status: Optional[AssignmentStatus] = Query(None, description="Filter assignments by status"),
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
        is_org_admin=is_org_admin,
        status_filter=status
    )


@router.post("", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    payload: AssignmentCreateRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.CREATE))
):
    """Create a new assignment for a subject (Teachers/Admins only, starts as DRAFT)."""
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
    """Update an assignment's title, description, or due date."""
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


@router.post("/{assignment_id}/publish", response_model=AssignmentResponse)
async def publish_assignment(
    assignment_id: uuid.UUID,
    subject_id: uuid.UUID = Query(..., description="Subject ID"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.UPDATE))
):
    """Publish a draft assignment (DRAFT -> PUBLISHED)."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.publish_assignment(
        org_id=org.organization_id,
        subject_id=subject_id,
        assignment_id=assignment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )
    await db.commit()
    return res


@router.post("/{assignment_id}/close", response_model=AssignmentResponse)
async def close_assignment(
    assignment_id: uuid.UUID,
    subject_id: uuid.UUID = Query(..., description="Subject ID"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.UPDATE))
):
    """Close an active assignment (PUBLISHED -> CLOSED)."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.close_assignment(
        org_id=org.organization_id,
        subject_id=subject_id,
        assignment_id=assignment_id,
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


# ── Assignment Attachment Endpoints (Step 10.3A) ─────────────────

@router.post("/{assignment_id}/attachments/upload-url", response_model=AttachmentUploadUrlResponse)
async def request_attachment_upload_url(
    assignment_id: uuid.UUID,
    payload: AttachmentUploadUrlRequest,
    subject_id: uuid.UUID = Query(..., description="Subject ID"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.UPDATE))
):
    """Request a short-lived presigned S3 upload URL for an assignment attachment."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.request_attachment_upload_url(
        org_id=org.organization_id,
        subject_id=subject_id,
        assignment_id=assignment_id,
        payload=payload,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )


@router.post("/{assignment_id}/attachments/confirm", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
async def confirm_attachment_upload(
    assignment_id: uuid.UUID,
    payload: AttachmentConfirmRequest,
    subject_id: uuid.UUID = Query(..., description="Subject ID"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.UPDATE))
):
    """Confirm S3 upload and record attachment metadata in database."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.confirm_attachment_upload(
        org_id=org.organization_id,
        subject_id=subject_id,
        assignment_id=assignment_id,
        payload=payload,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )
    await db.commit()
    return res


@router.get("/{assignment_id}/attachments", response_model=List[AttachmentResponse])
async def list_attachments(
    assignment_id: uuid.UUID,
    subject_id: uuid.UUID = Query(..., description="Subject ID"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.READ))
):
    """List attachments for an assignment."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.list_attachments(
        org_id=org.organization_id,
        subject_id=subject_id,
        assignment_id=assignment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )


@router.get("/{assignment_id}/attachments/{attachment_id}/download-url", response_model=AttachmentDownloadUrlResponse)
async def get_attachment_download_url(
    assignment_id: uuid.UUID,
    attachment_id: uuid.UUID,
    subject_id: uuid.UUID = Query(..., description="Subject ID"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.READ))
):
    """Get a short-lived presigned GET URL for downloading an attachment."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.get_attachment_download_url(
        org_id=org.organization_id,
        subject_id=subject_id,
        assignment_id=assignment_id,
        attachment_id=attachment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )


@router.delete("/{assignment_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    assignment_id: uuid.UUID,
    attachment_id: uuid.UUID,
    subject_id: uuid.UUID = Query(..., description="Subject ID"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssignmentPermission.UPDATE))
):
    """Delete an assignment attachment (S3 object and database row)."""
    service = AssignmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    await service.delete_attachment(
        org_id=org.organization_id,
        subject_id=subject_id,
        assignment_id=assignment_id,
        attachment_id=attachment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )
    await db.commit()
