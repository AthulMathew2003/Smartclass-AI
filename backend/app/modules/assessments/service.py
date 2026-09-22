import random
import statistics
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, exists
from sqlalchemy.orm import selectinload

from app.modules.assessments.models import (
    Assessment,
    AssessmentType,
    AssessmentStatus,
    QuestionBankItem,
    AssessmentQuestion,
    QuestionOption,
    QuestionType,
    QuestionStatus,
    AssessmentAttempt,
    AssessmentAttemptAnswer,
    AttemptStatus,
    AssessmentResult,
    AssessmentResultQuestion,
    ResultStatus,
    GradingStatus,
    CorrectnessStatus
)
from app.modules.assessments.schemas import (
    AssessmentCreateRequest,
    AssessmentUpdateRequest,
    AssessmentResponse,
    QuestionBankItemCreate,
    QuestionBankItemUpdate,
    QuestionBankItemResponse,
    AssessmentAddQuestionRequest,
    AssessmentCreateAndAddQuestionRequest,
    AssessmentQuestionUpdateRequest,
    QuestionReorderRequest,
    AssessmentQuestionResponse,
    StudentAssessmentQuestionResponse,
    QuestionOptionResponse,
    StudentQuestionOptionResponse,
    StudentAttemptAnswerInput,
    StudentAttemptQuestionResponse,
    AssessmentAttemptResponse,
    AssessmentAttemptSummaryResponse,
    ManualGradeInput,
    AssessmentResultQuestionResponse,
    AssessmentResultResponse,
    TeacherAssessmentResultSummaryResponse,
    AssessmentAnalyticsOverview,
    AssessmentScoreStatistics,
    AssessmentAttemptStatistics,
    AssessmentQuestionAnalyticsItem,
    AssessmentStudentAttemptItem,
    AssessmentStudentPerformanceItem,
    AssessmentAnalyticsResponse,
    StudentSelfAnalyticsResponse,
    ObservedDifficultyBand,
    StudentLearningOverview,
    StudentPerformanceTrendPoint,
    StudentLearningTrend,
    StudentSubjectPerformanceItem,
    StudentQuestionTypePerformanceItem,
    StudentLearningAnalyticsResponse,
    QuestionDifficultyAnalyticsItem,
    SubjectQuestionDifficultyResponse,
    SubjectLearningAnalyticsResponse,
    AssessmentLeaderboardSettingsUpdateRequest,
    LeaderboardStudentBrief,
    AssessmentLeaderboardEntryResponse,
    AssessmentLeaderboardResponse,
    ClassStudentPerformanceItem,
    ClassPerformanceDashboardResponse
)
from app.modules.assessments.repository import AssessmentRepository
from app.modules.subjects.models import Subject, SubjectTeacher, SubjectStatus
from app.modules.organizations.models import Workspace, WorkspaceStatus
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    ConflictException,
    ValidationException,
    AttemptExpiredException
)


class AssessmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AssessmentRepository(db)

    # ── Context and Authorization Verifications ─────────────────

    async def _verify_subject_hierarchy(
        self,
        subject_id: uuid.UUID,
        org_id: uuid.UUID,
        allow_archived_parent: bool = False
    ) -> tuple[Subject, Workspace]:
        """
        Verify tenant hierarchy: Subject -> Workspace -> Organization.
        """
        stmt = (
            select(Subject, Workspace)
            .join(Workspace, Subject.subject_workspace_id == Workspace.workspace_id)
            .where(
                Subject.subject_id == subject_id,
                Workspace.workspace_organization_id == org_id
            )
        )
        result = await self.db.execute(stmt)
        row = result.first()
        if not row:
            raise NotFoundException("Subject not found in the current organization.")

        subject, workspace = row
        if not allow_archived_parent:
            if workspace.workspace_status == WorkspaceStatus.ARCHIVED:
                raise ForbiddenException("Workspace is archived.")
            if subject.subject_status == SubjectStatus.ARCHIVED:
                raise ForbiddenException("Subject is archived.")

        return subject, workspace

    async def _verify_assessment_hierarchy(
        self,
        assessment_id: uuid.UUID,
        org_id: uuid.UUID,
        allow_archived_parent: bool = False
    ) -> tuple[Assessment, Subject, Workspace]:
        """
        Verify tenant hierarchy: Assessment -> Subject -> Workspace -> Organization.
        """
        assessment = await self.repo.get_assessment_by_id(assessment_id)
        if not assessment:
            raise NotFoundException("Assessment not found.")

        subject, workspace = await self._verify_subject_hierarchy(
            assessment.assessment_subject_id,
            org_id,
            allow_archived_parent=allow_archived_parent
        )
        return assessment, subject, workspace

    async def _verify_teacher_or_admin(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        workspace_id: uuid.UUID,
        is_org_admin: bool
    ) -> None:
        """
        Verify that the user is an Organization Owner/Admin OR an assigned teacher of the subject.
        """
        if is_org_admin:
            return

        is_ws_member = await self.repo.is_user_workspace_member(user_id, workspace_id)
        if not is_ws_member:
            raise ForbiddenException("Access denied. You are not a member of this workspace.")

        is_assigned_teacher = await self.repo.is_user_subject_teacher(user_id, subject_id)
        if not is_assigned_teacher:
            raise ForbiddenException("Access denied. You are not assigned to this subject.")

    async def _verify_workspace_access(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        is_org_admin: bool
    ) -> None:
        """
        Verify that the user is an Organization Owner/Admin OR a member of the workspace.
        """
        if is_org_admin:
            return

        is_ws_member = await self.repo.is_user_workspace_member(user_id, workspace_id)
        if not is_ws_member:
            raise ForbiddenException("Access denied. You are not a member of this workspace.")

    # ── Assessment Lifecycle & CRUD ─────────────────────────────

    async def create_assessment(
        self,
        org_id: uuid.UUID,
        created_by_user_id: uuid.UUID,
        is_org_admin: bool,
        payload: AssessmentCreateRequest
    ) -> AssessmentResponse:
        """Create a new Assessment in DRAFT status."""
        subject, workspace = await self._verify_subject_hierarchy(payload.subject_id, org_id)

        await self._verify_teacher_or_admin(
            created_by_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        total_marks = payload.total_marks if payload.total_marks is not None else Decimal("0.00")

        assessment = await self.repo.create_assessment(
            subject_id=subject.subject_id,
            title=payload.title,
            description=payload.description,
            type=payload.type,
            status=payload.status or AssessmentStatus.DRAFT,
            duration_minutes=payload.duration_minutes,
            start_at=payload.start_at,
            end_at=payload.end_at,
            total_marks=total_marks,
            passing_marks=payload.passing_marks,
            attempt_limit=payload.attempt_limit,
            randomize_questions=payload.randomize_questions,
            leaderboard_enabled=payload.leaderboard_enabled,
            created_by=created_by_user_id
        )

        resp = AssessmentResponse.model_validate(assessment)
        resp.subject_name = subject.subject_name
        resp.workspace_id = workspace.workspace_id
        resp.workspace_name = workspace.workspace_name
        resp.total_questions = 0
        return resp

    async def get_assessment(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        subject_id: Optional[uuid.UUID] = None
    ) -> AssessmentResponse:
        """Retrieve single assessment details."""
        assessment, subject, workspace = await self._verify_assessment_hierarchy(
            assessment_id,
            org_id,
            allow_archived_parent=True
        )
        if subject_id is not None and subject.subject_id != subject_id:
            raise NotFoundException("Assessment not found for the specified subject.")

        await self._verify_workspace_access(requesting_user_id, workspace.workspace_id, is_org_admin)

        is_teacher = is_org_admin or (await self.repo.is_user_subject_teacher(requesting_user_id, subject.subject_id))

        if assessment.assessment_status in (AssessmentStatus.DRAFT, AssessmentStatus.ARCHIVED) and not is_teacher:
            raise NotFoundException("Assessment not found.")

        resp = AssessmentResponse.model_validate(assessment)
        resp.subject_name = subject.subject_name
        resp.workspace_id = workspace.workspace_id
        resp.workspace_name = workspace.workspace_name
        resp.total_questions = len(assessment.assessment_questions)
        return resp

    async def list_assessments(
        self,
        org_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        subject_id: Optional[uuid.UUID] = None,
        workspace_id: Optional[uuid.UUID] = None,
        status_filter: Optional[AssessmentStatus] = None,
        search: Optional[str] = None
    ) -> List[AssessmentResponse]:
        """List accessible assessments."""
        if subject_id is not None:
            subject, workspace = await self._verify_subject_hierarchy(subject_id, org_id, allow_archived_parent=True)
            await self._verify_workspace_access(requesting_user_id, workspace.workspace_id, is_org_admin)

            is_teacher = is_org_admin or (await self.repo.is_user_subject_teacher(requesting_user_id, subject.subject_id))
            assessments = await self.repo.list_assessments_by_subject(
                subject_id=subject.subject_id,
                status_filter=status_filter,
                include_drafts=is_teacher,
                include_archived=is_teacher,
                search=search
            )

            responses = []
            for a in assessments:
                resp = AssessmentResponse.model_validate(a)
                resp.subject_name = subject.subject_name
                resp.workspace_id = workspace.workspace_id
                resp.workspace_name = workspace.workspace_name
                resp.total_questions = len(a.assessment_questions)
                responses.append(resp)
            return responses

        # Global list across organization
        is_teacher = (
            is_org_admin
            or (await self.repo.is_user_any_subject_teacher(org_id, requesting_user_id))
            or (await self.repo.is_user_teacher_or_admin_role(org_id, requesting_user_id))
        )

        if is_teacher:
            assessments = await self.repo.list_global_assessments_for_teacher_or_admin(
                org_id=org_id,
                user_id=requesting_user_id,
                is_org_admin=is_org_admin,
                status_filter=status_filter,
                workspace_id=workspace_id,
                search=search
            )
        else:
            assessments = await self.repo.list_global_assessments_for_student(
                org_id=org_id,
                user_id=requesting_user_id,
                status_filter=status_filter,
                workspace_id=workspace_id,
                search=search
            )

        responses = []
        for a in assessments:
            resp = AssessmentResponse.model_validate(a)
            if a.subject:
                resp.subject_name = a.subject.subject_name
                if a.subject.workspace:
                    resp.workspace_id = a.subject.workspace.workspace_id
                    resp.workspace_name = a.subject.workspace.workspace_name
            resp.total_questions = len(a.assessment_questions)
            responses.append(resp)
        return responses

    async def update_assessment(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        payload: AssessmentUpdateRequest,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        subject_id: Optional[uuid.UUID] = None
    ) -> AssessmentResponse:
        """Update an existing assessment's metadata."""
        assessment, subject, workspace = await self._verify_assessment_hierarchy(assessment_id, org_id)
        if subject_id is not None and subject.subject_id != subject_id:
            raise NotFoundException("Assessment not found for the specified subject.")

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        if assessment.assessment_status == AssessmentStatus.ARCHIVED:
            raise ConflictException("Archived assessments cannot be modified.")

        if assessment.assessment_status == AssessmentStatus.CLOSED:
            raise ConflictException("Closed assessments cannot be modified.")

        # If published, block structural changes to duration/marks
        if assessment.assessment_status in (AssessmentStatus.PUBLISHED, AssessmentStatus.ACTIVE):
            if payload.duration_minutes is not None and payload.duration_minutes != assessment.assessment_duration_minutes:
                raise ConflictException("Cannot modify duration of a published assessment.")
            if payload.total_marks is not None and payload.total_marks != assessment.assessment_total_marks:
                raise ConflictException("Cannot modify total marks of a published assessment.")

        start_at = payload.start_at if payload.start_at is not None else assessment.assessment_start_at
        end_at = payload.end_at if payload.end_at is not None else assessment.assessment_end_at
        if start_at is not None and start_at.tzinfo is None:
            start_at = start_at.replace(tzinfo=timezone.utc)
        if end_at is not None and end_at.tzinfo is None:
            end_at = end_at.replace(tzinfo=timezone.utc)

        if start_at is not None and end_at is not None and end_at <= start_at:
            raise ValidationException("Assessment end time must be after the start time.")

        passing_marks = payload.passing_marks if payload.passing_marks is not None else assessment.assessment_passing_marks
        total_marks = payload.total_marks if payload.total_marks is not None else assessment.assessment_total_marks
        if passing_marks is not None and total_marks is not None and passing_marks > total_marks:
            raise ValidationException("Passing marks cannot exceed total marks.")

        updated = await self.repo.update_assessment(
            assessment=assessment,
            title=payload.title,
            description=payload.description,
            type=payload.type,
            duration_minutes=payload.duration_minutes,
            start_at=start_at,
            end_at=end_at,
            total_marks=payload.total_marks,
            passing_marks=payload.passing_marks,
            attempt_limit=payload.attempt_limit,
            randomize_questions=payload.randomize_questions,
            leaderboard_enabled=payload.leaderboard_enabled
        )

        resp = AssessmentResponse.model_validate(updated)
        resp.subject_name = subject.subject_name
        resp.workspace_id = workspace.workspace_id
        resp.workspace_name = workspace.workspace_name
        resp.total_questions = len(updated.assessment_questions)
        return resp

    async def publish_assessment(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        subject_id: Optional[uuid.UUID] = None
    ) -> AssessmentResponse:
        """Publish a DRAFT assessment after validating questions, marks, and constraints."""
        assessment, subject, workspace = await self._verify_assessment_hierarchy(assessment_id, org_id)
        if subject_id is not None and subject.subject_id != subject_id:
            raise NotFoundException("Assessment not found for the specified subject.")

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        if assessment.assessment_status != AssessmentStatus.DRAFT:
            raise ConflictException(f"Only DRAFT assessments can be published (current: {assessment.assessment_status.value}).")

        # Recalculate total marks from questions
        total_marks = await self.repo.recalculate_assessment_total_marks(assessment_id)
        questions = await self.repo.list_assessment_questions(assessment_id)

        if len(questions) == 0:
            raise ValidationException("Cannot publish an assessment with zero questions. Add at least one question.")

        if total_marks <= Decimal("0.00"):
            raise ValidationException("Total marks must be greater than 0.")

        if assessment.assessment_passing_marks is not None and assessment.assessment_passing_marks > total_marks:
            raise ValidationException(f"Passing marks ({assessment.assessment_passing_marks}) cannot exceed total marks ({total_marks}).")

        if assessment.assessment_attempt_limit < 1:
            raise ValidationException("Attempt limit must be at least 1.")

        if assessment.assessment_start_at and assessment.assessment_end_at:
            if assessment.assessment_end_at <= assessment.assessment_start_at:
                raise ValidationException("Assessment end time must be after the start time.")

        updated = await self.repo.set_assessment_status(assessment, AssessmentStatus.PUBLISHED)
        resp = AssessmentResponse.model_validate(updated)
        resp.subject_name = subject.subject_name
        resp.workspace_id = workspace.workspace_id
        resp.workspace_name = workspace.workspace_name
        resp.total_questions = len(questions)
        return resp

    async def close_assessment(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        subject_id: Optional[uuid.UUID] = None
    ) -> AssessmentResponse:
        """Close a published assessment."""
        assessment, subject, workspace = await self._verify_assessment_hierarchy(
            assessment_id,
            org_id,
            allow_archived_parent=True
        )
        if subject_id is not None and subject.subject_id != subject_id:
            raise NotFoundException("Assessment not found for the specified subject.")

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        if assessment.assessment_status not in (AssessmentStatus.PUBLISHED, AssessmentStatus.ACTIVE):
            raise ConflictException(f"Only PUBLISHED or ACTIVE assessments can be closed (current: {assessment.assessment_status.value}).")

        updated = await self.repo.set_assessment_status(assessment, AssessmentStatus.CLOSED)
        resp = AssessmentResponse.model_validate(updated)
        resp.subject_name = subject.subject_name
        resp.workspace_id = workspace.workspace_id
        resp.workspace_name = workspace.workspace_name
        resp.total_questions = len(assessment.assessment_questions)
        return resp

    async def archive_assessment(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        subject_id: Optional[uuid.UUID] = None
    ) -> AssessmentResponse:
        """Archive an assessment."""
        assessment, subject, workspace = await self._verify_assessment_hierarchy(
            assessment_id,
            org_id,
            allow_archived_parent=True
        )
        if subject_id is not None and subject.subject_id != subject_id:
            raise NotFoundException("Assessment not found for the specified subject.")

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        if assessment.assessment_status == AssessmentStatus.ARCHIVED:
            raise ConflictException("Assessment is already archived.")

        updated = await self.repo.archive_assessment(assessment)
        resp = AssessmentResponse.model_validate(updated)
        resp.subject_name = subject.subject_name
        resp.workspace_id = workspace.workspace_id
        resp.workspace_name = workspace.workspace_name
        resp.total_questions = len(assessment.assessment_questions)
        return resp

    async def delete_assessment(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        subject_id: Optional[uuid.UUID] = None
    ) -> None:
        """Permanently delete an assessment and all attached snapshot questions."""
        assessment, subject, workspace = await self._verify_assessment_hierarchy(
            assessment_id,
            org_id,
            allow_archived_parent=True
        )
        if subject_id is not None and subject.subject_id != subject_id:
            raise NotFoundException("Assessment not found for the specified subject.")

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        await self.repo.delete_assessment(assessment)

    # ── Subject Question Bank Operations ────────────────────────

    async def create_question_bank_item(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        payload: QuestionBankItemCreate
    ) -> QuestionBankItemResponse:
        """Create a question in the Subject Question Bank."""
        subject, workspace = await self._verify_subject_hierarchy(subject_id, org_id)

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        options_data = [
            {
                "option_text": opt.option_text,
                "option_order": opt.option_order,
                "option_is_correct": opt.option_is_correct
            }
            for opt in payload.options
        ]

        question = await self.repo.create_question_bank_item(
            subject_id=subject.subject_id,
            question_type=payload.question_type,
            question_text=payload.question_text,
            default_marks=payload.default_marks,
            question_explanation=payload.question_explanation,
            created_by=requesting_user_id,
            options_data=options_data
        )
        return QuestionBankItemResponse.model_validate(question)

    async def list_subject_questions(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        question_type: Optional[QuestionType] = None,
        search: Optional[str] = None,
        include_archived: bool = False
    ) -> List[QuestionBankItemResponse]:
        """List questions in the Subject Question Bank."""
        subject, workspace = await self._verify_subject_hierarchy(subject_id, org_id, allow_archived_parent=True)

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        questions = await self.repo.list_questions_by_subject(
            subject_id=subject.subject_id,
            question_type=question_type,
            search=search,
            include_archived=include_archived
        )
        return [QuestionBankItemResponse.model_validate(q) for q in questions]

    async def get_question_bank_item(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        question_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> QuestionBankItemResponse:
        """Get single Question Bank item."""
        subject, workspace = await self._verify_subject_hierarchy(subject_id, org_id, allow_archived_parent=True)

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        question = await self.repo.get_question_bank_item_by_id(question_id)
        if not question or question.question_subject_id != subject_id:
            raise NotFoundException("Question not found in this subject's question bank.")

        return QuestionBankItemResponse.model_validate(question)

    async def update_question_bank_item(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        question_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        payload: QuestionBankItemUpdate
    ) -> QuestionBankItemResponse:
        """Update Question Bank item."""
        subject, workspace = await self._verify_subject_hierarchy(subject_id, org_id)

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        question = await self.repo.get_question_bank_item_by_id(question_id)
        if not question or question.question_subject_id != subject_id:
            raise NotFoundException("Question not found in this subject's question bank.")

        if question.question_status == QuestionStatus.ARCHIVED:
            raise ConflictException("Archived questions cannot be modified.")

        options_data = None
        if payload.options is not None:
            options_data = [
                {
                    "option_text": opt.option_text,
                    "option_order": opt.option_order,
                    "option_is_correct": opt.option_is_correct
                }
                for opt in payload.options
            ]

        updated = await self.repo.update_question_bank_item(
            question=question,
            question_text=payload.question_text,
            default_marks=payload.default_marks,
            question_explanation=payload.question_explanation,
            question_type=payload.question_type,
            options_data=options_data
        )
        return QuestionBankItemResponse.model_validate(updated)

    async def delete_question_bank_item(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        question_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> None:
        """Delete / archive Question Bank item."""
        subject, workspace = await self._verify_subject_hierarchy(subject_id, org_id)

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        question = await self.repo.get_question_bank_item_by_id(question_id)
        if not question or question.question_subject_id != subject_id:
            raise NotFoundException("Question not found in this subject's question bank.")

        await self.repo.delete_question_bank_item(question)

    # ── Assessment Builder & Question Snapshot Operations ───────

    def _build_question_snapshot(
        self,
        question_id: uuid.UUID,
        question_type: QuestionType,
        question_text: str,
        marks: Decimal,
        question_explanation: Optional[str],
        options: List[Any]
    ) -> dict:
        """Construct immutable JSON snapshot of question content for assessment."""
        formatted_options = []
        for opt in options:
            if hasattr(opt, "option_id"):
                opt_id = str(opt.option_id)
                opt_text = opt.option_text
                opt_order = opt.option_order
                opt_is_correct = opt.option_is_correct
            elif isinstance(opt, dict):
                opt_id = str(opt.get("option_id") or uuid.uuid4())
                opt_text = opt["option_text"]
                opt_order = opt["option_order"]
                opt_is_correct = opt.get("option_is_correct", False)
            else:
                opt_id = str(getattr(opt, "option_id", None) or uuid.uuid4())
                opt_text = getattr(opt, "option_text", "")
                opt_order = getattr(opt, "option_order", 1)
                opt_is_correct = getattr(opt, "option_is_correct", False)

            formatted_options.append({
                "option_id": opt_id,
                "option_text": opt_text,
                "option_order": opt_order,
                "option_is_correct": opt_is_correct
            })

        return {
            "question_id": str(question_id),
            "question_type": question_type.value if hasattr(question_type, "value") else str(question_type),
            "question_text": question_text,
            "question_marks": float(marks),
            "question_explanation": question_explanation,
            "options": formatted_options
        }

    def _unpack_assessment_question(
        self,
        aq: AssessmentQuestion,
        sanitize_for_student: bool = False
    ) -> dict:
        """Unpack snapshot into teacher or sanitized student response dict."""
        snapshot = aq.assessment_question_snapshot or {}
        q_type = snapshot.get("question_type", "mcq_single")
        q_text = snapshot.get("question_text", "")
        q_explanation = snapshot.get("question_explanation")
        raw_options = snapshot.get("options", [])

        if sanitize_for_student:
            student_options = [
                {
                    "option_id": opt.get("option_id"),
                    "option_text": opt.get("option_text", ""),
                    "option_order": opt.get("option_order", idx + 1)
                }
                for idx, opt in enumerate(raw_options)
            ]
            return {
                "assessment_question_id": aq.assessment_question_id,
                "assessment_question_order": aq.assessment_question_order,
                "assessment_question_marks": aq.assessment_question_marks,
                "question_type": q_type,
                "question_text": q_text,
                "options": student_options
            }

        teacher_options = [
            {
                "option_id": opt.get("option_id"),
                "option_question_id": aq.assessment_question_question_id,
                "option_text": opt.get("option_text", ""),
                "option_order": opt.get("option_order", idx + 1),
                "option_is_correct": opt.get("option_is_correct", False)
            }
            for idx, opt in enumerate(raw_options)
        ]
        return {
            "assessment_question_id": aq.assessment_question_id,
            "assessment_question_assessment_id": aq.assessment_question_assessment_id,
            "assessment_question_question_id": aq.assessment_question_question_id,
            "assessment_question_order": aq.assessment_question_order,
            "assessment_question_marks": aq.assessment_question_marks,
            "assessment_question_created_at": aq.assessment_question_created_at,
            "question_type": q_type,
            "question_text": q_text,
            "question_explanation": q_explanation,
            "options": teacher_options
        }

    async def add_question_from_bank(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        payload: AssessmentAddQuestionRequest
    ) -> AssessmentQuestionResponse:
        """Add an existing Question Bank item into the Assessment with a frozen Snapshot."""
        assessment, subject, workspace = await self._verify_assessment_hierarchy(assessment_id, org_id)

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        if assessment.assessment_status != AssessmentStatus.DRAFT:
            raise ConflictException(f"Questions can only be added to DRAFT assessments (current: {assessment.assessment_status.value}).")

        question = await self.repo.get_question_bank_item_by_id(payload.question_id)
        if not question:
            raise NotFoundException("Question not found in question bank.")

        # Prevent cross-subject question injection
        if question.question_subject_id != subject.subject_id:
            raise ForbiddenException("Cannot add questions from a different subject or workspace.")

        # Prevent duplicate question in the same assessment
        if await self.repo.exists_question_in_assessment(assessment_id, question.question_id):
            raise ConflictException("This question is already added to the assessment.")

        marks = payload.marks if payload.marks is not None else question.question_default_marks
        max_order = await self.repo.get_max_assessment_question_order(assessment_id)
        order = payload.order if payload.order is not None else (max_order + 1)

        snapshot = self._build_question_snapshot(
            question_id=question.question_id,
            question_type=question.question_type,
            question_text=question.question_text,
            marks=marks,
            question_explanation=question.question_explanation,
            options=question.options
        )

        aq = await self.repo.create_assessment_question(
            assessment_id=assessment_id,
            question_id=question.question_id,
            order=order,
            marks=marks,
            snapshot=snapshot
        )

        await self.repo.recalculate_assessment_total_marks(assessment_id)
        data = self._unpack_assessment_question(aq, sanitize_for_student=False)
        return AssessmentQuestionResponse.model_validate(data)

    async def create_and_add_question(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        payload: AssessmentCreateAndAddQuestionRequest
    ) -> AssessmentQuestionResponse:
        """Create a new Question in the Subject Question Bank and attach it to the Assessment."""
        assessment, subject, workspace = await self._verify_assessment_hierarchy(assessment_id, org_id)

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        if assessment.assessment_status != AssessmentStatus.DRAFT:
            raise ConflictException(f"Questions can only be added to DRAFT assessments (current: {assessment.assessment_status.value}).")

        # 1. Create in Subject Question Bank
        options_data = [
            {
                "option_text": opt.option_text,
                "option_order": opt.option_order,
                "option_is_correct": opt.option_is_correct
            }
            for opt in payload.options
        ]

        marks = getattr(payload, "marks", getattr(payload, "default_marks", Decimal("1.00")))
        order_val = getattr(payload, "order", None)

        bank_item = await self.repo.create_question_bank_item(
            subject_id=subject.subject_id,
            question_type=payload.question_type,
            question_text=payload.question_text,
            default_marks=marks,
            question_explanation=payload.question_explanation,
            created_by=requesting_user_id,
            options_data=options_data
        )

        # 2. Add to Assessment
        max_order = await self.repo.get_max_assessment_question_order(assessment_id)
        order = order_val if order_val is not None else (max_order + 1)

        snapshot = self._build_question_snapshot(
            question_id=bank_item.question_id,
            question_type=bank_item.question_type,
            question_text=bank_item.question_text,
            marks=marks,
            question_explanation=bank_item.question_explanation,
            options=bank_item.options
        )

        aq = await self.repo.create_assessment_question(
            assessment_id=assessment_id,
            question_id=bank_item.question_id,
            order=order,
            marks=marks,
            snapshot=snapshot
        )

        await self.repo.recalculate_assessment_total_marks(assessment_id)
        data = self._unpack_assessment_question(aq, sanitize_for_student=False)
        return AssessmentQuestionResponse.model_validate(data)

    async def list_assessment_questions(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> List[dict]:
        """List assessment questions (sanitized for students, complete for teachers)."""
        assessment, subject, workspace = await self._verify_assessment_hierarchy(
            assessment_id,
            org_id,
            allow_archived_parent=True
        )

        is_teacher = is_org_admin or (await self.repo.is_user_subject_teacher(requesting_user_id, subject.subject_id))

        if not is_teacher:
            # Student checks
            await self._verify_workspace_access(requesting_user_id, workspace.workspace_id, is_org_admin=False)
            if assessment.assessment_status not in (AssessmentStatus.PUBLISHED, AssessmentStatus.ACTIVE):
                raise NotFoundException("Assessment not found.")

            questions = await self.repo.list_assessment_questions(assessment_id)
            return [self._unpack_assessment_question(q, sanitize_for_student=True) for q in questions]

        # Teacher / Admin view
        questions = await self.repo.list_assessment_questions(assessment_id)
        return [self._unpack_assessment_question(q, sanitize_for_student=False) for q in questions]

    async def get_assessment_question(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        assessment_question_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> dict:
        """Get single assessment question."""
        assessment, subject, workspace = await self._verify_assessment_hierarchy(
            assessment_id,
            org_id,
            allow_archived_parent=True
        )

        aq = await self.repo.get_assessment_question_by_id(assessment_question_id)
        if not aq or aq.assessment_question_assessment_id != assessment_id:
            raise NotFoundException("Question not found in this assessment.")

        is_teacher = is_org_admin or (await self.repo.is_user_subject_teacher(requesting_user_id, subject.subject_id))

        if not is_teacher:
            await self._verify_workspace_access(requesting_user_id, workspace.workspace_id, is_org_admin=False)
            if assessment.assessment_status not in (AssessmentStatus.PUBLISHED, AssessmentStatus.ACTIVE):
                raise NotFoundException("Assessment not found.")
            return self._unpack_assessment_question(aq, sanitize_for_student=True)

        return self._unpack_assessment_question(aq, sanitize_for_student=False)

    async def update_assessment_question(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        assessment_question_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        payload: AssessmentQuestionUpdateRequest
    ) -> AssessmentQuestionResponse:
        """Update marks/order for an assessment question (Draft only)."""
        assessment, subject, workspace = await self._verify_assessment_hierarchy(assessment_id, org_id)

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        if assessment.assessment_status != AssessmentStatus.DRAFT:
            raise ConflictException(f"Questions can only be modified in DRAFT assessments (current: {assessment.assessment_status.value}).")

        aq = await self.repo.get_assessment_question_by_id(assessment_question_id)
        if not aq or aq.assessment_question_assessment_id != assessment_id:
            raise NotFoundException("Question not found in this assessment.")

        updated = await self.repo.update_assessment_question(
            assessment_question=aq,
            marks=payload.marks,
            order=payload.order
        )

        if payload.marks is not None:
            await self.repo.recalculate_assessment_total_marks(assessment_id)

        data = self._unpack_assessment_question(updated, sanitize_for_student=False)
        return AssessmentQuestionResponse.model_validate(data)

    async def remove_assessment_question(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        assessment_question_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> None:
        """Remove a question from an assessment (Draft only). Does not delete from Question Bank."""
        assessment, subject, workspace = await self._verify_assessment_hierarchy(assessment_id, org_id)

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        if assessment.assessment_status != AssessmentStatus.DRAFT:
            raise ConflictException(f"Questions can only be removed from DRAFT assessments (current: {assessment.assessment_status.value}).")

        aq = await self.repo.get_assessment_question_by_id(assessment_question_id)
        if not aq or aq.assessment_question_assessment_id != assessment_id:
            raise NotFoundException("Question not found in this assessment.")

        await self.repo.delete_assessment_question(aq)
        await self.repo.recalculate_assessment_total_marks(assessment_id)

        # Normalize remaining question orders (1..N)
        remaining = await self.repo.list_assessment_questions(assessment_id)
        if remaining:
            q_ids = [q.assessment_question_id for q in remaining]
            await self.repo.reorder_assessment_questions(assessment_id, q_ids)

    async def reorder_assessment_questions(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        payload: QuestionReorderRequest
    ) -> List[dict]:
        """Atomically reorder questions in an assessment (Draft only)."""
        assessment, subject, workspace = await self._verify_assessment_hierarchy(assessment_id, org_id)

        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        if assessment.assessment_status != AssessmentStatus.DRAFT:
            raise ConflictException(f"Questions can only be reordered when assessment is in DRAFT status (current: {assessment.assessment_status.value}).")

        existing_questions = await self.repo.list_assessment_questions(assessment_id)
        existing_ids = {q.assessment_question_id for q in existing_questions}

        request_ids_set = set(payload.question_ids)
        if request_ids_set != existing_ids:
            raise ValidationException("Reorder request must include all active question IDs for this assessment without additions or omissions.")

        await self.repo.reorder_assessment_questions(assessment_id, payload.question_ids)
        updated_questions = await self.repo.list_assessment_questions(assessment_id)
        return [self._unpack_assessment_question(q, sanitize_for_student=False) for q in updated_questions]

    # Aliases for backwards compatibility with earlier tests
    create_question = create_and_add_question
    list_questions = list_assessment_questions
    get_question = get_assessment_question
    update_question = update_assessment_question
    delete_question = remove_assessment_question
    reorder_questions = reorder_assessment_questions

    # ── Attempt Lifecycle & Taking Flow ─────────────────────────

    def _unpack_attempt(
        self,
        attempt: AssessmentAttempt,
        questions: List[AssessmentQuestion],
        sanitize_for_student: bool = True
    ) -> AssessmentAttemptResponse:
        questions_by_id = {str(q.assessment_question_id): q for q in questions}
        order_list = attempt.attempt_question_order or []

        # Order according to attempt_question_order, then append any remaining questions
        ordered_questions: List[AssessmentQuestion] = []
        seen = set()
        for qid in order_list:
            if qid in questions_by_id:
                ordered_questions.append(questions_by_id[qid])
                seen.add(qid)
        for q in sorted(questions, key=lambda x: x.assessment_question_order):
            if str(q.assessment_question_id) not in seen:
                ordered_questions.append(q)

        # Unpack each question snapshot
        formatted_questions: List[StudentAttemptQuestionResponse] = []
        for idx, q in enumerate(ordered_questions):
            snapshot = q.assessment_question_snapshot or {}
            raw_options = snapshot.get("options", [])
            student_options = [
                StudentQuestionOptionResponse(
                    option_id=opt.get("option_id"),
                    option_text=opt.get("option_text", ""),
                    option_order=opt.get("option_order", opt_idx + 1)
                )
                for opt_idx, opt in enumerate(raw_options)
            ]
            formatted_questions.append(
                StudentAttemptQuestionResponse(
                    assessment_question_id=q.assessment_question_id,
                    assessment_question_order=idx + 1,
                    question_type=snapshot.get("question_type", "mcq_single"),
                    question_text=snapshot.get("question_text", ""),
                    marks=q.assessment_question_marks,
                    options=student_options
                )
            )

        # Map answers
        answers_list = attempt.__dict__.get("answers")
        if answers_list is None:
            answers_list = []
        answers_map = {
            str(a.attempt_answer_question_id): a.attempt_answer_value
            for a in answers_list
        }

        return AssessmentAttemptResponse(
            attempt_id=attempt.attempt_id,
            attempt_assessment_id=attempt.attempt_assessment_id,
            attempt_student_id=attempt.attempt_student_id,
            attempt_number=attempt.attempt_number,
            attempt_status=attempt.attempt_status,
            attempt_started_at=attempt.attempt_started_at,
            attempt_expires_at=attempt.attempt_expires_at,
            attempt_submitted_at=attempt.attempt_submitted_at,
            attempt_question_order=order_list,
            total_questions=len(formatted_questions),
            questions=formatted_questions,
            answers=answers_map
        )

    # ── Expiry Check Helper ──────────────────────────────────────

    async def _check_and_expire_if_needed(
        self,
        attempt: AssessmentAttempt
    ) -> None:
        """Check if the attempt has exceeded its time limit. If so, expire it and raise AttemptExpiredException.
        Idempotent — safe to call multiple times."""
        if attempt.attempt_expires_at is None:
            # No time limit on this attempt
            return

        if attempt.attempt_status == AttemptStatus.EXPIRED:
            raise AttemptExpiredException()

        now_utc = datetime.now(timezone.utc)
        # Ensure expires_at is timezone-aware for comparison
        expires_at = attempt.attempt_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if now_utc >= expires_at:
            # Server confirms expiry — persist, evaluate, and raise
            await self.repo.expire_attempt(attempt)
            await self.evaluate_attempt(attempt.attempt_id)
            raise AttemptExpiredException()

    async def start_or_get_in_progress_attempt(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        student_user_id: uuid.UUID
    ) -> AssessmentAttemptResponse:
        """Start a new attempt or return an existing in-progress attempt (Idempotent)."""
        assessment, subject, workspace = await self._verify_assessment_hierarchy(assessment_id, org_id)
        await self._verify_workspace_access(student_user_id, workspace.workspace_id, is_org_admin=False)

        if assessment.assessment_status not in (AssessmentStatus.PUBLISHED, AssessmentStatus.ACTIVE):
            raise ConflictException(f"Assessment is not open for taking (current status: {assessment.assessment_status.value}).")

        # 1. Return existing in-progress attempt if found
        existing = await self.repo.get_student_in_progress_attempt(assessment_id, student_user_id)
        questions = await self.repo.list_assessment_questions(assessment_id)
        if existing:
            return self._unpack_attempt(existing, questions, sanitize_for_student=True)

        # 2. Check attempt limits
        prior_count = await self.repo.count_student_attempts(assessment_id, student_user_id)
        if prior_count >= assessment.assessment_attempt_limit:
            raise ConflictException(f"Maximum attempt limit ({assessment.assessment_attempt_limit}) reached for this assessment.")

        if not questions:
            raise ValidationException("Cannot start assessment: No questions have been added to this assessment.")

        # 3. Create question ordering (Randomized or Sequential)
        if assessment.assessment_randomize_questions:
            q_ids = [str(q.assessment_question_id) for q in questions]
            random.shuffle(q_ids)
        else:
            sorted_q = sorted(questions, key=lambda x: x.assessment_question_order)
            q_ids = [str(q.assessment_question_id) for q in sorted_q]

        # 4. Compute expiry time (server authority)
        expires_at: Optional[datetime] = None
        if assessment.assessment_duration_minutes is not None and assessment.assessment_duration_minutes > 0:
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=assessment.assessment_duration_minutes)

        attempt_number = prior_count + 1
        new_attempt = await self.repo.create_assessment_attempt(
            assessment_id=assessment_id,
            student_id=student_user_id,
            attempt_number=attempt_number,
            question_order=q_ids,
            expires_at=expires_at
        )

        return self._unpack_attempt(new_attempt, questions, sanitize_for_student=True)

    async def get_attempt(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        attempt_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> AssessmentAttemptResponse:
        """Get an existing assessment attempt by ID."""
        assessment, subject, workspace = await self._verify_assessment_hierarchy(
            assessment_id,
            org_id,
            allow_archived_parent=True
        )

        attempt = await self.repo.get_attempt_by_id(attempt_id)
        if not attempt or attempt.attempt_assessment_id != assessment_id:
            raise NotFoundException("Assessment attempt not found.")

        questions = await self.repo.list_assessment_questions(assessment_id)

        # If student is viewing own attempt
        if attempt.attempt_student_id == requesting_user_id:
            await self._verify_workspace_access(requesting_user_id, workspace.workspace_id, is_org_admin=False)
            return self._unpack_attempt(attempt, questions, sanitize_for_student=True)

        # If teacher/admin is viewing
        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )
        return self._unpack_attempt(attempt, questions, sanitize_for_student=False)

    async def list_student_attempts(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        student_user_id: uuid.UUID
    ) -> List[AssessmentAttemptSummaryResponse]:
        """List summary of all attempts for a student on an assessment."""
        assessment, subject, workspace = await self._verify_assessment_hierarchy(
            assessment_id,
            org_id,
            allow_archived_parent=True
        )
        await self._verify_workspace_access(student_user_id, workspace.workspace_id, is_org_admin=False)

        attempts = await self.repo.list_student_attempts(assessment_id, student_user_id)
        return [
            AssessmentAttemptSummaryResponse(
                attempt_id=a.attempt_id,
                attempt_assessment_id=a.attempt_assessment_id,
                attempt_student_id=a.attempt_student_id,
                attempt_number=a.attempt_number,
                attempt_status=a.attempt_status,
                attempt_started_at=a.attempt_started_at,
                attempt_submitted_at=a.attempt_submitted_at,
                answers_count=len(a.answers) if a.answers else 0
            )
            for a in attempts
        ]

    async def save_attempt_answer(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        attempt_id: uuid.UUID,
        question_id: uuid.UUID,
        student_user_id: uuid.UUID,
        payload: StudentAttemptAnswerInput
    ) -> dict:
        """Save/upsert student's answer for a single question during an active attempt."""
        attempt = await self.repo.get_attempt_by_id(attempt_id)
        if not attempt or attempt.attempt_assessment_id != assessment_id:
            raise NotFoundException("Assessment attempt not found.")

        if attempt.attempt_student_id != student_user_id:
            raise ForbiddenException("You can only save answers for your own attempt.")

        if attempt.attempt_status == AttemptStatus.EXPIRED:
            raise AttemptExpiredException()

        if attempt.attempt_status != AttemptStatus.IN_PROGRESS:
            raise ConflictException(f"Cannot save answer: attempt is {attempt.attempt_status.value}.")

        # Server-side expiry check — auto-expire if time limit exceeded
        await self._check_and_expire_if_needed(attempt)

        aq = await self.repo.get_assessment_question_by_id(question_id)
        if not aq or aq.assessment_question_assessment_id != assessment_id:
            raise NotFoundException("Question not found in this assessment.")

        answer_data = payload.model_dump(mode="json", exclude_unset=True)
        await self.repo.upsert_attempt_answer(
            attempt_id=attempt_id,
            question_id=question_id,
            answer_value=answer_data
        )

        return {
            "status": "saved",
            "attempt_id": str(attempt_id),
            "assessment_question_id": str(question_id)
        }

    async def submit_attempt(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        attempt_id: uuid.UUID,
        student_user_id: uuid.UUID
    ) -> AssessmentAttemptResponse:
        """Submit an in-progress assessment attempt and trigger automatic evaluation."""
        attempt = await self.repo.get_attempt_by_id(attempt_id)
        if not attempt or attempt.attempt_assessment_id != assessment_id:
            raise NotFoundException("Assessment attempt not found.")

        if attempt.attempt_student_id != student_user_id:
            raise ForbiddenException("You can only submit your own attempt.")

        questions = await self.repo.list_assessment_questions(assessment_id)

        if attempt.attempt_status == AttemptStatus.SUBMITTED:
            await self.evaluate_attempt(attempt.attempt_id)
            return self._unpack_attempt(attempt, questions, sanitize_for_student=True)

        if attempt.attempt_status == AttemptStatus.EXPIRED:
            await self.evaluate_attempt(attempt.attempt_id)
            raise AttemptExpiredException()

        if attempt.attempt_status != AttemptStatus.IN_PROGRESS:
            raise ConflictException(f"Cannot submit attempt with status: {attempt.attempt_status.value}.")

        # Server-side expiry check — auto-expire if time limit exceeded
        await self._check_and_expire_if_needed(attempt)

        submitted = await self.repo.submit_attempt(attempt)
        await self.evaluate_attempt(submitted.attempt_id)
        return self._unpack_attempt(submitted, questions, sanitize_for_student=True)

    # ── Assessment Evaluation & Grading ──────────────────────────

    async def evaluate_attempt(
        self,
        attempt_id: uuid.UUID
    ) -> AssessmentResult:
        """
        Server-side evaluation of an assessment attempt.
        Idempotent: if already evaluated, returns existing result.
        Uses immutable assessment question snapshots for grading.
        """
        existing = await self.repo.get_result_by_attempt_id(attempt_id)
        if existing:
            return existing

        attempt = await self.repo.get_attempt_by_id(attempt_id)
        if not attempt:
            raise NotFoundException("Assessment attempt not found.")

        assessment = attempt.assessment
        questions = await self.repo.list_assessment_questions(attempt.attempt_assessment_id)
        answers_map: Dict[uuid.UUID, AssessmentAttemptAnswer] = {
            a.attempt_answer_question_id: a for a in (attempt.answers or [])
        }

        total_marks = Decimal("0.00")
        obtained_marks = Decimal("0.00")
        correct_count = 0
        incorrect_count = 0
        unanswered_count = 0
        pending_count = 0

        question_evaluations = []

        for aq in questions:
            marks_available = aq.assessment_question_marks
            total_marks += marks_available
            snapshot = aq.assessment_question_snapshot or {}
            q_type = snapshot.get("question_type", aq.source_question.question_type.value if aq.source_question else "mcq_single")
            options = snapshot.get("options", [])

            ans_record = answers_map.get(aq.assessment_question_id)
            ans_value = ans_record.attempt_answer_value if ans_record else None

            # Evaluation per question type
            if q_type in ("mcq_single", "true_false"):
                # Find correct option ID from snapshot
                correct_opt_id = None
                for opt in options:
                    if opt.get("option_is_correct") is True or opt.get("is_correct") is True:
                        correct_opt_id = str(opt.get("option_id"))
                        break

                selected_opt_id = ans_value.get("selected_option_id") if ans_value else None
                if selected_opt_id is not None:
                    selected_opt_id = str(selected_opt_id)

                if not selected_opt_id:
                    correctness = CorrectnessStatus.UNANSWERED
                    awarded = Decimal("0.00")
                    status = GradingStatus.GRADED
                    unanswered_count += 1
                elif correct_opt_id is not None and selected_opt_id == correct_opt_id:
                    correctness = CorrectnessStatus.CORRECT
                    awarded = marks_available
                    status = GradingStatus.GRADED
                    correct_count += 1
                    obtained_marks += awarded
                else:
                    correctness = CorrectnessStatus.INCORRECT
                    awarded = Decimal("0.00")
                    status = GradingStatus.GRADED
                    incorrect_count += 1

                question_evaluations.append({
                    "assessment_question_id": aq.assessment_question_id,
                    "answer_value": ans_value,
                    "marks_available": marks_available,
                    "marks_awarded": awarded,
                    "correctness": correctness,
                    "grading_status": status,
                    "feedback": None,
                    "graded_by": None,
                    "graded_at": datetime.now(timezone.utc)
                })

            elif q_type == "mcq_multiple":
                correct_opt_ids = {
                    str(opt.get("option_id"))
                    for opt in options
                    if opt.get("option_is_correct") is True or opt.get("is_correct") is True
                }

                selected_ids_raw = ans_value.get("selected_option_ids", []) if ans_value else []
                selected_ids = {str(x) for x in selected_ids_raw if x is not None and str(x).strip()}

                if not selected_ids:
                    correctness = CorrectnessStatus.UNANSWERED
                    awarded = Decimal("0.00")
                    status = GradingStatus.GRADED
                    unanswered_count += 1
                elif selected_ids == correct_opt_ids:
                    correctness = CorrectnessStatus.CORRECT
                    awarded = marks_available
                    status = GradingStatus.GRADED
                    correct_count += 1
                    obtained_marks += awarded
                else:
                    correctness = CorrectnessStatus.INCORRECT
                    awarded = Decimal("0.00")
                    status = GradingStatus.GRADED
                    incorrect_count += 1

                question_evaluations.append({
                    "assessment_question_id": aq.assessment_question_id,
                    "answer_value": ans_value,
                    "marks_available": marks_available,
                    "marks_awarded": awarded,
                    "correctness": correctness,
                    "grading_status": status,
                    "feedback": None,
                    "graded_by": None,
                    "graded_at": datetime.now(timezone.utc)
                })

            elif q_type == "short_answer":
                text_ans = (ans_value.get("text_answer") or "").strip() if ans_value else ""
                if not text_ans:
                    # Unanswered short answer -> graded as 0.00, unanswered
                    correctness = CorrectnessStatus.UNANSWERED
                    awarded = Decimal("0.00")
                    status = GradingStatus.GRADED
                    unanswered_count += 1
                    graded_at = datetime.now(timezone.utc)
                else:
                    # Provided text -> pending teacher manual evaluation
                    correctness = CorrectnessStatus.PENDING
                    awarded = Decimal("0.00")
                    status = GradingStatus.PENDING
                    pending_count += 1
                    graded_at = None

                question_evaluations.append({
                    "assessment_question_id": aq.assessment_question_id,
                    "answer_value": ans_value,
                    "marks_available": marks_available,
                    "marks_awarded": awarded,
                    "correctness": correctness,
                    "grading_status": status,
                    "feedback": None,
                    "graded_by": None,
                    "graded_at": graded_at
                })

        percentage = (
            (obtained_marks / total_marks * Decimal("100.00")).quantize(Decimal("0.01"))
            if total_marks > 0
            else Decimal("0.00")
        )

        overall_status = (
            ResultStatus.PENDING_MANUAL_GRADING
            if pending_count > 0
            else ResultStatus.COMPLETED
        )

        if overall_status == ResultStatus.COMPLETED:
            if assessment.assessment_passing_marks is not None:
                passed = obtained_marks >= assessment.assessment_passing_marks
            else:
                passed = True
            result_graded_at = datetime.now(timezone.utc)
        else:
            passed = None
            result_graded_at = None

        result_record = await self.repo.create_assessment_result(
            attempt_id=attempt_id,
            assessment_id=attempt.attempt_assessment_id,
            student_id=attempt.attempt_student_id,
            total_marks=total_marks,
            obtained_marks=obtained_marks,
            percentage=percentage,
            passed=passed,
            status=overall_status,
            correct_count=correct_count,
            incorrect_count=incorrect_count,
            unanswered_count=unanswered_count,
            pending_count=pending_count,
            graded_at=result_graded_at
        )

        for qe in question_evaluations:
            await self.repo.create_result_question(
                result_id=result_record.result_id,
                assessment_question_id=qe["assessment_question_id"],
                answer_value=qe["answer_value"],
                marks_available=qe["marks_available"],
                marks_awarded=qe["marks_awarded"],
                correctness=qe["correctness"],
                grading_status=qe["grading_status"],
                feedback=qe["feedback"],
                graded_by=qe["graded_by"],
                graded_at=qe["graded_at"]
            )

        refreshed = await self.repo.get_result_by_id(result_record.result_id)
        return refreshed or result_record

    async def get_attempt_result(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        attempt_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> AssessmentResultResponse:
        """Get the full result of an assessment attempt with authorization checks."""
        assessment, subject, workspace = await self._verify_assessment_hierarchy(
            assessment_id,
            org_id,
            allow_archived_parent=True
        )

        attempt = await self.repo.get_attempt_by_id(attempt_id)
        if not attempt or attempt.attempt_assessment_id != assessment_id:
            raise NotFoundException("Assessment attempt not found.")

        # RBAC: Student must own attempt; else Teacher / Admin
        if attempt.attempt_student_id == requesting_user_id:
            await self._verify_workspace_access(requesting_user_id, workspace.workspace_id, is_org_admin=False)
        else:
            await self._verify_teacher_or_admin(
                requesting_user_id,
                org_id,
                subject.subject_id,
                workspace.workspace_id,
                is_org_admin
            )

        if attempt.attempt_status == AttemptStatus.IN_PROGRESS:
            raise ConflictException("Cannot view result: Assessment attempt is still in progress.")

        # If result hasn't been created yet, evaluate now
        result = await self.repo.get_result_by_attempt_id(attempt_id)
        if not result:
            result = await self.evaluate_attempt(attempt_id)

        questions = await self.repo.list_assessment_questions(assessment_id)
        rq_map = {rq.result_question_assessment_question_id: rq for rq in (result.question_results or [])}

        formatted_q_results = []
        for q in questions:
            rq = rq_map.get(q.assessment_question_id)
            snapshot = q.assessment_question_snapshot or {}

            options_data = []
            for opt in snapshot.get("options", []):
                options_data.append(
                    QuestionOptionResponse(
                        option_id=uuid.UUID(str(opt["option_id"])) if opt.get("option_id") else None,
                        option_question_id=None,
                        option_text=opt.get("option_text", ""),
                        option_order=opt.get("option_order", 1),
                        option_is_correct=opt.get("option_is_correct", opt.get("is_correct", False))
                    )
                )

            formatted_q_results.append(
                AssessmentResultQuestionResponse(
                    result_question_id=rq.result_question_id if rq else uuid.uuid4(),
                    assessment_question_id=q.assessment_question_id,
                    order=q.assessment_question_order,
                    question_type=QuestionType(snapshot.get("question_type", "mcq_single")),
                    question_text=snapshot.get("question_text", ""),
                    question_explanation=snapshot.get("question_explanation"),
                    options=options_data,
                    answer_value=rq.result_question_answer_value if rq else None,
                    marks_available=rq.result_question_marks_available if rq else q.assessment_question_marks,
                    marks_awarded=rq.result_question_marks_awarded if rq else Decimal("0.00"),
                    correctness=rq.result_question_correctness if rq else CorrectnessStatus.UNANSWERED,
                    grading_status=rq.result_question_grading_status if rq else GradingStatus.GRADED,
                    feedback=rq.result_question_feedback if rq else None,
                    graded_by=rq.result_question_graded_by if rq else None,
                    graded_at=rq.result_question_graded_at if rq else None
                )
            )

        return AssessmentResultResponse(
            result_id=result.result_id,
            attempt_id=result.result_attempt_id,
            assessment_id=result.result_assessment_id,
            student_id=result.result_student_id,
            assessment_title=assessment.assessment_title,
            attempt_number=attempt.attempt_number,
            attempt_status=attempt.attempt_status,
            attempt_started_at=attempt.attempt_started_at,
            attempt_submitted_at=attempt.attempt_submitted_at,
            total_marks=result.result_total_marks,
            obtained_marks=result.result_obtained_marks,
            percentage=result.result_percentage,
            passed=result.result_passed,
            status=result.result_status,
            correct_count=result.result_correct_count,
            incorrect_count=result.result_incorrect_count,
            unanswered_count=result.result_unanswered_count,
            pending_count=result.result_pending_count,
            graded_at=result.result_graded_at,
            questions=formatted_q_results
        )

    async def grade_question(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        attempt_id: uuid.UUID,
        question_id: uuid.UUID,
        grader_user_id: uuid.UUID,
        is_org_admin: bool,
        payload: ManualGradeInput
    ) -> AssessmentResultResponse:
        """Manually grade an assessment question (e.g. Short Answer) and recalculate result."""
        assessment, subject, workspace = await self._verify_assessment_hierarchy(assessment_id, org_id)
        await self._verify_teacher_or_admin(
            grader_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        attempt = await self.repo.get_attempt_by_id(attempt_id)
        if not attempt or attempt.attempt_assessment_id != assessment_id:
            raise NotFoundException("Assessment attempt not found.")

        if attempt.attempt_status == AttemptStatus.IN_PROGRESS:
            raise ConflictException("Cannot grade an in-progress attempt.")

        # Ensure attempt is evaluated
        result = await self.evaluate_attempt(attempt_id)

        aq = await self.repo.get_assessment_question_by_id(question_id)
        if not aq or aq.assessment_question_assessment_id != assessment_id:
            raise NotFoundException("Assessment question not found.")

        if payload.marks_awarded > aq.assessment_question_marks:
            raise ValidationException(f"Marks awarded ({payload.marks_awarded}) cannot exceed available question marks ({aq.assessment_question_marks}).")

        rq = await self.repo.get_result_question(result.result_id, question_id)
        if not rq:
            raise NotFoundException("Question evaluation record not found for this attempt.")

        # Update question evaluation
        rq.result_question_marks_awarded = payload.marks_awarded
        rq.result_question_feedback = payload.feedback
        rq.result_question_grading_status = GradingStatus.GRADED
        rq.result_question_graded_by = grader_user_id
        rq.result_question_graded_at = datetime.now(timezone.utc)

        if payload.marks_awarded == rq.result_question_marks_available:
            rq.result_question_correctness = CorrectnessStatus.CORRECT
        elif payload.marks_awarded == Decimal("0.00"):
            rq.result_question_correctness = CorrectnessStatus.INCORRECT
        else:
            rq.result_question_correctness = CorrectnessStatus.CORRECT

        await self.db.flush()

        # Recalculate result
        refreshed_result = await self.repo.get_result_by_id(result.result_id)
        question_results = refreshed_result.question_results if refreshed_result else []

        new_obtained = sum((q.result_question_marks_awarded for q in question_results), Decimal("0.00"))
        new_total = sum((q.result_question_marks_available for q in question_results), Decimal("0.00"))
        pending_cnt = sum(1 for q in question_results if q.result_question_grading_status == GradingStatus.PENDING)
        correct_cnt = sum(1 for q in question_results if q.result_question_correctness == CorrectnessStatus.CORRECT)
        incorrect_cnt = sum(1 for q in question_results if q.result_question_correctness == CorrectnessStatus.INCORRECT)
        unanswered_cnt = sum(1 for q in question_results if q.result_question_correctness == CorrectnessStatus.UNANSWERED)

        new_percentage = (
            (new_obtained / new_total * Decimal("100.00")).quantize(Decimal("0.01"))
            if new_total > 0
            else Decimal("0.00")
        )

        refreshed_result.result_obtained_marks = new_obtained
        refreshed_result.result_percentage = new_percentage
        refreshed_result.result_correct_count = correct_cnt
        refreshed_result.result_incorrect_count = incorrect_cnt
        refreshed_result.result_unanswered_count = unanswered_cnt
        refreshed_result.result_pending_count = pending_cnt
        refreshed_result.result_status = (
            ResultStatus.PENDING_MANUAL_GRADING
            if pending_cnt > 0
            else ResultStatus.COMPLETED
        )

        if refreshed_result.result_status == ResultStatus.COMPLETED:
            refreshed_result.result_graded_at = datetime.now(timezone.utc)
            if assessment.assessment_passing_marks is not None:
                refreshed_result.result_passed = (new_obtained >= assessment.assessment_passing_marks)
            else:
                refreshed_result.result_passed = True
        else:
            refreshed_result.result_passed = None

        await self.db.flush()
        return await self.get_attempt_result(org_id, assessment_id, attempt_id, grader_user_id, is_org_admin)

    async def list_assessment_results(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> List[TeacherAssessmentResultSummaryResponse]:
        """List all attempt results for an assessment (Teachers/Admins only)."""
        assessment, subject, workspace = await self._verify_assessment_hierarchy(
            assessment_id,
            org_id,
            allow_archived_parent=True
        )
        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        stmt = (
            select(AssessmentAttempt)
            .where(AssessmentAttempt.attempt_assessment_id == assessment_id)
            .options(
                selectinload(AssessmentAttempt.student),
                selectinload(AssessmentAttempt.answers)
            )
            .order_by(AssessmentAttempt.attempt_created_at.desc())
        )
        res = await self.db.execute(stmt)
        attempts = list(res.scalars().all())

        results_list: List[TeacherAssessmentResultSummaryResponse] = []
        for att in attempts:
            if att.attempt_status in (AttemptStatus.SUBMITTED, AttemptStatus.EXPIRED):
                result = await self.evaluate_attempt(att.attempt_id)
                results_list.append(
                    TeacherAssessmentResultSummaryResponse(
                        result_id=result.result_id,
                        attempt_id=att.attempt_id,
                        student_id=att.attempt_student_id,
                        student_name=f"{att.student.user_first_name} {att.student.user_last_name}" if att.student else None,
                        student_email=att.student.user_email if att.student else None,
                        attempt_number=att.attempt_number,
                        attempt_status=att.attempt_status,
                        total_marks=result.result_total_marks,
                        obtained_marks=result.result_obtained_marks,
                        percentage=result.result_percentage,
                        passed=result.result_passed,
                        status=result.result_status,
                        pending_count=result.result_pending_count,
                        started_at=att.attempt_started_at,
                        submitted_at=att.attempt_submitted_at
                    )
                )
            else:
                results_list.append(
                    TeacherAssessmentResultSummaryResponse(
                        result_id=None,
                        attempt_id=att.attempt_id,
                        student_id=att.attempt_student_id,
                        student_name=f"{att.student.user_first_name} {att.student.user_last_name}" if att.student else None,
                        student_email=att.student.user_email if att.student else None,
                        attempt_number=att.attempt_number,
                        attempt_status=att.attempt_status,
                        total_marks=assessment.assessment_total_marks,
                        obtained_marks=Decimal("0.00"),
                        percentage=Decimal("0.00"),
                        passed=None,
                        status=ResultStatus.PENDING_MANUAL_GRADING,
                        pending_count=0,
                        started_at=att.attempt_started_at,
                        submitted_at=att.attempt_submitted_at
                    )
                )
        return results_list

    # ── Assessment Analytics Service (Step 10.11) ────────────────

    async def get_assessment_analytics(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> AssessmentAnalyticsResponse:
        """
        Compute comprehensive assessment analytics for teachers and organization admins.
        Enforces tenant isolation and subject teacher authorization.
        """
        assessment, subject, workspace = await self._verify_assessment_hierarchy(
            assessment_id,
            org_id,
            allow_archived_parent=True
        )
        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        # 1. Total enrolled students in workspace
        enrolled_count = await self.repo.get_workspace_student_count(workspace.workspace_id)

        # 2. Fetch all attempts and ensure submitted/expired attempts have results evaluated
        attempts = await self.repo.get_assessment_attempts_for_analytics(assessment_id)

        attempt_results_map: Dict[uuid.UUID, AssessmentResult] = {}
        for att in attempts:
            if att.attempt_status in (AttemptStatus.SUBMITTED, AttemptStatus.EXPIRED):
                res = await self.evaluate_attempt(att.attempt_id)
                if res:
                    attempt_results_map[att.attempt_id] = res

        # 3. Overview metrics
        students_attempted_set = {att.attempt_student_id for att in attempts}
        total_students_attempted = len(students_attempted_set)
        total_attempts = len(attempts)
        submitted_attempts = sum(1 for a in attempts if a.attempt_status == AttemptStatus.SUBMITTED)
        expired_attempts = sum(1 for a in attempts if a.attempt_status == AttemptStatus.EXPIRED)
        in_progress_attempts = sum(1 for a in attempts if a.attempt_status == AttemptStatus.IN_PROGRESS)

        completed_evaluations = sum(1 for r in attempt_results_map.values() if r.result_status == ResultStatus.COMPLETED)
        pending_manual_grading = sum(1 for r in attempt_results_map.values() if r.result_status == ResultStatus.PENDING_MANUAL_GRADING or r.result_pending_count > 0)

        passed_count = sum(1 for r in attempt_results_map.values() if r.result_status == ResultStatus.COMPLETED and r.result_passed is True)
        failed_count = sum(1 for r in attempt_results_map.values() if r.result_status == ResultStatus.COMPLETED and r.result_passed is False)

        pass_percentage = (
            round((passed_count / completed_evaluations) * 100.0, 2)
            if completed_evaluations > 0
            else None
        )
        participation_rate = (
            round((total_students_attempted / enrolled_count) * 100.0, 2)
            if enrolled_count > 0
            else None
        )

        overview = AssessmentAnalyticsOverview(
            total_enrolled_students=enrolled_count,
            total_students_attempted=total_students_attempted,
            total_attempts=total_attempts,
            total_submitted_attempts=submitted_attempts,
            total_expired_attempts=expired_attempts,
            total_in_progress_attempts=in_progress_attempts,
            total_completed_evaluations=completed_evaluations,
            total_pending_manual_grading=pending_manual_grading,
            total_passed=passed_count,
            total_failed=failed_count,
            pass_percentage=pass_percentage,
            participation_rate=participation_rate
        )

        # 4. Score Statistics across completed evaluations
        completed_results = [r for r in attempt_results_map.values() if r.result_status == ResultStatus.COMPLETED]
        if completed_results:
            percentages = [float(r.result_percentage) for r in completed_results]
            obtained_marks_list = [float(r.result_obtained_marks) for r in completed_results]

            avg_percentage = round(sum(percentages) / len(percentages), 2)
            med_percentage = round(float(statistics.median(percentages)), 2)
            high_percentage = round(max(percentages), 2)
            low_percentage = round(min(percentages), 2)
            avg_obtained = round(sum(obtained_marks_list) / len(obtained_marks_list), 2)
        else:
            avg_percentage = None
            med_percentage = None
            high_percentage = None
            low_percentage = None
            avg_obtained = None

        score_statistics = AssessmentScoreStatistics(
            average_percentage=avg_percentage,
            median_percentage=med_percentage,
            highest_percentage=high_percentage,
            lowest_percentage=low_percentage,
            average_obtained_marks=avg_obtained,
            total_marks=float(assessment.assessment_total_marks),
            passing_marks=float(assessment.assessment_passing_marks) if assessment.assessment_passing_marks is not None else None
        )

        # 5. Attempt Statistics
        attempts_per_student_counts: Dict[uuid.UUID, int] = {}
        for a in attempts:
            attempts_per_student_counts[a.attempt_student_id] = attempts_per_student_counts.get(a.attempt_student_id, 0) + 1

        single_attempt_count = sum(1 for cnt in attempts_per_student_counts.values() if cnt == 1)
        multiple_attempts_count = sum(1 for cnt in attempts_per_student_counts.values() if cnt > 1)
        avg_attempts_per_student = (
            round(total_attempts / total_students_attempted, 2)
            if total_students_attempted > 0
            else None
        )

        attempt_statistics = AssessmentAttemptStatistics(
            total_attempts=total_attempts,
            average_attempts_per_student=avg_attempts_per_student,
            single_attempt_student_count=single_attempt_count,
            multiple_attempts_student_count=multiple_attempts_count
        )

        # 6. Question-level Statistics
        questions = await self.repo.list_assessment_questions(assessment_id)
        result_questions = await self.repo.get_assessment_result_questions_for_analytics(assessment_id)

        rq_by_question: Dict[uuid.UUID, List[AssessmentResultQuestion]] = {}
        for rq in result_questions:
            q_id = rq.result_question_assessment_question_id
            if q_id not in rq_by_question:
                rq_by_question[q_id] = []
            rq_by_question[q_id].append(rq)

        question_stats_list: List[AssessmentQuestionAnalyticsItem] = []
        for q in questions:
            snapshot = q.assessment_question_snapshot or {}
            q_type = QuestionType(snapshot.get("question_type", q.source_question.question_type.value if q.source_question else "mcq_single"))
            q_text = snapshot.get("question_text", "")
            marks_avail = float(q.assessment_question_marks)

            rq_list = rq_by_question.get(q.assessment_question_id, [])
            eval_count = len(rq_list)
            corr_count = sum(1 for item in rq_list if item.result_question_correctness == CorrectnessStatus.CORRECT)
            incorr_count = sum(1 for item in rq_list if item.result_question_correctness == CorrectnessStatus.INCORRECT)
            unans_count = sum(1 for item in rq_list if item.result_question_correctness == CorrectnessStatus.UNANSWERED)
            pend_count = sum(1 for item in rq_list if item.result_question_grading_status == GradingStatus.PENDING)

            if eval_count > 0:
                avg_awarded = round(sum(float(item.result_question_marks_awarded) for item in rq_list) / eval_count, 2)
            else:
                avg_awarded = None

            graded_objective_total = corr_count + incorr_count
            if graded_objective_total > 0:
                accuracy = round((corr_count / graded_objective_total) * 100.0, 2)
            else:
                accuracy = None

            question_stats_list.append(
                AssessmentQuestionAnalyticsItem(
                    assessment_question_id=q.assessment_question_id,
                    question_order=q.assessment_question_order,
                    question_type=q_type,
                    question_text=q_text,
                    marks_available=marks_avail,
                    evaluated_count=eval_count,
                    correct_count=corr_count,
                    incorrect_count=incorr_count,
                    unanswered_count=unans_count,
                    pending_count=pend_count,
                    average_marks_awarded=avg_awarded,
                    accuracy_percentage=accuracy
                )
            )

        # 7. Student Performance Breakdown
        attempts_by_student: Dict[uuid.UUID, List[AssessmentAttempt]] = {}
        for a in attempts:
            if a.attempt_student_id not in attempts_by_student:
                attempts_by_student[a.attempt_student_id] = []
            attempts_by_student[a.attempt_student_id].append(a)

        student_performance_list: List[AssessmentStudentPerformanceItem] = []
        for s_id, s_attempts in attempts_by_student.items():
            first_att = s_attempts[0]
            student_user = first_att.student
            student_name = f"{student_user.user_first_name} {student_user.user_last_name}" if student_user else None
            student_email = student_user.user_email if student_user else None

            sorted_s_attempts = sorted(s_attempts, key=lambda x: x.attempt_number)

            attempt_items: List[AssessmentStudentAttemptItem] = []
            has_pending = False
            best_pct: Optional[float] = None
            best_obtained: Optional[float] = None

            for a in sorted_s_attempts:
                r = attempt_results_map.get(a.attempt_id)
                dur: Optional[int] = None
                if a.attempt_submitted_at and a.attempt_started_at:
                    dur = max(0, int((a.attempt_submitted_at - a.attempt_started_at).total_seconds()))

                pct = float(r.result_percentage) if r else None
                obt = float(r.result_obtained_marks) if r else None
                pas = r.result_passed if r else None
                rst = r.result_status if r else None
                p_cnt = r.result_pending_count if r else 0

                if r and (r.result_status == ResultStatus.PENDING_MANUAL_GRADING or r.result_pending_count > 0):
                    has_pending = True

                if r and r.result_status == ResultStatus.COMPLETED and pct is not None:
                    if best_pct is None or pct > best_pct:
                        best_pct = pct
                        best_obtained = obt

                attempt_items.append(
                    AssessmentStudentAttemptItem(
                        attempt_id=a.attempt_id,
                        attempt_number=a.attempt_number,
                        attempt_status=a.attempt_status,
                        started_at=a.attempt_started_at,
                        submitted_at=a.attempt_submitted_at,
                        duration_seconds=dur,
                        obtained_marks=obt,
                        percentage=pct,
                        passed=pas,
                        status=rst,
                        pending_count=p_cnt
                    )
                )

            latest_att = sorted_s_attempts[-1]
            latest_res = attempt_results_map.get(latest_att.attempt_id)

            student_performance_list.append(
                AssessmentStudentPerformanceItem(
                    student_id=s_id,
                    student_name=student_name,
                    student_email=student_email,
                    total_attempts=len(sorted_s_attempts),
                    latest_attempt_number=latest_att.attempt_number,
                    latest_attempt_status=latest_att.attempt_status,
                    latest_percentage=float(latest_res.result_percentage) if latest_res else None,
                    latest_obtained_marks=float(latest_res.result_obtained_marks) if latest_res else None,
                    latest_passed=latest_res.result_passed if latest_res else None,
                    latest_result_status=latest_res.result_status if latest_res else None,
                    best_percentage=best_pct,
                    best_obtained_marks=best_obtained,
                    has_pending_grading=has_pending,
                    attempts=attempt_items
                )
            )

        student_performance_list.sort(key=lambda x: (x.student_name or "").lower())

        return AssessmentAnalyticsResponse(
            assessment_id=assessment.assessment_id,
            assessment_title=assessment.assessment_title,
            assessment_type=assessment.assessment_type,
            assessment_status=assessment.assessment_status,
            overview=overview,
            score_statistics=score_statistics,
            attempt_statistics=attempt_statistics,
            question_statistics=question_stats_list,
            student_statistics=student_performance_list
        )

    async def get_student_self_analytics(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        student_user_id: uuid.UUID
    ) -> StudentSelfAnalyticsResponse:
        """
        Get student's own attempts and performance analytics for an assessment.
        Ensures tenant isolation and student privacy.
        """
        assessment, subject, workspace = await self._verify_assessment_hierarchy(
            assessment_id,
            org_id,
            allow_archived_parent=True
        )
        await self._verify_workspace_access(student_user_id, workspace.workspace_id, is_org_admin=False)

        attempts = await self.repo.get_student_attempts_for_analytics(assessment_id, student_user_id)

        attempt_items: List[AssessmentStudentAttemptItem] = []
        has_pending = False
        best_pct: Optional[float] = None
        best_obtained: Optional[float] = None
        latest_res: Optional[AssessmentResult] = None

        for a in attempts:
            r: Optional[AssessmentResult] = None
            if a.attempt_status in (AttemptStatus.SUBMITTED, AttemptStatus.EXPIRED):
                r = await self.evaluate_attempt(a.attempt_id)

            dur: Optional[int] = None
            if a.attempt_submitted_at and a.attempt_started_at:
                dur = max(0, int((a.attempt_submitted_at - a.attempt_started_at).total_seconds()))

            pct = float(r.result_percentage) if r else None
            obt = float(r.result_obtained_marks) if r else None
            pas = r.result_passed if r else None
            rst = r.result_status if r else None
            p_cnt = r.result_pending_count if r else 0

            if r and (r.result_status == ResultStatus.PENDING_MANUAL_GRADING or r.result_pending_count > 0):
                has_pending = True

            if r and r.result_status == ResultStatus.COMPLETED and pct is not None:
                if best_pct is None or pct > best_pct:
                    best_pct = pct
                    best_obtained = obt

            attempt_items.append(
                AssessmentStudentAttemptItem(
                    attempt_id=a.attempt_id,
                    attempt_number=a.attempt_number,
                    attempt_status=a.attempt_status,
                    started_at=a.attempt_started_at,
                    submitted_at=a.attempt_submitted_at,
                    duration_seconds=dur,
                    obtained_marks=obt,
                    percentage=pct,
                    passed=pas,
                    status=rst,
                    pending_count=p_cnt
                )
            )

        if attempts:
            latest_att = attempts[-1]
            if latest_att.attempt_status in (AttemptStatus.SUBMITTED, AttemptStatus.EXPIRED):
                latest_res = await self.evaluate_attempt(latest_att.attempt_id)

        total_used = len(attempts)
        remaining = max(0, assessment.assessment_attempt_limit - total_used)

        return StudentSelfAnalyticsResponse(
            assessment_id=assessment.assessment_id,
            assessment_title=assessment.assessment_title,
            assessment_total_marks=float(assessment.assessment_total_marks),
            attempt_limit=assessment.assessment_attempt_limit,
            total_attempts_used=total_used,
            attempts_remaining=remaining,
            latest_percentage=float(latest_res.result_percentage) if latest_res else None,
            latest_obtained_marks=float(latest_res.result_obtained_marks) if latest_res else None,
            best_percentage=best_pct,
            best_obtained_marks=best_obtained,
            passed=latest_res.result_passed if latest_res else None,
            has_pending_grading=has_pending,
            attempts=attempt_items
        )

    # ── Learning Analytics & Question Difficulty Service Methods (Step 10.12) ──

    MIN_SAMPLE_SIZE = 5

    @classmethod
    def classify_observed_difficulty(
        cls,
        accuracy_percentage: Optional[float],
        evaluated_count: int
    ) -> tuple[ObservedDifficultyBand, str, bool]:
        """
        Centralized descriptive difficulty classification rule:
        - Sample size < MIN_SAMPLE_SIZE: Insufficient Sample
        - Accuracy >= 70%: Easier Observed
        - Accuracy >= 40% and < 70%: Moderate Observed
        - Accuracy < 40%: Harder Observed
        """
        if evaluated_count < cls.MIN_SAMPLE_SIZE or accuracy_percentage is None:
            return ObservedDifficultyBand.INSUFFICIENT_SAMPLE, "Insufficient Sample", True
        if accuracy_percentage >= 70.0:
            return ObservedDifficultyBand.EASIER_OBSERVED, "Easier Observed", False
        if accuracy_percentage >= 40.0:
            return ObservedDifficultyBand.MODERATE_OBSERVED, "Moderate Observed", False
        return ObservedDifficultyBand.HARDER_OBSERVED, "Harder Observed", False

    async def get_student_learning_analytics(
        self,
        org_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        target_student_id: uuid.UUID,
        is_org_admin: bool
    ) -> StudentLearningAnalyticsResponse:
        """
        Get longitudinal learning analytics for a student across all assessments.
        Enforces tenant isolation and student privacy.
        """
        if requesting_user_id != target_student_id and not is_org_admin:
            is_teacher = (
                await self.repo.is_user_any_subject_teacher(org_id, requesting_user_id)
                or await self.repo.is_user_teacher_or_admin_role(org_id, requesting_user_id)
            )
            if not is_teacher:
                raise ForbiddenException("Access denied. You can only view your own learning analytics.")

        results = await self.repo.get_student_all_results_for_learning_analytics(target_student_id, org_id)
        result_questions = await self.repo.get_student_all_result_questions_for_learning_analytics(target_student_id, org_id)

        # Get student details
        student_name: Optional[str] = None
        student_email: Optional[str] = None
        if results and results[0].student:
            student_name = f"{results[0].student.user_first_name} {results[0].student.user_last_name}".strip()
            student_email = results[0].student.user_email

        # 1. Overview KPIs
        distinct_assessments = set(r.result_assessment_id for r in results)
        completed_results = [r for r in results if r.result_status == ResultStatus.COMPLETED]
        pending_results = [r for r in results if r.result_status == ResultStatus.PENDING_MANUAL_GRADING or r.result_pending_count > 0]
        completed_percentages = [float(r.result_percentage) for r in completed_results]

        avg_pct = round(sum(completed_percentages) / len(completed_percentages), 2) if completed_percentages else None
        best_pct = max(completed_percentages) if completed_percentages else None
        latest_pct = completed_percentages[-1] if completed_percentages else None

        passed_count = sum(1 for r in completed_results if r.result_passed is True)
        failed_count = sum(1 for r in completed_results if r.result_passed is False)

        overview = StudentLearningOverview(
            total_assessments_attempted=len(distinct_assessments),
            total_assessments_completed=len(set(r.result_assessment_id for r in completed_results)),
            total_assessments_pending_grading=len(set(r.result_assessment_id for r in pending_results)),
            total_attempts_count=len(results),
            average_percentage=avg_pct,
            best_percentage=best_pct,
            latest_percentage=latest_pct,
            total_passed_count=passed_count,
            total_failed_count=failed_count
        )

        # 2. Performance Progression Trend
        progression: List[StudentPerformanceTrendPoint] = []
        for r in results:
            asm = r.assessment
            subj = asm.subject if asm else None
            progression.append(
                StudentPerformanceTrendPoint(
                    assessment_id=r.result_assessment_id,
                    assessment_title=asm.assessment_title if asm else "Assessment",
                    subject_id=subj.subject_id if subj else uuid.UUID(int=0),
                    subject_name=subj.subject_name if subj else "Subject",
                    attempt_id=r.result_attempt_id,
                    attempt_number=r.attempt.attempt_number if r.attempt else 1,
                    date=r.result_created_at,
                    percentage=float(r.result_percentage),
                    obtained_marks=float(r.result_obtained_marks),
                    total_marks=float(r.result_total_marks),
                    passed=r.result_passed,
                    status=r.result_status
                )
            )

        # 3. Trend Calculations (Last 5 window)
        recent_window = completed_percentages[-5:] if completed_percentages else []
        recent_avg = round(sum(recent_window) / len(recent_window), 2) if recent_window else None
        improvement = round(completed_percentages[-1] - completed_percentages[-2], 2) if len(completed_percentages) >= 2 else None

        trend = StudentLearningTrend(
            recent_average_percentage=recent_avg,
            historical_average_percentage=avg_pct,
            improvement_from_previous=improvement,
            recent_window_size=5
        )

        # 4. Subject-Level Breakdown
        subject_map: Dict[uuid.UUID, Dict[str, Any]] = {}
        for r in results:
            asm = r.assessment
            if not asm or not asm.subject:
                continue
            sid = asm.subject.subject_id
            sname = asm.subject.subject_name
            if sid not in subject_map:
                subject_map[sid] = {
                    "subject_id": sid,
                    "subject_name": sname,
                    "assessments": set(),
                    "completed_assessments": set(),
                    "percentages": [],
                    "passed": 0,
                    "failed": 0
                }
            subject_map[sid]["assessments"].add(r.result_assessment_id)
            if r.result_status == ResultStatus.COMPLETED:
                subject_map[sid]["completed_assessments"].add(r.result_assessment_id)
                subject_map[sid]["percentages"].append(float(r.result_percentage))
                if r.result_passed is True:
                    subject_map[sid]["passed"] += 1
                elif r.result_passed is False:
                    subject_map[sid]["failed"] += 1

        subject_items: List[StudentSubjectPerformanceItem] = []
        for sid, sdata in subject_map.items():
            pcts = sdata["percentages"]
            s_avg = round(sum(pcts) / len(pcts), 2) if pcts else None
            s_best = max(pcts) if pcts else None
            s_latest = pcts[-1] if pcts else None

            # Calculate objective accuracy for this subject
            subj_rqs = [
                rq for rq in result_questions
                if rq.assessment_question and rq.assessment_question.assessment_question_assessment_id in sdata["assessments"]
            ]
            obj_eval = [
                rq for rq in subj_rqs
                if rq.result_question_grading_status == GradingStatus.GRADED
                and ((rq.assessment_question.assessment_question_snapshot or {}).get("type") != "short_answer" and (rq.assessment_question.assessment_question_snapshot or {}).get("question_type") != "short_answer")
            ]
            obj_correct = sum(1 for rq in obj_eval if rq.result_question_correctness == CorrectnessStatus.CORRECT)
            obj_acc = round((obj_correct / len(obj_eval)) * 100, 2) if obj_eval else None

            subject_items.append(
                StudentSubjectPerformanceItem(
                    subject_id=sid,
                    subject_name=sdata["subject_name"],
                    assessments_attempted=len(sdata["assessments"]),
                    assessments_completed=len(sdata["completed_assessments"]),
                    average_percentage=s_avg,
                    best_percentage=s_best,
                    latest_percentage=s_latest,
                    objective_accuracy_percentage=obj_acc,
                    passed_count=sdata["passed"],
                    failed_count=sdata["failed"]
                )
            )

        # 5. Question-Type Breakdown
        qtype_items: List[StudentQuestionTypePerformanceItem] = []
        for qtype in [QuestionType.MCQ_SINGLE, QuestionType.MCQ_MULTIPLE, QuestionType.TRUE_FALSE, QuestionType.SHORT_ANSWER]:
            type_rqs = [
                rq for rq in result_questions
                if rq.assessment_question and (
                    (rq.assessment_question.assessment_question_snapshot or {}).get("type") == qtype.value
                    or (rq.assessment_question.assessment_question_snapshot or {}).get("question_type") == qtype.value
                )
            ]
            eval_count = sum(1 for rq in type_rqs if rq.result_question_grading_status == GradingStatus.GRADED)
            correct_count = sum(1 for rq in type_rqs if rq.result_question_correctness == CorrectnessStatus.CORRECT)
            incorrect_count = sum(1 for rq in type_rqs if rq.result_question_correctness == CorrectnessStatus.INCORRECT)
            unanswered_count = sum(1 for rq in type_rqs if rq.result_question_correctness == CorrectnessStatus.UNANSWERED)
            pending_count = sum(1 for rq in type_rqs if rq.result_question_grading_status == GradingStatus.PENDING)

            if qtype == QuestionType.SHORT_ANSWER:
                graded_awarded = sum(float(rq.result_question_marks_awarded) for rq in type_rqs if rq.result_question_grading_status == GradingStatus.GRADED)
                graded_avail = sum(float(rq.result_question_marks_available) for rq in type_rqs if rq.result_question_grading_status == GradingStatus.GRADED)
                acc = round((graded_awarded / graded_avail) * 100, 2) if graded_avail > 0 else None
            else:
                acc = round((correct_count / eval_count) * 100, 2) if eval_count > 0 else None

            qtype_items.append(
                StudentQuestionTypePerformanceItem(
                    question_type=qtype,
                    evaluated_count=eval_count,
                    correct_count=correct_count,
                    incorrect_count=incorrect_count,
                    unanswered_count=unanswered_count,
                    pending_count=pending_count,
                    accuracy_percentage=acc
                )
            )

        # 6. Recent Assessments (Last 5 descending)
        recent_assessments = progression[-5:][::-1]

        return StudentLearningAnalyticsResponse(
            student_id=target_student_id,
            student_name=student_name,
            student_email=student_email,
            overview=overview,
            trend=trend,
            performance_progression=progression,
            subject_performance=subject_items,
            question_type_performance=qtype_items,
            recent_assessments=recent_assessments
        )

    async def get_subject_learning_analytics(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> SubjectLearningAnalyticsResponse:
        """
        Get subject-level longitudinal learning progression and assessment performance.
        Accessible only to authorized Teachers and Admins.
        """
        subject, workspace = await self._verify_subject_hierarchy(subject_id, org_id, allow_archived_parent=True)
        await self._verify_teacher_or_admin(requesting_user_id, org_id, subject_id, workspace.workspace_id, is_org_admin)

        assessments = await self.repo.get_subject_assessments_and_results_for_analytics(subject_id)
        enrolled_students = await self.repo.get_workspace_student_count(workspace.workspace_id)

        all_results: List[AssessmentResult] = []
        attempted_students = set()
        assessment_trends: List[Dict[str, Any]] = []

        for asm in assessments:
            asm_results = asm.results or []
            completed = [r for r in asm_results if r.result_status == ResultStatus.COMPLETED]
            pcts = [float(r.result_percentage) for r in completed]
            avg_p = round(sum(pcts) / len(pcts), 2) if pcts else None

            for r in asm_results:
                all_results.append(r)
                attempted_students.add(r.result_student_id)

            passed_count = sum(1 for r in completed if r.result_passed is True)
            pass_rate = round((passed_count / len(completed)) * 100, 2) if completed else None

            assessment_trends.append({
                "assessment_id": str(asm.assessment_id),
                "title": asm.assessment_title,
                "status": asm.assessment_status.value,
                "total_attempts": len(asm.attempts or []),
                "completed_evaluations": len(completed),
                "average_percentage": avg_p,
                "pass_rate_percentage": pass_rate,
                "created_at": asm.assessment_created_at.isoformat()
            })

        completed_all = [r for r in all_results if r.result_status == ResultStatus.COMPLETED]
        pending_all = [r for r in all_results if r.result_status == ResultStatus.PENDING_MANUAL_GRADING or r.result_pending_count > 0]
        all_pcts = [float(r.result_percentage) for r in completed_all]

        subject_avg = round(sum(all_pcts) / len(all_pcts), 2) if all_pcts else None
        total_passed = sum(1 for r in completed_all if r.result_passed is True)
        overall_pass_rate = round((total_passed / len(completed_all)) * 100, 2) if completed_all else None

        # Question difficulty distribution summary
        diff_resp = await self.get_subject_question_difficulty_analytics(org_id, subject_id, requesting_user_id, is_org_admin)
        diff_summary = {
            "easier_count": diff_resp.easier_count,
            "moderate_count": diff_resp.moderate_count,
            "harder_count": diff_resp.harder_count,
            "insufficient_sample_count": diff_resp.insufficient_sample_count
        }

        return SubjectLearningAnalyticsResponse(
            subject_id=subject_id,
            subject_name=subject.subject_name,
            total_assessments=len(assessments),
            total_students_enrolled=enrolled_students,
            total_students_attempted=len(attempted_students),
            average_subject_percentage=subject_avg,
            pass_rate_percentage=overall_pass_rate,
            total_evaluations_completed=len(completed_all),
            total_pending_manual_grading=len(pending_all),
            assessment_trends=assessment_trends,
            question_difficulty_summary=diff_summary
        )

    async def get_subject_question_difficulty_analytics(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> SubjectQuestionDifficultyResponse:
        """
        Calculate descriptive observed difficulty for all questions in a subject.
        Reuses historical snapshots and evaluates accuracy across student attempts.
        """
        subject, workspace = await self._verify_subject_hierarchy(subject_id, org_id, allow_archived_parent=True)
        await self._verify_teacher_or_admin(requesting_user_id, org_id, subject_id, workspace.workspace_id, is_org_admin)

        result_questions = await self.repo.get_subject_result_questions_for_difficulty_analytics(subject_id)
        assessment_questions = await self.repo.get_subject_assessment_questions(subject_id)

        # Map assessment questions by ID
        aq_map: Dict[uuid.UUID, AssessmentQuestion] = {aq.assessment_question_id: aq for aq in assessment_questions}

        # Aggregate metrics per question
        # Group by assessment_question_id (and link to source_question_id if present)
        grouped_stats: Dict[uuid.UUID, Dict[str, Any]] = {}

        for aq_id, aq in aq_map.items():
            snap = aq.assessment_question_snapshot or {}
            grouped_stats[aq_id] = {
                "question_id": aq_id,
                "source_question_id": aq.assessment_question_question_id,
                "question_text": snap.get("text") or snap.get("question_text") or "Question",
                "question_type": QuestionType(snap.get("type", "mcq_single")),
                "marks_available": float(aq.assessment_question_marks),
                "evaluated_count": 0,
                "correct_count": 0,
                "incorrect_count": 0,
                "unanswered_count": 0,
                "pending_count": 0,
                "total_marks_awarded": 0.0,
                "assessment_count": 1
            }

        for rq in result_questions:
            aq_id = rq.result_question_assessment_question_id
            if aq_id not in grouped_stats:
                continue

            entry = grouped_stats[aq_id]
            if rq.result_question_grading_status == GradingStatus.GRADED:
                entry["evaluated_count"] += 1
                entry["total_marks_awarded"] += float(rq.result_question_marks_awarded)
                if rq.result_question_correctness == CorrectnessStatus.CORRECT:
                    entry["correct_count"] += 1
                elif rq.result_question_correctness == CorrectnessStatus.INCORRECT:
                    entry["incorrect_count"] += 1
                elif rq.result_question_correctness == CorrectnessStatus.UNANSWERED:
                    entry["unanswered_count"] += 1
            elif rq.result_question_grading_status == GradingStatus.PENDING:
                entry["pending_count"] += 1

        question_items: List[QuestionDifficultyAnalyticsItem] = []
        easier_count = 0
        moderate_count = 0
        harder_count = 0
        insufficient_count = 0

        for aq_id, data in grouped_stats.items():
            eval_cnt = data["evaluated_count"]
            qtype = data["question_type"]
            marks_avail = data["marks_available"]

            avg_marks = round(data["total_marks_awarded"] / eval_cnt, 2) if eval_cnt > 0 else None

            if qtype == QuestionType.SHORT_ANSWER:
                acc_pct = round((avg_marks / marks_avail) * 100, 2) if avg_marks is not None and marks_avail > 0 else None
            else:
                acc_pct = round((data["correct_count"] / eval_cnt) * 100, 2) if eval_cnt > 0 else None

            band, label, is_insufficient = self.classify_observed_difficulty(acc_pct, eval_cnt)

            if is_insufficient:
                insufficient_count += 1
            elif band == ObservedDifficultyBand.EASIER_OBSERVED:
                easier_count += 1
            elif band == ObservedDifficultyBand.MODERATE_OBSERVED:
                moderate_count += 1
            elif band == ObservedDifficultyBand.HARDER_OBSERVED:
                harder_count += 1

            question_items.append(
                QuestionDifficultyAnalyticsItem(
                    question_id=data["question_id"],
                    source_question_id=data["source_question_id"],
                    question_text=data["question_text"],
                    question_type=data["question_type"],
                    marks_available=marks_avail,
                    evaluated_count=eval_cnt,
                    correct_count=data["correct_count"],
                    incorrect_count=data["incorrect_count"],
                    unanswered_count=data["unanswered_count"],
                    pending_count=data["pending_count"],
                    average_marks_awarded=avg_marks,
                    accuracy_percentage=acc_pct,
                    difficulty_band=band,
                    difficulty_label=label,
                    is_insufficient_sample=is_insufficient,
                    assessment_count=data["assessment_count"]
                )
            )

        # Sort by accuracy ascending (hardest first) with insufficient sample items at the end
        question_items.sort(
            key=lambda item: (
                1 if item.is_insufficient_sample else 0,
                item.accuracy_percentage if item.accuracy_percentage is not None else 999.0
            )
        )

        return SubjectQuestionDifficultyResponse(
            subject_id=subject_id,
            subject_name=subject.subject_name,
            total_questions_analyzed=len(question_items),
            easier_count=easier_count,
            moderate_count=moderate_count,
            harder_count=harder_count,
            insufficient_sample_count=insufficient_count,
            questions=question_items
        )

    # ── Step 10.13: Leaderboard & Class Performance Dashboard ────────────

    async def get_assessment_leaderboard(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        page: int = 1,
        page_size: int = 20
    ) -> AssessmentLeaderboardResponse:
        """
        Retrieve server-authoritative leaderboard rankings for an assessment.
        Applies deterministic competition ranking ("1-2-2-4") using best completed results.
        Enforces student privacy sanitization.
        """
        assessment, subject, workspace = await self._verify_assessment_hierarchy(
            assessment_id,
            org_id,
            allow_archived_parent=True
        )
        await self._verify_workspace_access(requesting_user_id, workspace.workspace_id, is_org_admin)

        is_teacher_or_admin = is_org_admin or (await self.repo.is_user_subject_teacher(requesting_user_id, subject.subject_id))

        # If leaderboard is disabled and requester is a student, return empty disabled response
        if not assessment.assessment_leaderboard_enabled and not is_teacher_or_admin:
            return AssessmentLeaderboardResponse(
                assessment_id=assessment.assessment_id,
                assessment_title=assessment.assessment_title,
                leaderboard_enabled=False,
                total_ranked_students=0,
                my_rank=None,
                my_entry=None,
                entries=[],
                page=page,
                page_size=page_size,
                total_pages=1
            )

        # 1. Fetch completed results and attempts count for this assessment
        completed_results = await self.repo.get_assessment_completed_results_for_leaderboard(assessment_id)
        attempt_counts = await self.repo.get_student_attempts_count_for_assessment(assessment_id)

        def get_result_completion_time(r: AssessmentResult) -> datetime:
            return r.result_graded_at or (r.attempt.attempt_submitted_at if r.attempt else None) or r.result_created_at or datetime.min.replace(tzinfo=timezone.utc)

        # 2. Multiple Attempts Rule: Select student's BEST COMPLETED RESULT
        # Comparison order: Higher percentage > Higher obtained marks > Earlier completed_at
        student_best_results: Dict[uuid.UUID, AssessmentResult] = {}
        for res in completed_results:
            sid = res.result_student_id
            if sid not in student_best_results:
                student_best_results[sid] = res
            else:
                curr = student_best_results[sid]
                curr_pct = float(curr.result_percentage or 0)
                res_pct = float(res.result_percentage or 0)
                if res_pct > curr_pct:
                    student_best_results[sid] = res
                elif res_pct == curr_pct:
                    curr_marks = float(curr.result_obtained_marks or 0)
                    res_marks = float(res.result_obtained_marks or 0)
                    if res_marks > curr_marks:
                        student_best_results[sid] = res
                    elif res_marks == curr_marks:
                        curr_time = get_result_completion_time(curr)
                        res_time = get_result_completion_time(res)
                        if res_time < curr_time:
                            student_best_results[sid] = res

        # 3. Deterministic Sorting:
        # - percentage DESC
        # - obtained_marks DESC
        # - completion_time ASC
        # - student_id ASC (absolute secondary deterministic fallback)
        sorted_items = sorted(
            student_best_results.values(),
            key=lambda r: (
                -float(r.result_percentage or 0),
                -float(r.result_obtained_marks or 0),
                get_result_completion_time(r),
                str(r.result_student_id)
            )
        )

        # 4. Standard Competition Ranking (1-2-2-4):
        ranked_entries: List[AssessmentLeaderboardEntryResponse] = []
        current_rank = 1
        total_students = len(sorted_items)

        my_rank: Optional[int] = None
        my_entry: Optional[AssessmentLeaderboardEntryResponse] = None

        for idx, res in enumerate(sorted_items):
            if idx > 0:
                prev = sorted_items[idx - 1]
                prev_pct = float(prev.result_percentage or 0)
                curr_pct = float(res.result_percentage or 0)
                prev_marks = float(prev.result_obtained_marks or 0)
                curr_marks = float(res.result_obtained_marks or 0)
                prev_time = get_result_completion_time(prev)
                curr_time = get_result_completion_time(res)

                if prev_pct == curr_pct and prev_marks == curr_marks and prev_time == curr_time:
                    # Same score and completion time -> share identical rank
                    pass
                else:
                    current_rank = idx + 1
            else:
                current_rank = 1

            student_user = res.student
            # Privacy Sanitization: Mask peer names for students to "Jane D."
            display_name = f"{student_user.user_first_name} {student_user.user_last_name}".strip() if student_user else "Student"
            if not is_teacher_or_admin and student_user and student_user.user_id != requesting_user_id:
                if student_user.user_last_name:
                    display_name = f"{student_user.user_first_name} {student_user.user_last_name[0]}."
                else:
                    display_name = f"{student_user.user_first_name}"

            is_current = (res.result_student_id == requesting_user_id)
            entry = AssessmentLeaderboardEntryResponse(
                rank=current_rank,
                student=LeaderboardStudentBrief(
                    id=res.result_student_id,
                    display_name=display_name,
                    profile_image_url=getattr(student_user, "user_profile_image", None) if student_user else None
                ),
                percentage=float(res.result_percentage or 0),
                obtained_marks=float(res.result_obtained_marks or 0),
                total_marks=float(res.result_total_marks or 0),
                attempts_used=attempt_counts.get(res.result_student_id, 1),
                completed_at=get_result_completion_time(res),
                is_current_user=is_current
            )

            ranked_entries.append(entry)

            if is_current:
                my_rank = current_rank
                my_entry = entry

        # Server-side pagination
        page = max(1, page)
        page_size = max(1, min(100, page_size))
        total_pages = max(1, (total_students + page_size - 1) // page_size) if total_students > 0 else 1
        start_idx = (page - 1) * page_size
        paged_entries = ranked_entries[start_idx : start_idx + page_size]

        return AssessmentLeaderboardResponse(
            assessment_id=assessment.assessment_id,
            assessment_title=assessment.assessment_title,
            leaderboard_enabled=assessment.assessment_leaderboard_enabled,
            total_ranked_students=total_students,
            my_rank=my_rank,
            my_entry=my_entry,
            entries=paged_entries,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    async def update_assessment_leaderboard_settings(
        self,
        org_id: uuid.UUID,
        assessment_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool,
        payload: AssessmentLeaderboardSettingsUpdateRequest
    ) -> AssessmentLeaderboardResponse:
        """Update leaderboard enable/disable toggle for an assessment."""
        assessment, subject, workspace = await self._verify_assessment_hierarchy(
            assessment_id,
            org_id,
            allow_archived_parent=False
        )
        await self._verify_teacher_or_admin(
            requesting_user_id,
            org_id,
            subject.subject_id,
            workspace.workspace_id,
            is_org_admin
        )

        await self.repo.update_assessment_leaderboard_setting(
            assessment_id=assessment_id,
            enabled=payload.enabled
        )

        return await self.get_assessment_leaderboard(
            org_id=org_id,
            assessment_id=assessment_id,
            requesting_user_id=requesting_user_id,
            is_org_admin=is_org_admin
        )

    async def get_class_performance_dashboard(
        self,
        org_id: uuid.UUID,
        subject_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        is_org_admin: bool
    ) -> ClassPerformanceDashboardResponse:
        """
        Consolidated Class Performance Dashboard for instructors and admins.
        Aggregates class metrics, timeline trend, assessment grid, student roster, and question difficulty.
        """
        subject, workspace = await self._verify_subject_hierarchy(subject_id, org_id, allow_archived_parent=True)
        await self._verify_teacher_or_admin(requesting_user_id, org_id, subject_id, workspace.workspace_id, is_org_admin)

        # 1. Enrolled students and assessments
        assessments = await self.repo.get_subject_assessments_and_results_for_analytics(subject_id)
        students = await self.repo.get_workspace_students(workspace.workspace_id)
        total_enrolled = len(students)

        # 2. Subject student results
        all_subject_results = await self.repo.get_subject_student_results_and_attempts(subject_id)

        student_results_map: Dict[uuid.UUID, List[AssessmentResult]] = {}
        for r in all_subject_results:
            student_results_map.setdefault(r.result_student_id, []).append(r)

        completed_results = [r for r in all_subject_results if r.result_status == ResultStatus.COMPLETED]
        pending_results = [r for r in all_subject_results if r.result_status == ResultStatus.PENDING_MANUAL_GRADING or (r.result_pending_count or 0) > 0]
        participating_student_ids = set(student_results_map.keys())

        all_completed_pcts = sorted([float(r.result_percentage or 0) for r in completed_results])
        class_avg = round(sum(all_completed_pcts) / len(all_completed_pcts), 2) if all_completed_pcts else None

        if all_completed_pcts:
            n = len(all_completed_pcts)
            if n % 2 == 1:
                class_median = all_completed_pcts[n // 2]
            else:
                class_median = round((all_completed_pcts[n // 2 - 1] + all_completed_pcts[n // 2]) / 2, 2)
        else:
            class_median = None

        total_passed_evals = sum(1 for r in completed_results if r.result_passed is True)
        class_pass_rate = round((total_passed_evals / len(completed_results)) * 100, 2) if completed_results else None
        participation_rate = round((len(participating_student_ids) / total_enrolled) * 100, 2) if total_enrolled > 0 else 0.0

        # 3. Assessment summaries & Chronological Trend
        assessment_summaries: List[Dict[str, Any]] = []
        performance_trend: List[Dict[str, Any]] = []

        for asm in assessments:
            asm_results = asm.results or []
            asm_completed = [r for r in asm_results if r.result_status == ResultStatus.COMPLETED]
            asm_pending = [r for r in asm_results if r.result_status == ResultStatus.PENDING_MANUAL_GRADING or (r.result_pending_count or 0) > 0]
            asm_pcts = sorted([float(r.result_percentage or 0) for r in asm_completed])

            asm_avg = round(sum(asm_pcts) / len(asm_pcts), 2) if asm_pcts else None
            if asm_pcts:
                an = len(asm_pcts)
                asm_median = asm_pcts[an // 2] if an % 2 == 1 else round((asm_pcts[an // 2 - 1] + asm_pcts[an // 2]) / 2, 2)
                asm_highest = max(asm_pcts)
                asm_lowest = min(asm_pcts)
            else:
                asm_median = None
                asm_highest = None
                asm_lowest = None

            asm_passed = sum(1 for r in asm_completed if r.result_passed is True)
            asm_pass_rate = round((asm_passed / len(asm_completed)) * 100, 2) if asm_completed else None
            asm_participants = len(set(r.result_student_id for r in asm_results))

            summary_item = {
                "assessment_id": str(asm.assessment_id),
                "title": asm.assessment_title,
                "status": asm.assessment_status.value,
                "total_attempts": len(asm.attempts or []),
                "participants": asm_participants,
                "completed_evaluations": len(asm_completed),
                "pending_grading": len(asm_pending),
                "average_percentage": asm_avg,
                "median_percentage": asm_median,
                "highest_percentage": asm_highest,
                "lowest_percentage": asm_lowest,
                "pass_rate_percentage": asm_pass_rate,
                "leaderboard_enabled": asm.assessment_leaderboard_enabled,
                "created_at": asm.assessment_created_at.isoformat()
            }
            assessment_summaries.append(summary_item)
            performance_trend.append(summary_item)

        # 4. Student Roster Performance
        student_roster: List[ClassStudentPerformanceItem] = []
        for std in students:
            s_res = student_results_map.get(std.user_id, [])
            s_completed = [r for r in s_res if r.result_status == ResultStatus.COMPLETED]
            s_pending = [r for r in s_res if r.result_status == ResultStatus.PENDING_MANUAL_GRADING or (r.result_pending_count or 0) > 0]
            s_pcts = [float(r.result_percentage or 0) for r in s_completed]

            s_avg = round(sum(s_pcts) / len(s_pcts), 2) if s_pcts else None
            s_best = max(s_pcts) if s_pcts else None
            s_latest = s_pcts[-1] if s_pcts else None
            s_passed = sum(1 for r in s_completed if r.result_passed is True)

            if s_pending:
                status_label = "Pending Review"
            elif not s_completed:
                status_label = "No Submissions"
            elif s_avg is not None and s_avg < 50.0:
                status_label = "Below Passing Threshold"
            else:
                status_label = "Passing"

            student_roster.append(
                ClassStudentPerformanceItem(
                    student_id=std.user_id,
                    student_name=f"{std.user_first_name} {std.user_last_name}".strip(),
                    student_email=std.user_email,
                    assessments_completed=len(s_completed),
                    average_percentage=s_avg,
                    latest_percentage=s_latest,
                    best_percentage=s_best,
                    passed_count=s_passed,
                    pending_grading_count=len(s_pending),
                    status_label=status_label
                )
            )

        # 5. Question Difficulty Summary (Reused from Step 10.12)
        diff_resp = await self.get_subject_question_difficulty_analytics(org_id, subject_id, requesting_user_id, is_org_admin)
        diff_summary = {
            "easier_count": diff_resp.easier_count,
            "moderate_count": diff_resp.moderate_count,
            "harder_count": diff_resp.harder_count,
            "insufficient_sample_count": diff_resp.insufficient_sample_count
        }

        return ClassPerformanceDashboardResponse(
            subject_id=subject.subject_id,
            subject_name=subject.subject_name,
            workspace_id=workspace.workspace_id,
            workspace_name=workspace.workspace_name,
            total_students=total_enrolled,
            participating_students=len(participating_student_ids),
            participation_rate_percentage=participation_rate,
            total_assessments=len(assessments),
            completed_evaluations=len(completed_results),
            class_average_percentage=class_avg,
            class_median_percentage=class_median,
            class_pass_rate_percentage=class_pass_rate,
            total_pending_manual_grading=len(pending_results),
            performance_trend=performance_trend,
            assessment_summaries=assessment_summaries,
            student_roster=student_roster,
            question_difficulty_summary=diff_summary
        )




