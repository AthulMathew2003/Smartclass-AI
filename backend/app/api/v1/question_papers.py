"""
Question Paper Draft API Router (Step 10.16).

All endpoints are subject-scoped under /subjects/{subject_id}/question-paper-drafts.
Strict tenant isolation and teacher/admin RBAC are enforced on all routes.
Internal generation metadata and raw AI responses are never exposed to clients.
"""
import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.users.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.organizations.models import Organization
from app.modules.rbac.dependencies import get_current_organization, require_permission
from app.modules.rbac.constants import AssessmentPermission
from app.modules.assessments.qp_service import QuestionPaperGenerationService
from app.modules.assessments.qp_schemas import (
    QpGenerateRequest,
    QpDraftResponse,
    QpDraftListItem,
    QpDraftQuestionUpdateInput,
    QpRegenerateQuestionRequest,
    QpConvertRequest,
    QpMaterialListResponse,
    QpMaterialSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Course Materials for Paper Generation ───────────────────────

@router.get("/materials", response_model=QpMaterialListResponse)
async def list_materials_for_qp(
    subject_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.READ)),
):
    """
    List active course materials for a subject with their index status and chunk count.
    Used by teachers on Step A of question paper generation.
    """
    service = QuestionPaperGenerationService(db)
    is_org_admin = await service.assessment_repo.is_user_org_admin(
        current_user.user_id, org.organization_id
    )
    subject, materials = await service.list_subject_materials(
        org_id=org.organization_id,
        subject_id=subject_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
    )
    summaries = [
        QpMaterialSummary(
            material_id=m.material_id,
            title=m.material_title,
            original_filename=m.material_original_filename,
            index_status=str(
                m.material_index_status.value
                if hasattr(m.material_index_status, "value")
                else m.material_index_status
            ),
            chunk_count=m.material_chunk_count or 0,
        )
        for m in materials
    ]
    return QpMaterialListResponse(
        subject_id=subject.subject_id,
        subject_name=subject.subject_name,
        materials=summaries,
    )


# ── Drafts List & Generate ──────────────────────────────────────

@router.get("", response_model=List[QpDraftListItem])
async def list_drafts(
    subject_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.READ)),
):
    """List all question paper drafts for this subject."""
    service = QuestionPaperGenerationService(db)
    is_org_admin = await service.assessment_repo.is_user_org_admin(
        current_user.user_id, org.organization_id
    )
    return await service.list_drafts(
        org_id=org.organization_id,
        subject_id=subject_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
    )


@router.post("/generate", response_model=QpDraftResponse, status_code=status.HTTP_201_CREATED)
async def generate_draft(
    subject_id: uuid.UUID,
    payload: QpGenerateRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.CREATE)),
):
    """
    Generate an AI question paper draft from selected course materials.
    Questions are strictly grounded in the selected materials.
    The resulting draft remains unpublished until explicitly converted.
    """
    service = QuestionPaperGenerationService(db)
    is_org_admin = await service.assessment_repo.is_user_org_admin(
        current_user.user_id, org.organization_id
    )
    return await service.generate_draft(
        org_id=org.organization_id,
        subject_id=subject_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        config=payload,
    )


# ── Single Draft Operations ─────────────────────────────────────

@router.get("/{draft_id}", response_model=QpDraftResponse)
async def get_draft(
    subject_id: uuid.UUID,
    draft_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.READ)),
):
    """Get full details of a question paper draft including questions and validation results."""
    service = QuestionPaperGenerationService(db)
    is_org_admin = await service.assessment_repo.is_user_org_admin(
        current_user.user_id, org.organization_id
    )
    return await service.get_draft(
        org_id=org.organization_id,
        subject_id=subject_id,
        draft_id=draft_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
    )


@router.patch("/{draft_id}", response_model=QpDraftResponse)
async def update_draft_metadata(
    subject_id: uuid.UUID,
    draft_id: uuid.UUID,
    title: Optional[str] = Query(None, min_length=1, max_length=255),
    description: Optional[str] = Query(None, max_length=5000),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.UPDATE)),
):
    """Update draft title and/or description."""
    service = QuestionPaperGenerationService(db)
    is_org_admin = await service.assessment_repo.is_user_org_admin(
        current_user.user_id, org.organization_id
    )
    return await service.update_draft(
        org_id=org.organization_id,
        subject_id=subject_id,
        draft_id=draft_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        title=title,
        description=description,
    )


@router.patch("/{draft_id}/questions/{dq_id}", response_model=QpDraftResponse)
async def update_draft_question(
    subject_id: uuid.UUID,
    draft_id: uuid.UUID,
    dq_id: uuid.UUID,
    payload: QpDraftQuestionUpdateInput,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.UPDATE)),
):
    """Edit a single question in a draft (text, marks, difficulty, options, rubric)."""
    service = QuestionPaperGenerationService(db)
    is_org_admin = await service.assessment_repo.is_user_org_admin(
        current_user.user_id, org.organization_id
    )
    return await service.update_question(
        org_id=org.organization_id,
        subject_id=subject_id,
        draft_id=draft_id,
        dq_id=dq_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        payload=payload,
    )


@router.post("/{draft_id}/questions/{dq_id}/regenerate", response_model=QpDraftResponse)
async def regenerate_single_question(
    subject_id: uuid.UUID,
    draft_id: uuid.UUID,
    dq_id: uuid.UUID,
    payload: QpRegenerateQuestionRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.UPDATE)),
):
    """
    Regenerate a single question without re-generating the entire paper.
    Retrieval is strictly scoped to the draft's original selected material set.
    """
    service = QuestionPaperGenerationService(db)
    is_org_admin = await service.assessment_repo.is_user_org_admin(
        current_user.user_id, org.organization_id
    )
    return await service.regenerate_question(
        org_id=org.organization_id,
        subject_id=subject_id,
        draft_id=draft_id,
        dq_id=dq_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        payload=payload,
    )


@router.post("/{draft_id}/validate", response_model=QpDraftResponse)
async def validate_draft(
    subject_id: uuid.UUID,
    draft_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.READ)),
):
    """Re-run deterministic server-side validation on the draft."""
    service = QuestionPaperGenerationService(db)
    is_org_admin = await service.assessment_repo.is_user_org_admin(
        current_user.user_id, org.organization_id
    )
    return await service.validate_draft(
        org_id=org.organization_id,
        subject_id=subject_id,
        draft_id=draft_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
    )


@router.post("/{draft_id}/convert")
async def convert_draft_to_assessment(
    subject_id: uuid.UUID,
    draft_id: uuid.UUID,
    payload: QpConvertRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.CREATE)),
):
    """
    Convert an approved question paper draft into an Assessment.
    Creates Assessment (DRAFT status), QuestionBankItems, and AssessmentQuestions.
    """
    service = QuestionPaperGenerationService(db)
    is_org_admin = await service.assessment_repo.is_user_org_admin(
        current_user.user_id, org.organization_id
    )
    return await service.convert_draft_to_assessment(
        org_id=org.organization_id,
        subject_id=subject_id,
        draft_id=draft_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        payload=payload,
    )


@router.delete("/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_draft(
    subject_id: uuid.UUID,
    draft_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.DELETE)),
):
    """Discard an unconverted draft."""
    service = QuestionPaperGenerationService(db)
    is_org_admin = await service.assessment_repo.is_user_org_admin(
        current_user.user_id, org.organization_id
    )
    await service.delete_draft(
        org_id=org.organization_id,
        subject_id=subject_id,
        draft_id=draft_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
    )
