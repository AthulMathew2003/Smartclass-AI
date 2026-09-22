import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from sqlalchemy import (
    String,
    Text,
    DateTime,
    Numeric,
    Integer,
    Boolean,
    Enum as SQLEnum,
    ForeignKey,
    UniqueConstraint,
    JSON,
    func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base


class AssessmentType(str, Enum):
    QUIZ = "quiz"
    EXAM = "exam"
    PRACTICE = "practice"


class AssessmentStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


class QuestionType(str, Enum):
    MCQ_SINGLE = "mcq_single"
    MCQ_MULTIPLE = "mcq_multiple"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"


class QuestionStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class Assessment(Base):
    __tablename__ = "tbl_assessments"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    assessment_subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_subjects.subject_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    assessment_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    assessment_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    assessment_type: Mapped[AssessmentType] = mapped_column(
        SQLEnum(
            AssessmentType,
            name="assessment_type_enum",
            values_callable=lambda obj: [e.value for e in obj]
        ),
        default=AssessmentType.QUIZ,
        nullable=False
    )
    assessment_status: Mapped[AssessmentStatus] = mapped_column(
        SQLEnum(
            AssessmentStatus,
            name="assessment_status_enum",
            values_callable=lambda obj: [e.value for e in obj]
        ),
        default=AssessmentStatus.DRAFT,
        nullable=False,
        index=True
    )
    assessment_duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    assessment_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )
    assessment_end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )
    assessment_total_marks: Mapped[Decimal] = mapped_column(
        Numeric(precision=7, scale=2),
        nullable=False
    )
    assessment_passing_marks: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=7, scale=2),
        nullable=True
    )
    assessment_attempt_limit: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
        nullable=False
    )
    assessment_randomize_questions: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False
    )
    assessment_created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_users.user_id", ondelete="SET NULL"),
        nullable=True
    )
    assessment_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False
    )
    assessment_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    subject = relationship("Subject", back_populates="assessments")
    creator = relationship("User", foreign_keys=[assessment_created_by], lazy="selectin")
    assessment_questions = relationship(
        "AssessmentQuestion",
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="AssessmentQuestion.assessment_question_order"
    )
    questions = relationship(
        "AssessmentQuestion",
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="AssessmentQuestion.assessment_question_order",
        overlaps="assessment_questions"
    )


class QuestionBankItem(Base):
    __tablename__ = "tbl_questions"

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    question_subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_subjects.subject_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    question_type: Mapped[QuestionType] = mapped_column(
        SQLEnum(
            QuestionType,
            name="question_type_enum",
            values_callable=lambda obj: [e.value for e in obj]
        ),
        nullable=False
    )
    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    question_default_marks: Mapped[Decimal] = mapped_column(
        Numeric(precision=7, scale=2),
        default=Decimal("1.00"),
        server_default="1.00",
        nullable=False
    )
    question_explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    question_status: Mapped[QuestionStatus] = mapped_column(
        SQLEnum(
            QuestionStatus,
            name="question_status_enum",
            values_callable=lambda obj: [e.value for e in obj]
        ),
        default=QuestionStatus.ACTIVE,
        nullable=False,
        index=True
    )
    question_created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_users.user_id", ondelete="SET NULL"),
        nullable=True
    )
    question_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False
    )
    question_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    subject = relationship("Subject", back_populates="questions")
    creator = relationship("User", foreign_keys=[question_created_by], lazy="selectin")
    options = relationship(
        "QuestionOption",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuestionOption.option_order"
    )


class QuestionOption(Base):
    __tablename__ = "tbl_question_options"
    __table_args__ = (
        UniqueConstraint("option_question_id", "option_order", name="uq_question_option_order"),
    )

    option_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    option_question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_questions.question_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    option_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    option_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    option_is_correct: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    question = relationship("QuestionBankItem", back_populates="options")


class AssessmentQuestion(Base):
    __tablename__ = "tbl_assessment_questions"
    __table_args__ = (
        UniqueConstraint("assessment_question_assessment_id", "assessment_question_order", name="uq_assessment_question_order"),
        UniqueConstraint("assessment_question_assessment_id", "assessment_question_question_id", name="uq_assessment_question_unique_bank_q"),
    )

    assessment_question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    assessment_question_assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_assessments.assessment_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    assessment_question_question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_questions.question_id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    assessment_question_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True
    )
    assessment_question_marks: Mapped[Decimal] = mapped_column(
        Numeric(precision=7, scale=2),
        nullable=False
    )
    assessment_question_snapshot: Mapped[dict] = mapped_column(
        JSON,
        nullable=False
    )
    assessment_question_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False
    )

    assessment = relationship("Assessment", back_populates="assessment_questions")
    source_question = relationship("QuestionBankItem", foreign_keys=[assessment_question_question_id], lazy="selectin")
