"""
Repository for Question Paper Draft CRUD operations.
All queries are subject-scoped for tenant isolation.
"""
import uuid
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.assessments.qp_models import QpDraft, QpDraftQuestion, QpDraftStatus


class QpDraftRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Draft CRUD ────────────────────────────────────────────────

    async def create_draft(
        self,
        subject_id: uuid.UUID,
        created_by: uuid.UUID,
        title: str,
        description: Optional[str],
        config: dict,
        status: QpDraftStatus = QpDraftStatus.GENERATING,
    ) -> QpDraft:
        draft = QpDraft(
            draft_subject_id=subject_id,
            draft_created_by=created_by,
            draft_title=title,
            draft_description=description,
            draft_config=config,
            draft_status=status,
        )
        self.db.add(draft)
        await self.db.flush()
        return draft

    async def get_draft(
        self, draft_id: uuid.UUID, subject_id: Optional[uuid.UUID] = None
    ) -> Optional[QpDraft]:
        stmt = (
            select(QpDraft)
            .where(QpDraft.draft_id == draft_id)
            .options(selectinload(QpDraft.questions), selectinload(QpDraft.subject))
        )
        if subject_id is not None:
            stmt = stmt.where(QpDraft.draft_subject_id == subject_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_drafts_for_subject(
        self, subject_id: uuid.UUID
    ) -> List[QpDraft]:
        stmt = (
            select(QpDraft)
            .where(QpDraft.draft_subject_id == subject_id)
            .options(selectinload(QpDraft.questions))
            .order_by(QpDraft.draft_created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_draft_status(
        self,
        draft: QpDraft,
        status: QpDraftStatus,
        error: Optional[str] = None,
        validation_result: Optional[dict] = None,
    ) -> QpDraft:
        draft.draft_status = status
        if error is not None:
            draft.draft_generation_error = error[:2000]
        if validation_result is not None:
            draft.draft_validation_result = validation_result
        await self.db.flush()
        return draft

    async def update_draft_metadata(
        self,
        draft: QpDraft,
        title: Optional[str] = None,
        description: Optional[str] = None,
        config: Optional[dict] = None,
        validation_result: Optional[dict] = None,
    ) -> QpDraft:
        if title is not None:
            draft.draft_title = title.strip()
        if description is not None:
            draft.draft_description = description.strip() or None
        if config is not None:
            draft.draft_config = config
        if validation_result is not None:
            draft.draft_validation_result = validation_result
        await self.db.flush()
        return draft

    async def mark_converted(
        self, draft: QpDraft, assessment_id: uuid.UUID
    ) -> QpDraft:
        draft.draft_status = QpDraftStatus.CONVERTED
        draft.draft_converted_assessment_id = assessment_id
        await self.db.flush()
        return draft

    async def delete_draft(self, draft: QpDraft) -> None:
        await self.db.delete(draft)
        await self.db.flush()

    # ── Draft Question CRUD ───────────────────────────────────────

    async def bulk_insert_questions(
        self, draft_id: uuid.UUID, questions: List[dict]
    ) -> List[QpDraftQuestion]:
        """Insert questions for a draft in one flush."""
        objs: List[QpDraftQuestion] = []
        for idx, q in enumerate(questions):
            obj = QpDraftQuestion(
                dq_draft_id=draft_id,
                dq_order=q.get("order", idx + 1),
                dq_question_type=q["question_type"],
                dq_question_text=q["question_text"],
                dq_marks=q["marks"],
                dq_difficulty=q.get("difficulty", "medium"),
                dq_options=q.get("options"),
                dq_expected_answer=q.get("expected_answer"),
                dq_rubric=q.get("rubric"),
                dq_explanation=q.get("explanation"),
                dq_source_material_ids=q.get("source_material_ids", []),
                dq_source_chunks=q.get("source_chunks"),
                dq_generation_metadata=q.get("generation_metadata"),
            )
            self.db.add(obj)
            objs.append(obj)
        await self.db.flush()
        return objs

    async def get_question(
        self, dq_id: uuid.UUID, draft_id: uuid.UUID
    ) -> Optional[QpDraftQuestion]:
        stmt = select(QpDraftQuestion).where(
            and_(
                QpDraftQuestion.dq_id == dq_id,
                QpDraftQuestion.dq_draft_id == draft_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_question(
        self,
        question: QpDraftQuestion,
        question_text: Optional[str] = None,
        marks: Optional[float] = None,
        difficulty: Optional[str] = None,
        options: Optional[list] = None,
        expected_answer: Optional[str] = None,
        rubric: Optional[str] = None,
        explanation: Optional[str] = None,
        is_flagged: Optional[bool] = None,
        source_material_ids: Optional[list] = None,
        source_chunks: Optional[list] = None,
        generation_metadata: Optional[dict] = None,
    ) -> QpDraftQuestion:
        if question_text is not None:
            question.dq_question_text = question_text.strip()
        if marks is not None:
            question.dq_marks = marks
        if difficulty is not None:
            question.dq_difficulty = difficulty
        if options is not None:
            question.dq_options = options
        if expected_answer is not None:
            question.dq_expected_answer = expected_answer.strip() or None
        if rubric is not None:
            question.dq_rubric = rubric.strip() or None
        if explanation is not None:
            question.dq_explanation = explanation.strip() or None
        if is_flagged is not None:
            question.dq_is_flagged = is_flagged
        if source_material_ids is not None:
            question.dq_source_material_ids = source_material_ids
        if source_chunks is not None:
            question.dq_source_chunks = source_chunks
        if generation_metadata is not None:
            question.dq_generation_metadata = generation_metadata
        await self.db.flush()
        return question

    async def delete_question(self, question: QpDraftQuestion) -> None:
        await self.db.delete(question)
        await self.db.flush()

    async def delete_all_questions(self, draft_id: uuid.UUID) -> None:
        """Remove all questions for a draft (before regeneration)."""
        stmt = select(QpDraftQuestion).where(
            QpDraftQuestion.dq_draft_id == draft_id
        )
        result = await self.db.execute(stmt)
        for q in result.scalars().all():
            await self.db.delete(q)
        await self.db.flush()
