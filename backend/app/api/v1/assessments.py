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
    StudentAssessmentQuestionResponse,
    AssessmentAttemptResponse,
    AssessmentAttemptSummaryResponse,
    StudentAttemptAnswerInput,
    ManualGradeInput,
    AssessmentResultResponse,
    TeacherAssessmentResultSummaryResponse,
    AssessmentAnalyticsResponse,
    StudentSelfAnalyticsResponse,
    StudentLearningAnalyticsResponse,
    SubjectQuestionDifficultyResponse,
    SubjectLearningAnalyticsResponse,
    AssessmentLeaderboardResponse,
    AssessmentLeaderboardSettingsUpdateRequest
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


# ── Longitudinal Learning Analytics (Step 10.12) ───────────────

@router.get("/analytics/learning/me", response_model=StudentLearningAnalyticsResponse)
async def get_my_learning_analytics(
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.READ))
):
    """Retrieve longitudinal learning analytics for the authenticated student."""
    service = AssessmentService(db)
    res = await service.get_student_learning_analytics(
        org_id=org.organization_id,
        target_student_id=current_user.user_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=False
    )
    await db.commit()
    return res


@router.get("/analytics/learning/students/{student_id}", response_model=StudentLearningAnalyticsResponse)
async def get_student_learning_analytics_for_teacher(
    student_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.READ))
):
    """Retrieve longitudinal learning analytics for a specific student (Teachers/Admins only)."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.get_student_learning_analytics(
        org_id=org.organization_id,
        target_student_id=student_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )
    await db.commit()
    return res


@router.get("/subjects/{subject_id}/analytics/learning", response_model=SubjectLearningAnalyticsResponse)
async def get_subject_learning_analytics(
    subject_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.READ))
):
    """Retrieve subject-level learning analytics overview across assessments (Teachers/Admins only)."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.get_subject_learning_analytics(
        org_id=org.organization_id,
        subject_id=subject_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )
    await db.commit()
    return res


@router.get("/subjects/{subject_id}/analytics/question-difficulty", response_model=SubjectQuestionDifficultyResponse)
async def get_subject_question_difficulty_analytics(
    subject_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.READ))
):
    """Retrieve descriptive question difficulty analytics for a subject (Teachers/Admins only)."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.get_subject_question_difficulty_analytics(
        org_id=org.organization_id,
        subject_id=subject_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
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


# ── Exam Attempts & Taking Flow Endpoints ───────────────────────

@router.post("/{assessment_id}/start", response_model=AssessmentAttemptResponse)
async def start_assessment_attempt(
    assessment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.READ))
):
    """Start a new attempt or resume an existing in-progress attempt (Idempotent)."""
    service = AssessmentService(db)
    res = await service.start_or_get_in_progress_attempt(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        student_user_id=current_user.user_id
    )
    await db.commit()
    return res


@router.get("/{assessment_id}/attempts", response_model=List[AssessmentAttemptSummaryResponse])
async def list_student_assessment_attempts(
    assessment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.READ))
):
    """List all previous and active attempts for the requesting student on an assessment."""
    service = AssessmentService(db)
    return await service.list_student_attempts(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        student_user_id=current_user.user_id
    )


@router.get("/{assessment_id}/attempts/{attempt_id}", response_model=AssessmentAttemptResponse)
async def get_assessment_attempt(
    assessment_id: uuid.UUID,
    attempt_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.READ))
):
    """Get attempt details and saved answers (sanitized for students, complete for teachers/admins)."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    return await service.get_attempt(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        attempt_id=attempt_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )


@router.put("/{assessment_id}/attempts/{attempt_id}/answers/{question_id}")
async def save_attempt_answer(
    assessment_id: uuid.UUID,
    attempt_id: uuid.UUID,
    question_id: uuid.UUID,
    payload: StudentAttemptAnswerInput,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.READ))
):
    """Save or update student answer for a single question in an active attempt."""
    service = AssessmentService(db)
    res = await service.save_attempt_answer(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        attempt_id=attempt_id,
        question_id=question_id,
        student_user_id=current_user.user_id,
        payload=payload
    )
    await db.commit()
    return res


@router.post("/{assessment_id}/attempts/{attempt_id}/submit", response_model=AssessmentAttemptResponse)
async def submit_assessment_attempt(
    assessment_id: uuid.UUID,
    attempt_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.READ))
):
    """Submit an in-progress assessment attempt and trigger automatic evaluation."""
    service = AssessmentService(db)
    res = await service.submit_attempt(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        attempt_id=attempt_id,
        student_user_id=current_user.user_id
    )
    await db.commit()
    return res


# ── Assessment Evaluation & Result Endpoints ───────────────────

@router.get("/{assessment_id}/attempts/{attempt_id}/result", response_model=AssessmentResultResponse)
async def get_attempt_result(
    assessment_id: uuid.UUID,
    attempt_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.READ))
):
    """Get the calculated and stored result for an assessment attempt."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.get_attempt_result(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        attempt_id=attempt_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )
    await db.commit()
    return res


@router.put("/{assessment_id}/attempts/{attempt_id}/questions/{question_id}/grade", response_model=AssessmentResultResponse)
async def grade_attempt_question(
    assessment_id: uuid.UUID,
    attempt_id: uuid.UUID,
    question_id: uuid.UUID,
    payload: ManualGradeInput,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.UPDATE))
):
    """Grade a student's answer for a specific question (e.g. Short Answer) and recalculate result."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.grade_question(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        attempt_id=attempt_id,
        question_id=question_id,
        grader_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        payload=payload
    )
    await db.commit()
    return res


@router.get("/{assessment_id}/results", response_model=List[TeacherAssessmentResultSummaryResponse])
async def list_assessment_results(
    assessment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.READ))
):
    """List all attempt results for an assessment (Teachers and Admins only)."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.list_assessment_results(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )
    await db.commit()
    return res


# ── Assessment Analytics Endpoints (Step 10.11) ─────────────────

@router.get("/{assessment_id}/analytics", response_model=AssessmentAnalyticsResponse)
async def get_assessment_analytics(
    assessment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.READ))
):
    """Get full class-wide analytics for an assessment (Teachers and Org Admins only)."""
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.get_assessment_analytics(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin
    )
    await db.commit()
    return res


@router.get("/{assessment_id}/analytics/self", response_model=StudentSelfAnalyticsResponse)
async def get_student_self_analytics(
    assessment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.READ))
):
    """Get student's own attempts and performance progression for an assessment."""
    service = AssessmentService(db)
    res = await service.get_student_self_analytics(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        student_user_id=current_user.user_id
    )
    await db.commit()
    return res


# ── Assessment Leaderboard Endpoints (Step 10.13) ───────────────

@router.get("/{assessment_id}/leaderboard", response_model=AssessmentLeaderboardResponse)
async def get_assessment_leaderboard(
    assessment_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.READ))
):
    """
    Get server-authoritative leaderboard rankings for an assessment.
    Returns 0 entries if leaderboard is disabled and requester is a student.
    """
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.get_assessment_leaderboard(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        page=page,
        page_size=page_size
    )
    await db.commit()
    return res


@router.patch("/{assessment_id}/leaderboard-settings", response_model=AssessmentLeaderboardResponse)
async def update_assessment_leaderboard_settings(
    assessment_id: uuid.UUID,
    payload: AssessmentLeaderboardSettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission(AssessmentPermission.UPDATE))
):
    """
    Enable or disable leaderboard rankings for an assessment (Teachers and Org Admins only).
    """
    service = AssessmentService(db)
    is_org_admin = await service.repo.is_user_org_admin(current_user.user_id, org.organization_id)
    res = await service.update_assessment_leaderboard_settings(
        org_id=org.organization_id,
        assessment_id=assessment_id,
        requesting_user_id=current_user.user_id,
        is_org_admin=is_org_admin,
        payload=payload
    )
    await db.commit()
    return res




