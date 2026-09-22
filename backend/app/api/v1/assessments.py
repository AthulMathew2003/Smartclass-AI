import uuid
from typing import List, Optional, Union, Dict, Any
from fastapi import APIRouter, Depends, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.users.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.organizations.models import Organization
from app.modules.rbac.dependencies import get_current_organization, require_permission
from app.modules.rbac.constants import AssessmentPermission, QuestionPermission
from app.modules.assessments.models import AssessmentStatus
from app.modules.assessments.service import AssessmentService
from app.modules.assessments.schemas import (
    AssessmentCreateRequest,
    AssessmentUpdateRequest,
    AssessmentResponse,
    AssessmentAddQuestionRequest,
    AssessmentCreateAndAddQuestionRequest,
    AssessmentQuestionUpdateRequest,
    QuestionReorderRequest,
    AssessmentQuestionResponse,
    StudentAssessmentQuestionResponse
)

router = APIRouter()


# ── Assessment Endpoints ────────────────────────────────────────

@router.get("", response_model=List[AssessmentResponse])
async def list_assessments(
    subject_id: Optional[uuid.UUID] = Query(None, description="Subject ID (optional for global view)"),
    workspace_id: Optional[uuid.UUID] = Query(None, description="Workspace ID (optional)"),
    status: Optional[AssessmentStatus] = Query(None, description="Filter assessments by status"),
    search: Optional[str] = Query(None, description="Search assessments by title, description, or subject name"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.READ))
):
    """List accessible assessments (subject-scoped or global across organization)."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.list_assessments(
        org_id=org.organization_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        subject_id=subject_id,
        workspace_id=workspace_id,
        status_filter=status,
        search=search
    )


@router.post("", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    payload: AssessmentCreateRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.CREATE))
):
    """Create a new assessment for a subject (Teachers/Admins only, starts as DRAFT)."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.create_assessment(
        org_id=org.organization_id,
        created_by_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        payload=payload
    )
    await db.commit()
    return res


@router.get("/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment(
    assessment_id: uuid.UUID,
    subject_id: Optional[uuid.UUID] = Query(None, description="Subject ID (optional)"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.READ))
):
    """Retrieve details of a single assessment."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.get_assessment(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        subject_id=subject_id
    )


@router.patch("/{assessment_id}", response_model=AssessmentResponse)
async def update_assessment(
    assessment_id: uuid.UUID,
    payload: AssessmentUpdateRequest,
    subject_id: Optional[uuid.UUID] = Query(None, description="Subject ID (optional)"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.UPDATE))
):
    """Update an assessment's metadata."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.update_assessment(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        payload=payload,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        subject_id=subject_id
    )
    await db.commit()
    return res


@router.post("/{assessment_id}/publish", response_model=AssessmentResponse)
async def publish_assessment(
    assessment_id: uuid.UUID,
    subject_id: Optional[uuid.UUID] = Query(None, description="Subject ID (optional)"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.PUBLISH))
):
    """Publish a draft assessment (DRAFT -> PUBLISHED)."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.publish_assessment(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        subject_id=subject_id
    )
    await db.commit()
    return res


@router.post("/{assessment_id}/close", response_model=AssessmentResponse)
async def close_assessment(
    assessment_id: uuid.UUID,
    subject_id: Optional[uuid.UUID] = Query(None, description="Subject ID (optional)"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.UPDATE))
):
    """Close an active/published assessment (PUBLISHED/ACTIVE -> CLOSED)."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.close_assessment(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        subject_id=subject_id
    )
    await db.commit()
    return res


@router.post("/{assessment_id}/archive", response_model=AssessmentResponse)
async def archive_assessment(
    assessment_id: uuid.UUID,
    subject_id: Optional[uuid.UUID] = Query(None, description="Subject ID (optional)"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.DELETE))
):
    """Archive an assessment."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.archive_assessment(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        subject_id=subject_id
    )
    await db.commit()
    return res


@router.delete("/{assessment_id}")
async def delete_assessment(
    assessment_id: uuid.UUID,
    subject_id: Optional[uuid.UUID] = Query(None, description="Subject ID (optional)"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.DELETE))
):
    """Delete an assessment."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    await service.delete_assessment(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        subject_id=subject_id
    )
    await db.commit()
    return {"message": "Assessment deleted successfully", "assessment_id": str(assessment_id)}


# ── Assessment Questions Endpoints ──────────────────────────────

@router.get("/{assessment_id}/questions")
async def list_assessment_questions(
    assessment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(QuestionPermission.READ))
):
    """List questions in an assessment (Sanitized for students; full for teachers)."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.list_assessment_questions(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )


@router.post("/{assessment_id}/questions", response_model=AssessmentQuestionResponse, status_code=status.HTTP_201_CREATED)
async def add_or_create_assessment_question(
    assessment_id: uuid.UUID,
    payload: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(QuestionPermission.CREATE))
):
    """
    Add a question to an assessment (Draft only).
    Accepts either:
    1. {"question_id": "...", "marks": 5.0, "order": 1} (from Question Bank)
    2. {"question_type": "...", "question_text": "...", "marks": 5.0, "options": [...]} (inline create)
    """
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)

    if "question_id" in payload and payload.get("question_id"):
        parsed_add = AssessmentAddQuestionRequest.model_validate(payload)
        res = await service.add_question_from_bank(
            org_id=org.organization_id,
            assessment_id=assessment_id,
            requesting_user_id=current_user.user_id,
            is_org_admin=is_org_admin,
            payload=parsed_add
        )
    else:
        parsed_create = AssessmentCreateAndAddQuestionRequest.model_validate(payload)
        res = await service.create_and_add_question(
            org_id=org.organization_id,
            assessment_id=assessment_id,
            requesting_user_id=current_user.user_id,
            is_org_admin=is_org_admin,
            payload=parsed_create
        )

    await db.commit()
    return res


@router.post("/{assessment_id}/questions/from-bank", response_model=AssessmentQuestionResponse, status_code=status.HTTP_201_CREATED)
async def add_question_from_bank(
    assessment_id: uuid.UUID,
    payload: AssessmentAddQuestionRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(QuestionPermission.CREATE))
):
    """Add an existing question from Subject Question Bank to an assessment (creates snapshot)."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.add_question_from_bank(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        payload=payload
    )
    await db.commit()
    return res


@router.post("/{assessment_id}/questions/reorder")
@router.patch("/{assessment_id}/questions/reorder")
async def reorder_assessment_questions(
    assessment_id: uuid.UUID,
    payload: QuestionReorderRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(QuestionPermission.REORDER))
):
    """Reorder questions in a draft assessment."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.reorder_assessment_questions(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        payload=payload
    )
    await db.commit()
    return res


@router.get("/{assessment_id}/questions/{assessment_question_id}")
async def get_assessment_question(
    assessment_id: uuid.UUID,
    assessment_question_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(QuestionPermission.READ))
):
    """Get single assessment question."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.get_assessment_question(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        assessment_question_id=assessment_question_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )


@router.patch("/{assessment_id}/questions/{assessment_question_id}", response_model=AssessmentQuestionResponse)
async def update_assessment_question(
    assessment_id: uuid.UUID,
    assessment_question_id: uuid.UUID,
    payload: AssessmentQuestionUpdateRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(QuestionPermission.UPDATE))
):
    """Update assessment question marks or order (Draft only)."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.update_assessment_question(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        assessment_question_id=assessment_question_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        payload=payload
    )
    await db.commit()
    return res


@router.delete("/{assessment_id}/questions/{assessment_question_id}")
async def remove_assessment_question(
    assessment_id: uuid.UUID,
    assessment_question_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(QuestionPermission.DELETE))
):
    """Remove question from draft assessment."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    await service.remove_assessment_question(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        assessment_question_id=assessment_question_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )
    await db.commit()
    return {"message": "Question removed from assessment successfully", "assessment_question_id": str(assessment_question_id)}
