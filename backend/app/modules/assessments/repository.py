import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
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
    QuestionStatus
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
        created_by: Optional[uuid.UUID]
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
        randomize_questions: Optional[bool] = None
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
