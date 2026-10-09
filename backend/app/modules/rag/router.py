import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.users.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.organizations.models import Organization
from app.modules.rbac.dependencies import get_current_organization, require_permission
from app.modules.rbac.constants import SubjectMaterialPermission, SubjectPermission
from app.modules.rag.service import RagService
from app.modules.rag.schemas import (
    RagSearchRequest,
    RagSearchResponse,
    RagIndexStatusResponse,
    RagReindexRequest,
)

router = APIRouter()


@router.post("/search", response_model=RagSearchResponse)
async def search_materials(
    payload: RagSearchRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(SubjectPermission.READ)),
):
    """
    Execute authorization-enforced semantic search over indexed subject materials.
    Returns relevant chunks and source citations with tenant isolation.
    """
    service = RagService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.search(
        org_id=org.organization_id,
        subject_id=payload.subject_id,
        query=payload.query,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        top_k=payload.top_k or 5,
    )


@router.post(
    "/subjects/{subject_id}/materials/{material_id}/reindex",
    response_model=RagIndexStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def reindex_material(
    subject_id: uuid.UUID,
    material_id: uuid.UUID,
    payload: RagReindexRequest = RagReindexRequest(),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(SubjectMaterialPermission.CREATE)),
):
    """
    Trigger re-indexing of a subject material (Teachers / Admins only).
    """
    service = RagService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    material = await service.index_material(
        org_id=org.organization_id,
        subject_id=subject_id,
        material_id=material_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        force=payload.force,
    )
    await db.commit()
    return RagIndexStatusResponse(
        material_id=material.material_id,
        status=material.material_index_status.value if hasattr(material.material_index_status, "value") else str(material.material_index_status),
        indexed_at=material.material_indexed_at,
        chunk_count=material.material_chunk_count or 0,
        content_hash=material.material_content_hash,
        error=material.material_index_error,
    )


@router.get(
    "/subjects/{subject_id}/materials/{material_id}/index-status",
    response_model=RagIndexStatusResponse,
)
async def get_material_index_status(
    subject_id: uuid.UUID,
    material_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(SubjectMaterialPermission.READ)),
):
    """
    Check the current RAG index status of a subject material.
    """
    service = RagService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.get_index_status(
        org_id=org.organization_id,
        subject_id=subject_id,
        material_id=material_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
    )
