import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, exists

from app.modules.assessments.models import (
    Assessment,
    AssessmentType,
    AssessmentStatus,
    QuestionBankItem,
    AssessmentQuestion,
    QuestionOption,
    QuestionType,
    QuestionStatus
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
    StudentQuestionOptionResponse
)
from app.modules.assessments.repository import AssessmentRepository
from app.modules.subjects.models import Subject, SubjectTeacher, SubjectStatus
from app.modules.organizations.models import Workspace, WorkspaceStatus
from app.core.exceptions import (
    NotFoundException,
    ForbiddenException,
    ConflictException,
    ValidationException
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
            randomize_questions=payload.randomize_questions
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
