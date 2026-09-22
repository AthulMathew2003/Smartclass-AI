import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.users.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.organizations.models import Organization
from app.modules.rbac.dependencies import get_current_organization, require_permission
from app.modules.rbac.constants import SubjectMaterialPermission
from app.modules.subjects.models import SubjectMaterialStatus
from app.modules.subjects.material_service import SubjectMaterialService
from app.modules.subjects.material_schemas import (
    MaterialUploadUrlRequest,
    MaterialUploadUrlResponse,
    MaterialConfirmRequest,
    MaterialUpdateRequest,
    MaterialResponse,
    MaterialDownloadUrlResponse
)

router = APIRouter()


@router.post("/upload-url", response_model=MaterialUploadUrlResponse, status_code=status.HTTP_201_CREATED)
async def request_material_upload_url(
    subject_id: uuid.UUID,
    payload: MaterialUploadUrlRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(SubjectMaterialPermission.CREATE))
):
    """
    Request a presigned PUT URL for uploading course materials directly to S3.
    Requires teacher assignment to subject or organization admin privileges.
    """
    service = SubjectMaterialService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.request_upload_url(
        org_id=org.organization_id,
        subject_id=subject_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        payload=payload
    )
    await db.commit()
    return res


@router.post("/{material_id}/confirm", response_model=MaterialResponse)
async def confirm_material_upload(
    subject_id: uuid.UUID,
    material_id: uuid.UUID,
    payload: MaterialConfirmRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(SubjectMaterialPermission.CREATE))
):
    """
    Confirm that an uploaded course material object exists in S3 and mark it active.
    """
    service = SubjectMaterialService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.confirm_upload(
        org_id=org.organization_id,
        subject_id=subject_id,
        material_id=material_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        payload=payload
    )
    await db.commit()
    return res


@router.get("", response_model=List[MaterialResponse])
async def list_materials(
    subject_id: uuid.UUID,
    category: Optional[str] = Query(None, description="Filter by category name"),
    search: Optional[str] = Query(None, description="Search by title, description, or filename"),
    status: Optional[SubjectMaterialStatus] = Query(None, description="Filter by status (teachers/admins only)"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(SubjectMaterialPermission.READ))
):
    """
    List all active course materials for a subject.
    """
    service = SubjectMaterialService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.list_materials(
        org_id=org.organization_id,
        subject_id=subject_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        category=category,
        search=search,
        status_filter=status
    )


@router.get("/{material_id}", response_model=MaterialResponse)
async def get_material(
    subject_id: uuid.UUID,
    material_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(SubjectMaterialPermission.READ))
):
    """
    Retrieve details and metadata for a specific course material.
    """
    service = SubjectMaterialService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.get_material(
        org_id=org.organization_id,
        subject_id=subject_id,
        material_id=material_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )


@router.patch("/{material_id}", response_model=MaterialResponse)
async def update_material(
    subject_id: uuid.UUID,
    material_id: uuid.UUID,
    payload: MaterialUpdateRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(SubjectMaterialPermission.UPDATE))
):
    """
    Update course material metadata (title, description, category).
    """
    service = SubjectMaterialService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.update_material(
        org_id=org.organization_id,
        subject_id=subject_id,
        material_id=material_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        payload=payload
    )
    await db.commit()
    return res


@router.delete("/{material_id}")
async def archive_material(
    subject_id: uuid.UUID,
    material_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(SubjectMaterialPermission.DELETE))
):
    """
    Soft archive a course material item.
    """
    service = SubjectMaterialService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.archive_material(
        org_id=org.organization_id,
        subject_id=subject_id,
        material_id=material_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )
    await db.commit()
    return res


@router.get("/{material_id}/download-url", response_model=MaterialDownloadUrlResponse)
async def get_material_download_url(
    subject_id: uuid.UUID,
    material_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(SubjectMaterialPermission.READ))
):
    """
    Generate a secure short-lived presigned GET URL for downloading or browser-viewing a course material.
    """
    service = SubjectMaterialService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.get_download_url(
        org_id=org.organization_id,
        subject_id=subject_id,
        material_id=material_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )
