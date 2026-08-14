import uuid
from typing import List
from fastapi import APIRouter, Depends, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.modules.users.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.organizations.models import Organization
from app.modules.rbac.dependencies import get_current_organization, require_permission
from app.modules.subjects.service import SubjectService
from app.modules.subjects.schemas import (
    SubjectCreateRequest,
    SubjectUpdateRequest,
    SubjectResponse,
    SubjectTeacherAddRequest,
    SubjectTeacherResponse
)

router = APIRouter()


@router.get("", response_model=List[SubjectResponse])
async def list_subjects(
    request: Request,
    workspace_id: uuid.UUID = Query(..., description="The workspace ID to list subjects for"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("subject.read"))
):
    service = SubjectService(db)
    perms = getattr(request.state, "permissions_cache", [])
    is_org_admin = "subject.delete" in perms

    return await service.list_accessible_subjects(
        user_id=current_user.user_id,
        org_id=org.organization_id,
        workspace_id=workspace_id,
        is_org_admin=is_org_admin
    )


@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(
    payload: SubjectCreateRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("subject.create"))
):
    service = SubjectService(db)
    res = await service.create_subject(
        org_id=org.organization_id,
        workspace_id=payload.workspace_id,
        created_by_user_id=current_user.user_id,
        payload=payload
    )
    await db.commit()
    return res


@router.get("/{subject_id}", response_model=SubjectResponse)
async def get_subject(
    subject_id: uuid.UUID,
    request: Request,
    workspace_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("subject.read"))
):
    service = SubjectService(db)
    perms = getattr(request.state, "permissions_cache", [])
    is_org_admin = "subject.delete" in perms
    return await service.get_subject(
        subject_id,
        workspace_id,
        org.organization_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )


@router.patch("/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: uuid.UUID,
    payload: SubjectUpdateRequest,
    request: Request,
    workspace_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("subject.update"))
):
    service = SubjectService(db)
    perms = getattr(request.state, "permissions_cache", [])
    is_org_admin = "subject.delete" in perms
    res = await service.update_subject(
        subject_id,
        org.organization_id,
        workspace_id,
        payload,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )
    await db.commit()
    return res


@router.delete("/{subject_id}", response_model=SubjectResponse)
async def archive_subject(
    subject_id: uuid.UUID,
    workspace_id: uuid.UUID = Query(...),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("subject.delete"))
):
    service = SubjectService(db)
    res = await service.archive_subject(subject_id, org.organization_id, workspace_id)
    await db.commit()
    return res


# ── Subject Teacher endpoints ───────────────────────────────────────────

@router.get("/{subject_id}/teachers", response_model=List[SubjectTeacherResponse])
async def list_subject_teachers(
    subject_id: uuid.UUID,
    request: Request,
    workspace_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("subject.read"))
):
    service = SubjectService(db)
    perms = getattr(request.state, "permissions_cache", [])
    is_org_admin = "subject.delete" in perms
    return await service.get_subject_teachers(
        subject_id,
        org.organization_id,
        workspace_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )


@router.post("/{subject_id}/teachers", response_model=SubjectTeacherResponse, status_code=status.HTTP_201_CREATED)
async def add_subject_teacher(
    subject_id: uuid.UUID,
    payload: SubjectTeacherAddRequest,
    request: Request,
    workspace_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("subject.teacher.add"))
):
    service = SubjectService(db)
    perms = getattr(request.state, "permissions_cache", [])
    is_org_admin = "subject.delete" in perms
    res = await service.add_subject_teacher(
        subject_id=subject_id,
        org_id=org.organization_id,
        workspace_id=workspace_id,
        payload=payload,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )
    await db.commit()
    return res


@router.delete("/{subject_id}/teachers/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_subject_teacher(
    subject_id: uuid.UUID,
    user_id: uuid.UUID,
    request: Request,
    workspace_id: uuid.UUID = Query(...),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("subject.teacher.remove"))
):
    service = SubjectService(db)
    perms = getattr(request.state, "permissions_cache", [])
    is_org_admin = "subject.delete" in perms
    await service.remove_subject_teacher(
        subject_id=subject_id,
        user_id=user_id,
        org_id=org.organization_id,
        workspace_id=workspace_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )
    await db.commit()
    return None
