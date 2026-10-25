"""
Question Paper Draft SQLAlchemy models.

Two tables:
  tbl_qp_drafts        — one row per generation session
  tbl_qp_draft_questions — one row per generated question

Draft lifecycle: generating → ready (or failed) → converted
Converted drafts have draft_converted_assessment_id set.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    String, Text, Integer, Boolean, Numeric, DateTime,
    Enum as SQLEnum, ForeignKey, JSON, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class QpDraftStatus(str, Enum):
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    CONVERTED = "converted"


class QpDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    MIXED = "mixed"


class QpDraft(Base):
    __tablename__ = "tbl_qp_drafts"

    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    draft_subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_subjects.subject_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    draft_created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    draft_title: Mapped[str] = mapped_column(String(255), nullable=False)
    draft_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_status: Mapped[QpDraftStatus] = mapped_column(
        SQLEnum(
            QpDraftStatus,
            name="qp_draft_status_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=QpDraftStatus.GENERATING,
        nullable=False,
        index=True,
    )
    # Full generation config stored as JSON for provenance and re-generation
    draft_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Server-side validation report (last run)
    draft_validation_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Human-readable error if generation failed
    draft_generation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Set when teacher converts draft → assessment
    draft_converted_assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_assessments.assessment_id", ondelete="SET NULL"),
        nullable=True,
    )
    draft_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    draft_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    subject = relationship("Subject", foreign_keys=[draft_subject_id], lazy="selectin")
    creator = relationship("User", foreign_keys=[draft_created_by], lazy="selectin")
    questions = relationship(
        "QpDraftQuestion",
        back_populates="draft",
        cascade="all, delete-orphan",
        order_by="QpDraftQuestion.dq_order",
    )


class QpDraftQuestion(Base):
    __tablename__ = "tbl_qp_draft_questions"

    dq_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dq_draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_qp_drafts.draft_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dq_order: Mapped[int] = mapped_column(Integer, nullable=False)
    # Maps to existing QuestionType enum values
    dq_question_type: Mapped[str] = mapped_column(String(32), nullable=False)
    dq_question_text: Mapped[str] = mapped_column(Text, nullable=False)
    dq_marks: Mapped[float] = mapped_column(Numeric(precision=7, scale=2), nullable=False)
    dq_difficulty: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    # For MCQ/T-F: [{text, is_correct}]
    dq_options: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # For short_answer
    dq_expected_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    dq_rubric: Mapped[str | None] = mapped_column(Text, nullable=True)
    dq_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Source provenance — list of material UUIDs (as strings)
    dq_source_material_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Detailed chunk-level provenance
    dq_source_chunks: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Internal audit metadata (model, timestamp, generation prompt hash, etc.)
    dq_generation_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Teacher flagged this question for manual review
    dq_is_flagged: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    dq_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    dq_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    draft = relationship("QpDraft", back_populates="questions")
