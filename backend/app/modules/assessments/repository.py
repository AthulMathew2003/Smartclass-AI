import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy import select, delete, and_, or_, exists, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
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
from app.modules.subjects.models import Subject, SubjectTeacher, SubjectStatus
from app.modules.organizations.models import (
    Workspace,
    WorkspaceMember,
    WorkspaceStatus,
    OrganizationMember,
    OrganizationMemberStatus,
    Role
)
from app.modules.users.models import User


class AssessmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Assessment CRUD ─────────────────────────────────────────

    async def create_assessment(
        self,
        subject_id: uuid.UUID,
        title: str,
        description: Optional[str],
        type: AssessmentType,
        status: AssessmentStatus,
        duration_minutes: Optional[int],
        start_at: Optional[datetime],
        end_at: Optional[datetime],
        total_marks: Decimal,
        passing_marks: Optional[Decimal],
        attempt_limit: int,
        randomize_questions: bool,
        leaderboard_enabled: bool = False,
        created_by: Optional[uuid.UUID] = None
    ) -> Assessment:
        assessment = Assessment(
            assessment_subject_id=subject_id,
            assessment_title=title,
            assessment_description=description,
            assessment_type=type,
            assessment_status=status,
            assessment_duration_minutes=duration_minutes,
            assessment_start_at=start_at,
            assessment_end_at=end_at,
            assessment_total_marks=total_marks,
            assessment_passing_marks=passing_marks,
            assessment_attempt_limit=attempt_limit,
            assessment_randomize_questions=randomize_questions,
            assessment_leaderboard_enabled=leaderboard_enabled,
            assessment_created_by=created_by
        )
        self.db.add(assessment)
        try:
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            raise e
        return assessment

    async def get_assessment_by_id(self, assessment_id: uuid.UUID) -> Optional[Assessment]:
        stmt = (
            select(Assessment)
            .where(Assessment.assessment_id == assessment_id)
            .options(
                selectinload(Assessment.subject).selectinload(Subject.workspace),
                selectinload(Assessment.creator),
                selectinload(Assessment.assessment_questions)
            )
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_assessments_by_subject(
        self,
        subject_id: uuid.UUID,
        status_filter: Optional[AssessmentStatus] = None,
        include_drafts: bool = False,
        include_archived: bool = False,
        search: Optional[str] = None
    ) -> List[Assessment]:
        stmt = (
            select(Assessment)
            .where(Assessment.assessment_subject_id == subject_id)
            .options(
                selectinload(Assessment.subject).selectinload(Subject.workspace),
                selectinload(Assessment.creator),
                selectinload(Assessment.assessment_questions)
            )
        )

        if status_filter is not None:
            if status_filter == AssessmentStatus.DRAFT and not include_drafts:
                return []
            if status_filter == AssessmentStatus.ARCHIVED and not include_archived:
                return []
            stmt = stmt.where(Assessment.assessment_status == status_filter)
        else:
            if not include_drafts:
                stmt = stmt.where(Assessment.assessment_status != AssessmentStatus.DRAFT)
            if not include_archived:
                stmt = stmt.where(Assessment.assessment_status != AssessmentStatus.ARCHIVED)

        if search:
            search_pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Assessment.assessment_title.ilike(search_pattern),
                    Assessment.assessment_description.ilike(search_pattern)
                )
            )

        stmt = stmt.order_by(Assessment.assessment_created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_global_assessments_for_teacher_or_admin(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        is_org_admin: bool,
        workspace_id: Optional[uuid.UUID] = None,
        status_filter: Optional[AssessmentStatus] = None,
        search: Optional[str] = None
    ) -> List[Assessment]:
        stmt = (
            select(Assessment)
            .join(Subject, Assessment.assessment_subject_id == Subject.subject_id)
            .join(Workspace, Subject.subject_workspace_id == Workspace.workspace_id)
            .options(
                selectinload(Assessment.subject).selectinload(Subject.workspace),
                selectinload(Assessment.creator),
                selectinload(Assessment.assessment_questions)
            )
            .where(Workspace.workspace_organization_id == org_id)
        )

        if not is_org_admin:
            stmt = stmt.where(
                exists().where(
                    and_(
                        SubjectTeacher.subject_teacher_subject_id == Subject.subject_id,
                        SubjectTeacher.subject_teacher_user_id == user_id
                    )
                )
            )

        if workspace_id:
            stmt = stmt.where(Workspace.workspace_id == workspace_id)

        if status_filter is not None:
            stmt = stmt.where(Assessment.assessment_status == status_filter)
        else:
            stmt = stmt.where(Assessment.assessment_status != AssessmentStatus.ARCHIVED)

        if search:
            search_pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Assessment.assessment_title.ilike(search_pattern),
                    Assessment.assessment_description.ilike(search_pattern),
                    Subject.subject_name.ilike(search_pattern)
                )
            )

        stmt = stmt.order_by(Assessment.assessment_created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_global_assessments_for_teacher(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        is_org_admin: bool,
        workspace_id: Optional[uuid.UUID] = None,
        status_filter: Optional[AssessmentStatus] = None,
        search: Optional[str] = None
    ) -> List[Assessment]:
        return await self.list_global_assessments_for_teacher_or_admin(
            org_id=org_id,
            user_id=user_id,
            is_org_admin=is_org_admin,
            workspace_id=workspace_id,
            status_filter=status_filter,
            search=search
        )

    async def list_global_assessments_for_student(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        workspace_id: Optional[uuid.UUID] = None,
        status_filter: Optional[AssessmentStatus] = None,
        search: Optional[str] = None
    ) -> List[Assessment]:
        stmt = (
            select(Assessment)
            .join(Subject, Assessment.assessment_subject_id == Subject.subject_id)
            .join(Workspace, Subject.subject_workspace_id == Workspace.workspace_id)
            .join(WorkspaceMember, Workspace.workspace_id == WorkspaceMember.workspace_member_workspace_id)
            .options(
                selectinload(Assessment.subject).selectinload(Subject.workspace),
                selectinload(Assessment.creator),
                selectinload(Assessment.assessment_questions)
            )
            .where(
                Workspace.workspace_organization_id == org_id,
                WorkspaceMember.workspace_member_user_id == user_id,
                Subject.subject_status == SubjectStatus.ACTIVE,
                Workspace.workspace_status == WorkspaceStatus.ACTIVE
            )
        )

        allowed_statuses = [AssessmentStatus.PUBLISHED, AssessmentStatus.ACTIVE, AssessmentStatus.CLOSED]
        if status_filter is not None:
            if status_filter in allowed_statuses:
                stmt = stmt.where(Assessment.assessment_status == status_filter)
            else:
                return []
        else:
            stmt = stmt.where(Assessment.assessment_status.in_(allowed_statuses))

        if workspace_id:
            stmt = stmt.where(Workspace.workspace_id == workspace_id)

        if search:
            search_pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Assessment.assessment_title.ilike(search_pattern),
                    Assessment.assessment_description.ilike(search_pattern),
                    Subject.subject_name.ilike(search_pattern)
                )
            )

        stmt = stmt.order_by(Assessment.assessment_created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_assessment(
        self,
        assessment: Assessment,
        title: Optional[str] = None,
        description: Optional[str] = None,
        type: Optional[AssessmentType] = None,
        status: Optional[AssessmentStatus] = None,
        duration_minutes: Optional[int] = None,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None,
        total_marks: Optional[Decimal] = None,
        passing_marks: Optional[Decimal] = None,
        attempt_limit: Optional[int] = None,
        randomize_questions: Optional[bool] = None,
        leaderboard_enabled: Optional[bool] = None
    ) -> Assessment:
        if title is not None:
            assessment.assessment_title = title
        if description is not None:
            assessment.assessment_description = description
        if type is not None:
            assessment.assessment_type = type
        if status is not None:
            assessment.assessment_status = status
        if duration_minutes is not None:
            assessment.assessment_duration_minutes = duration_minutes
        if start_at is not None:
            assessment.assessment_start_at = start_at
        if end_at is not None:
            assessment.assessment_end_at = end_at
        if total_marks is not None:
            assessment.assessment_total_marks = total_marks
        if passing_marks is not None:
            assessment.assessment_passing_marks = passing_marks
        if attempt_limit is not None:
            assessment.assessment_attempt_limit = attempt_limit
        if randomize_questions is not None:
            assessment.assessment_randomize_questions = randomize_questions
        if leaderboard_enabled is not None:
            assessment.assessment_leaderboard_enabled = leaderboard_enabled

        try:
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            raise e
        return assessment

    async def set_assessment_status(
        self,
        assessment: Assessment,
        new_status: AssessmentStatus
    ) -> Assessment:
        assessment.assessment_status = new_status
        try:
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            raise e
        return assessment

    async def archive_assessment(self, assessment: Assessment) -> Assessment:
        return await self.set_assessment_status(assessment, AssessmentStatus.ARCHIVED)

    async def delete_assessment(self, assessment: Assessment) -> None:
        await self.db.delete(assessment)
        await self.db.flush()

    # ── Subject Question Bank CRUD ──────────────────────────────

    async def create_question_bank_item(
        self,
        subject_id: uuid.UUID,
        question_type: QuestionType,
        question_text: str,
        default_marks: Decimal,
        question_explanation: Optional[str],
        created_by: Optional[uuid.UUID],
        options_data: Optional[List[dict]] = None
    ) -> QuestionBankItem:
        question = QuestionBankItem(
            question_subject_id=subject_id,
            question_type=question_type,
            question_text=question_text,
            question_default_marks=default_marks,
            question_explanation=question_explanation,
            question_status=QuestionStatus.ACTIVE,
            question_created_by=created_by
        )
        self.db.add(question)
        await self.db.flush()

        if options_data:
            for opt in options_data:
                option = QuestionOption(
                    option_question_id=question.question_id,
                    option_text=opt["option_text"],
                    option_order=opt["option_order"],
                    option_is_correct=opt.get("option_is_correct", False)
                )
                self.db.add(option)
            await self.db.flush()

        return await self.get_question_bank_item_by_id(question.question_id)

    async def get_question_bank_item_by_id(self, question_id: uuid.UUID) -> Optional[QuestionBankItem]:
        stmt = (
            select(QuestionBankItem)
            .where(QuestionBankItem.question_id == question_id)
            .options(
                selectinload(QuestionBankItem.options),
                selectinload(QuestionBankItem.creator),
                selectinload(QuestionBankItem.subject).selectinload(Subject.workspace)
            )
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_questions_by_subject(
        self,
        subject_id: uuid.UUID,
        question_type: Optional[QuestionType] = None,
        search: Optional[str] = None,
        include_archived: bool = False
    ) -> List[QuestionBankItem]:
        stmt = (
            select(QuestionBankItem)
            .where(QuestionBankItem.question_subject_id == subject_id)
            .options(
                selectinload(QuestionBankItem.options),
                selectinload(QuestionBankItem.creator)
            )
        )
        if not include_archived:
            stmt = stmt.where(QuestionBankItem.question_status != QuestionStatus.ARCHIVED)

        if question_type is not None:
            stmt = stmt.where(QuestionBankItem.question_type == question_type)

        if search:
            search_pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    QuestionBankItem.question_text.ilike(search_pattern),
                    QuestionBankItem.question_explanation.ilike(search_pattern)
                )
            )

        stmt = stmt.order_by(QuestionBankItem.question_created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_question_bank_item(
        self,
        question: QuestionBankItem,
        question_text: Optional[str] = None,
        default_marks: Optional[Decimal] = None,
        question_explanation: Optional[str] = None,
        question_type: Optional[QuestionType] = None,
        options_data: Optional[List[dict]] = None
    ) -> QuestionBankItem:
        if question_text is not None:
            question.question_text = question_text
        if default_marks is not None:
            question.question_default_marks = default_marks
        if question_explanation is not None:
            question.question_explanation = question_explanation
        if question_type is not None:
            question.question_type = question_type

        if options_data is not None:
            await self.db.execute(
                delete(QuestionOption).where(QuestionOption.option_question_id == question.question_id)
            )
            await self.db.flush()

            for opt in options_data:
                new_opt = QuestionOption(
                    option_question_id=question.question_id,
                    option_text=opt["option_text"],
                    option_order=opt["option_order"],
                    option_is_correct=opt.get("option_is_correct", False)
                )
                self.db.add(new_opt)
            await self.db.flush()

        await self.db.flush()
        return await self.get_question_bank_item_by_id(question.question_id)

    async def archive_question_bank_item(self, question: QuestionBankItem) -> QuestionBankItem:
        question.question_status = QuestionStatus.ARCHIVED
        await self.db.flush()
        return question

    async def delete_question_bank_item(self, question: QuestionBankItem) -> None:
        await self.db.delete(question)
        await self.db.flush()

    # ── Assessment Questions & Snapshot Operations ─────────────

    async def create_assessment_question(
        self,
        assessment_id: uuid.UUID,
        question_id: Optional[uuid.UUID],
        order: int,
        marks: Decimal,
        snapshot: dict
    ) -> AssessmentQuestion:
        aq = AssessmentQuestion(
            assessment_question_assessment_id=assessment_id,
            assessment_question_question_id=question_id,
            assessment_question_order=order,
            assessment_question_marks=marks,
            assessment_question_snapshot=snapshot
        )
        self.db.add(aq)
        try:
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            raise e
        return aq

    async def get_assessment_question_by_id(self, assessment_question_id: uuid.UUID) -> Optional[AssessmentQuestion]:
        stmt = (
            select(AssessmentQuestion)
            .where(AssessmentQuestion.assessment_question_id == assessment_question_id)
            .options(
                selectinload(AssessmentQuestion.assessment),
                selectinload(AssessmentQuestion.source_question)
            )
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_assessment_questions(self, assessment_id: uuid.UUID) -> List[AssessmentQuestion]:
        stmt = (
            select(AssessmentQuestion)
            .where(AssessmentQuestion.assessment_question_assessment_id == assessment_id)
            .order_by(AssessmentQuestion.assessment_question_order.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_max_assessment_question_order(self, assessment_id: uuid.UUID) -> int:
        stmt = select(func.max(AssessmentQuestion.assessment_question_order)).where(
            AssessmentQuestion.assessment_question_assessment_id == assessment_id
        )
        result = await self.db.execute(stmt)
        max_order = result.scalar()
        return max_order if max_order is not None else 0

    async def exists_question_in_assessment(self, assessment_id: uuid.UUID, question_id: uuid.UUID) -> bool:
        stmt = select(exists().where(
            and_(
                AssessmentQuestion.assessment_question_assessment_id == assessment_id,
                AssessmentQuestion.assessment_question_question_id == question_id
            )
        ))
        result = await self.db.execute(stmt)
        return bool(result.scalar())

    async def update_assessment_question(
        self,
        assessment_question: AssessmentQuestion,
        marks: Optional[Decimal] = None,
        order: Optional[int] = None
    ) -> AssessmentQuestion:
        if marks is not None:
            assessment_question.assessment_question_marks = marks
            # Update snapshot marks if present
            if isinstance(assessment_question.assessment_question_snapshot, dict):
                snapshot = dict(assessment_question.assessment_question_snapshot)
                snapshot["question_marks"] = float(marks)
                assessment_question.assessment_question_snapshot = snapshot
        if order is not None:
            assessment_question.assessment_question_order = order

        try:
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            raise e
        return assessment_question

    async def delete_assessment_question(self, assessment_question: AssessmentQuestion) -> None:
        await self.db.delete(assessment_question)
        await self.db.flush()

    async def reorder_assessment_questions(
        self,
        assessment_id: uuid.UUID,
        ordered_assessment_question_ids: List[uuid.UUID]
    ) -> None:
        """
        Atomically updates assessment question order for the specified IDs.
        Uses two-phase update (-order then order) to satisfy unique constraint.
        """
        # Phase 1: Set temporary negative order values
        for idx, aqid in enumerate(ordered_assessment_question_ids):
            temp_order = - (idx + 1)
            stmt = select(AssessmentQuestion).where(
                AssessmentQuestion.assessment_question_id == aqid,
                AssessmentQuestion.assessment_question_assessment_id == assessment_id
            )
            aq = (await self.db.execute(stmt)).scalar_one_or_none()
            if aq:
                aq.assessment_question_order = temp_order
        await self.db.flush()

        # Phase 2: Set final positive 1-based order values
        for idx, aqid in enumerate(ordered_assessment_question_ids):
            final_order = idx + 1
            stmt = select(AssessmentQuestion).where(
                AssessmentQuestion.assessment_question_id == aqid,
                AssessmentQuestion.assessment_question_assessment_id == assessment_id
            )
            aq = (await self.db.execute(stmt)).scalar_one_or_none()
            if aq:
                aq.assessment_question_order = final_order
        await self.db.flush()

    async def recalculate_assessment_total_marks(self, assessment_id: uuid.UUID) -> Decimal:
        """Calculates total marks server-side from assessment questions sum and persists on assessment."""
        stmt = select(func.coalesce(func.sum(AssessmentQuestion.assessment_question_marks), Decimal("0.00"))).where(
            AssessmentQuestion.assessment_question_assessment_id == assessment_id
        )
        result = await self.db.execute(stmt)
        total = Decimal(str(result.scalar() or "0.00"))

        stmt_a = select(Assessment).where(Assessment.assessment_id == assessment_id)
        assessment = (await self.db.execute(stmt_a)).scalar_one_or_none()
        if assessment:
            assessment.assessment_total_marks = total
            await self.db.flush()
        return total

    # ── Hierarchy and Permission Queries ────────────────────────

    async def is_user_subject_teacher(self, user_id: uuid.UUID, subject_id: uuid.UUID) -> bool:
        stmt = select(exists().where(
            and_(
                SubjectTeacher.subject_teacher_subject_id == subject_id,
                SubjectTeacher.subject_teacher_user_id == user_id
            )
        ))
        result = await self.db.execute(stmt)
        return bool(result.scalar())

    async def is_user_workspace_member(self, user_id: uuid.UUID, workspace_id: uuid.UUID) -> bool:
        stmt = select(exists().where(
            and_(
                WorkspaceMember.workspace_member_workspace_id == workspace_id,
                WorkspaceMember.workspace_member_user_id == user_id
            )
        ))
        result = await self.db.execute(stmt)
        return bool(result.scalar())

    async def is_user_org_admin(self, user_id: uuid.UUID, org_id: uuid.UUID) -> bool:
        stmt = (
            select(OrganizationMember)
            .join(Role, OrganizationMember.organization_member_role_id == Role.role_id)
            .where(
                OrganizationMember.organization_member_organization_id == org_id,
                OrganizationMember.organization_member_user_id == user_id,
                OrganizationMember.organization_member_status == OrganizationMemberStatus.ACTIVE,
                Role.role_name.in_(["Owner", "Admin"])
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first() is not None

    async def is_user_any_subject_teacher(self, org_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        stmt = select(exists().where(
            and_(
                SubjectTeacher.subject_teacher_user_id == user_id,
                SubjectTeacher.subject_teacher_subject_id == Subject.subject_id,
                Subject.subject_workspace_id == Workspace.workspace_id,
                Workspace.workspace_organization_id == org_id
            )
        ))
        result = await self.db.execute(stmt)
        return bool(result.scalar())

    async def is_user_teacher_or_admin_role(self, org_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        stmt = (
            select(OrganizationMember)
            .join(Role, OrganizationMember.organization_member_role_id == Role.role_id)
            .where(
                OrganizationMember.organization_member_organization_id == org_id,
                OrganizationMember.organization_member_user_id == user_id,
                OrganizationMember.organization_member_status == OrganizationMemberStatus.ACTIVE,
                Role.role_name.in_(["Owner", "Admin", "Teacher"])
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first() is not None

    # ── Attempt CRUD & Taking Flow ──────────────────────────────

    async def create_assessment_attempt(
        self,
        assessment_id: uuid.UUID,
        student_id: uuid.UUID,
        attempt_number: int,
        question_order: List[str],
        expires_at: Optional[datetime] = None
    ) -> AssessmentAttempt:
        attempt = AssessmentAttempt(
            attempt_assessment_id=assessment_id,
            attempt_student_id=student_id,
            attempt_number=attempt_number,
            attempt_status=AttemptStatus.IN_PROGRESS,
            attempt_question_order=question_order,
            attempt_expires_at=expires_at
        )
        attempt.answers = []
        self.db.add(attempt)
        try:
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            raise e
        return attempt

    async def get_student_in_progress_attempt(
        self,
        assessment_id: uuid.UUID,
        student_id: uuid.UUID
    ) -> Optional[AssessmentAttempt]:
        stmt = (
            select(AssessmentAttempt)
            .where(
                and_(
                    AssessmentAttempt.attempt_assessment_id == assessment_id,
                    AssessmentAttempt.attempt_student_id == student_id,
                    AssessmentAttempt.attempt_status == AttemptStatus.IN_PROGRESS
                )
            )
            .options(
                selectinload(AssessmentAttempt.answers),
                selectinload(AssessmentAttempt.assessment).selectinload(Assessment.assessment_questions)
            )
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def count_student_attempts(
        self,
        assessment_id: uuid.UUID,
        student_id: uuid.UUID
    ) -> int:
        stmt = (
            select(func.count(AssessmentAttempt.attempt_id))
            .where(
                and_(
                    AssessmentAttempt.attempt_assessment_id == assessment_id,
                    AssessmentAttempt.attempt_student_id == student_id
                )
            )
        )
        result = await self.db.execute(stmt)
        return int(result.scalar() or 0)

    async def get_attempt_by_id(
        self,
        attempt_id: uuid.UUID
    ) -> Optional[AssessmentAttempt]:
        stmt = (
            select(AssessmentAttempt)
            .where(AssessmentAttempt.attempt_id == attempt_id)
            .options(
                selectinload(AssessmentAttempt.answers),
                selectinload(AssessmentAttempt.assessment).selectinload(Assessment.assessment_questions),
                selectinload(AssessmentAttempt.assessment).selectinload(Assessment.subject).selectinload(Subject.workspace),
                selectinload(AssessmentAttempt.student)
            )
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_student_attempts(
        self,
        assessment_id: uuid.UUID,
        student_id: uuid.UUID
    ) -> List[AssessmentAttempt]:
        stmt = (
            select(AssessmentAttempt)
            .where(
                and_(
                    AssessmentAttempt.attempt_assessment_id == assessment_id,
                    AssessmentAttempt.attempt_student_id == student_id
                )
            )
            .options(
                selectinload(AssessmentAttempt.answers)
            )
            .order_by(AssessmentAttempt.attempt_number.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_attempt_answer(
        self,
        attempt_id: uuid.UUID,
        question_id: uuid.UUID
    ) -> Optional[AssessmentAttemptAnswer]:
        stmt = (
            select(AssessmentAttemptAnswer)
            .where(
                and_(
                    AssessmentAttemptAnswer.attempt_answer_attempt_id == attempt_id,
                    AssessmentAttemptAnswer.attempt_answer_question_id == question_id
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_attempt_answer(
        self,
        attempt_id: uuid.UUID,
        question_id: uuid.UUID,
        answer_value: dict
    ) -> AssessmentAttemptAnswer:
        existing = await self.get_attempt_answer(attempt_id, question_id)
        if existing:
            existing.attempt_answer_value = answer_value
            existing.attempt_answer_updated_at = datetime.now(timezone.utc)
            await self.db.flush()
            return existing
        else:
            answer = AssessmentAttemptAnswer(
                attempt_answer_attempt_id=attempt_id,
                attempt_answer_question_id=question_id,
                attempt_answer_value=answer_value
            )
            self.db.add(answer)
            try:
                await self.db.flush()
            except IntegrityError as e:
                await self.db.rollback()
                raise e
            return answer

    async def submit_attempt(
        self,
        attempt: AssessmentAttempt
    ) -> AssessmentAttempt:
        attempt.attempt_status = AttemptStatus.SUBMITTED
        attempt.attempt_submitted_at = datetime.now(timezone.utc)
        await self.db.flush()
        refreshed = await self.get_attempt_by_id(attempt.attempt_id)
        return refreshed or attempt

    async def expire_attempt(
        self,
        attempt: AssessmentAttempt
    ) -> AssessmentAttempt:
        """Idempotently transition an in-progress attempt to EXPIRED status."""
        if attempt.attempt_status != AttemptStatus.EXPIRED:
            attempt.attempt_status = AttemptStatus.EXPIRED
            attempt.attempt_submitted_at = datetime.now(timezone.utc)
            await self.db.flush()
        refreshed = await self.get_attempt_by_id(attempt.attempt_id)
        return refreshed or attempt

    # ── Assessment Evaluation & Result CRUD ─────────────────────

    async def get_result_by_attempt_id(
        self,
        attempt_id: uuid.UUID
    ) -> Optional[AssessmentResult]:
        stmt = (
            select(AssessmentResult)
            .where(AssessmentResult.result_attempt_id == attempt_id)
            .options(
                selectinload(AssessmentResult.question_results).selectinload(AssessmentResultQuestion.assessment_question),
                selectinload(AssessmentResult.attempt),
                selectinload(AssessmentResult.assessment),
                selectinload(AssessmentResult.student)
            )
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_result_by_id(
        self,
        result_id: uuid.UUID
    ) -> Optional[AssessmentResult]:
        stmt = (
            select(AssessmentResult)
            .where(AssessmentResult.result_id == result_id)
            .options(
                selectinload(AssessmentResult.question_results).selectinload(AssessmentResultQuestion.assessment_question),
                selectinload(AssessmentResult.attempt),
                selectinload(AssessmentResult.assessment),
                selectinload(AssessmentResult.student)
            )
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_assessment_result(
        self,
        attempt_id: uuid.UUID,
        assessment_id: uuid.UUID,
        student_id: uuid.UUID,
        total_marks: Decimal,
        obtained_marks: Decimal,
        percentage: Decimal,
        passed: Optional[bool],
        status: ResultStatus,
        correct_count: int,
        incorrect_count: int,
        unanswered_count: int,
        pending_count: int,
        graded_at: Optional[datetime]
    ) -> AssessmentResult:
        result = AssessmentResult(
            result_attempt_id=attempt_id,
            result_assessment_id=assessment_id,
            result_student_id=student_id,
            result_total_marks=total_marks,
            result_obtained_marks=obtained_marks,
            result_percentage=percentage,
            result_passed=passed,
            result_status=status,
            result_correct_count=correct_count,
            result_incorrect_count=incorrect_count,
            result_unanswered_count=unanswered_count,
            result_pending_count=pending_count,
            result_graded_at=graded_at
        )
        self.db.add(result)
        try:
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            raise e
        return result

    async def create_result_question(
        self,
        result_id: uuid.UUID,
        assessment_question_id: uuid.UUID,
        answer_value: Optional[dict],
        marks_available: Decimal,
        marks_awarded: Decimal,
        correctness: CorrectnessStatus,
        grading_status: GradingStatus,
        feedback: Optional[str] = None,
        graded_by: Optional[uuid.UUID] = None,
        graded_at: Optional[datetime] = None
    ) -> AssessmentResultQuestion:
        rq = AssessmentResultQuestion(
            result_question_result_id=result_id,
            result_question_assessment_question_id=assessment_question_id,
            result_question_answer_value=answer_value,
            result_question_marks_available=marks_available,
            result_question_marks_awarded=marks_awarded,
            result_question_correctness=correctness,
            result_question_grading_status=grading_status,
            result_question_feedback=feedback,
            result_question_graded_by=graded_by,
            result_question_graded_at=graded_at
        )
        self.db.add(rq)
        try:
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            raise e
        return rq

    async def get_result_question(
        self,
        result_id: uuid.UUID,
        question_id: uuid.UUID
    ) -> Optional[AssessmentResultQuestion]:
        stmt = (
            select(AssessmentResultQuestion)
            .where(
                and_(
                    AssessmentResultQuestion.result_question_result_id == result_id,
                    AssessmentResultQuestion.result_question_assessment_question_id == question_id
                )
            )
            .options(
                selectinload(AssessmentResultQuestion.assessment_question),
                selectinload(AssessmentResultQuestion.grader)
            )
            .execution_options(populate_existing=True)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_assessment_results(
        self,
        assessment_id: uuid.UUID
    ) -> List[AssessmentResult]:
        stmt = (
            select(AssessmentResult)
            .where(AssessmentResult.result_assessment_id == assessment_id)
            .options(
                selectinload(AssessmentResult.question_results),
                selectinload(AssessmentResult.attempt),
                selectinload(AssessmentResult.student)
            )
            .order_by(AssessmentResult.result_created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── Assessment Analytics Repository Methods (Step 10.11) ──────

    async def get_workspace_student_count(self, workspace_id: uuid.UUID) -> int:
        """Count total enrolled students in the workspace."""
        stmt = (
            select(func.count(WorkspaceMember.workspace_member_id))
            .join(Role, WorkspaceMember.workspace_member_role_id == Role.role_id)
            .where(
                and_(
                    WorkspaceMember.workspace_member_workspace_id == workspace_id,
                    Role.role_name.ilike("%student%")
                )
            )
        )
        res = await self.db.execute(stmt)
        count = res.scalar_one()
        if count == 0:
            # Fallback to total workspace members if role names differ
            fallback_stmt = select(func.count(WorkspaceMember.workspace_member_id)).where(
                WorkspaceMember.workspace_member_workspace_id == workspace_id
            )
            fallback_res = await self.db.execute(fallback_stmt)
            count = fallback_res.scalar_one()
        return count

    async def get_assessment_attempts_for_analytics(
        self,
        assessment_id: uuid.UUID
    ) -> List[AssessmentAttempt]:
        """Fetch all attempts for an assessment with student details and answers."""
        stmt = (
            select(AssessmentAttempt)
            .where(AssessmentAttempt.attempt_assessment_id == assessment_id)
            .options(
                selectinload(AssessmentAttempt.student),
                selectinload(AssessmentAttempt.answers)
            )
            .order_by(
                AssessmentAttempt.attempt_student_id,
                AssessmentAttempt.attempt_number.asc()
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_assessment_result_questions_for_analytics(
        self,
        assessment_id: uuid.UUID
    ) -> List[AssessmentResultQuestion]:
        """Fetch all result questions for an assessment."""
        stmt = (
            select(AssessmentResultQuestion)
            .join(AssessmentResult, AssessmentResultQuestion.result_question_result_id == AssessmentResult.result_id)
            .where(AssessmentResult.result_assessment_id == assessment_id)
            .options(
                selectinload(AssessmentResultQuestion.assessment_question)
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_student_attempts_for_analytics(
        self,
        assessment_id: uuid.UUID,
        student_id: uuid.UUID
    ) -> List[AssessmentAttempt]:
        """Fetch all attempts for a specific student and assessment."""
        stmt = (
            select(AssessmentAttempt)
            .where(
                and_(
                    AssessmentAttempt.attempt_assessment_id == assessment_id,
                    AssessmentAttempt.attempt_student_id == student_id
                )
            )
            .options(
                selectinload(AssessmentAttempt.student),
                selectinload(AssessmentAttempt.answers)
            )
            .order_by(AssessmentAttempt.attempt_number.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── Learning Analytics & Question Difficulty Repository Methods (Step 10.12) ──

    async def get_student_all_results_for_learning_analytics(
        self,
        student_id: uuid.UUID,
        org_id: uuid.UUID
    ) -> List[AssessmentResult]:
        """Fetch all assessment results for a student across all subjects in the organization."""
        stmt = (
            select(AssessmentResult)
            .join(Assessment, AssessmentResult.result_assessment_id == Assessment.assessment_id)
            .join(Subject, Assessment.assessment_subject_id == Subject.subject_id)
            .join(Workspace, Subject.subject_workspace_id == Workspace.workspace_id)
            .where(
                and_(
                    AssessmentResult.result_student_id == student_id,
                    Workspace.workspace_organization_id == org_id
                )
            )
            .options(
                selectinload(AssessmentResult.assessment).selectinload(Assessment.subject),
                selectinload(AssessmentResult.attempt),
                selectinload(AssessmentResult.student)
            )
            .order_by(AssessmentResult.result_created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_student_all_result_questions_for_learning_analytics(
        self,
        student_id: uuid.UUID,
        org_id: uuid.UUID
    ) -> List[AssessmentResultQuestion]:
        """Fetch all result questions for a student across the organization."""
        stmt = (
            select(AssessmentResultQuestion)
            .join(AssessmentResult, AssessmentResultQuestion.result_question_result_id == AssessmentResult.result_id)
            .join(Assessment, AssessmentResult.result_assessment_id == Assessment.assessment_id)
            .join(Subject, Assessment.assessment_subject_id == Subject.subject_id)
            .join(Workspace, Subject.subject_workspace_id == Workspace.workspace_id)
            .where(
                and_(
                    AssessmentResult.result_student_id == student_id,
                    Workspace.workspace_organization_id == org_id
                )
            )
            .options(
                selectinload(AssessmentResultQuestion.assessment_question)
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_subject_assessments_and_results_for_analytics(
        self,
        subject_id: uuid.UUID
    ) -> List[Assessment]:
        """Fetch all assessments under a subject with their questions and results."""
        stmt = (
            select(Assessment)
            .where(Assessment.assessment_subject_id == subject_id)
            .options(
                selectinload(Assessment.assessment_questions),
                selectinload(Assessment.results).selectinload(AssessmentResult.student),
                selectinload(Assessment.attempts)
            )
            .order_by(Assessment.assessment_created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_subject_result_questions_for_difficulty_analytics(
        self,
        subject_id: uuid.UUID
    ) -> List[AssessmentResultQuestion]:
        """Fetch all result questions for all assessments in a subject."""
        stmt = (
            select(AssessmentResultQuestion)
            .join(AssessmentResult, AssessmentResultQuestion.result_question_result_id == AssessmentResult.result_id)
            .join(Assessment, AssessmentResult.result_assessment_id == Assessment.assessment_id)
            .where(Assessment.assessment_subject_id == subject_id)
            .options(
                selectinload(AssessmentResultQuestion.assessment_question).selectinload(AssessmentQuestion.source_question)
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_subject_assessment_questions(
        self,
        subject_id: uuid.UUID
    ) -> List[AssessmentQuestion]:
        """Fetch all assessment questions across all assessments in a subject."""
        stmt = (
            select(AssessmentQuestion)
            .join(Assessment, AssessmentQuestion.assessment_question_assessment_id == Assessment.assessment_id)
            .where(Assessment.assessment_subject_id == subject_id)
            .options(
                selectinload(AssessmentQuestion.source_question)
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── Step 10.13: Leaderboard & Class Performance Repository Methods ──

    async def update_assessment_leaderboard_setting(
        self,
        assessment_id: uuid.UUID,
        enabled: bool
    ) -> Optional[Assessment]:
        """Update leaderboard enable/disable toggle for an assessment."""
        assessment = await self.get_assessment_by_id(assessment_id)
        if not assessment:
            return None
        assessment.assessment_leaderboard_enabled = enabled
        self.db.add(assessment)
        await self.db.flush()
        return assessment

    async def get_assessment_completed_results_for_leaderboard(
        self,
        assessment_id: uuid.UUID
    ) -> List[AssessmentResult]:
        """Fetch all completed results for an assessment with student and attempt information."""
        stmt = (
            select(AssessmentResult)
            .where(
                and_(
                    AssessmentResult.result_assessment_id == assessment_id,
                    AssessmentResult.result_status == ResultStatus.COMPLETED
                )
            )
            .options(
                selectinload(AssessmentResult.student),
                selectinload(AssessmentResult.attempt)
            )
            .order_by(AssessmentResult.result_created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_student_attempts_count_for_assessment(
        self,
        assessment_id: uuid.UUID
    ) -> Dict[uuid.UUID, int]:
        """Return a mapping of student_id -> total attempts used for this assessment."""
        stmt = (
            select(
                AssessmentAttempt.attempt_student_id,
                func.count(AssessmentAttempt.attempt_id)
            )
            .where(AssessmentAttempt.attempt_assessment_id == assessment_id)
            .group_by(AssessmentAttempt.attempt_student_id)
        )
        result = await self.db.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def get_workspace_students(
        self,
        workspace_id: uuid.UUID
    ) -> List[User]:
        """Fetch all enrolled students in a workspace."""
        stmt = (
            select(User)
            .join(WorkspaceMember, User.user_id == WorkspaceMember.workspace_member_user_id)
            .join(Role, WorkspaceMember.workspace_member_role_id == Role.role_id)
            .where(
                and_(
                    WorkspaceMember.workspace_member_workspace_id == workspace_id,
                    func.lower(Role.role_name) == "student"
                )
            )
            .order_by(User.user_first_name.asc(), User.user_last_name.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_workspace_student_count(
        self,
        workspace_id: uuid.UUID
    ) -> int:
        """Count all enrolled students in a workspace."""
        stmt = (
            select(func.count(WorkspaceMember.workspace_member_id))
            .join(Role, WorkspaceMember.workspace_member_role_id == Role.role_id)
            .where(
                and_(
                    WorkspaceMember.workspace_member_workspace_id == workspace_id,
                    func.lower(Role.role_name) == "student"
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_subject_student_results_and_attempts(
        self,
        subject_id: uuid.UUID
    ) -> List[AssessmentResult]:
        """Fetch all assessment results for all assessments in a subject."""
        stmt = (
            select(AssessmentResult)
            .join(Assessment, AssessmentResult.result_assessment_id == Assessment.assessment_id)
            .where(Assessment.assessment_subject_id == subject_id)
            .options(
                selectinload(AssessmentResult.student),
                selectinload(AssessmentResult.assessment),
                selectinload(AssessmentResult.attempt)
            )
            .order_by(AssessmentResult.result_created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())




