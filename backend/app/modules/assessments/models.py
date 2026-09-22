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


class AttemptStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    EXPIRED = "expired"


class ResultStatus(str, Enum):
    PENDING_MANUAL_GRADING = "pending_manual_grading"
    COMPLETED = "completed"


class GradingStatus(str, Enum):
    PENDING = "pending"
    GRADED = "graded"


class CorrectnessStatus(str, Enum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    UNANSWERED = "unanswered"
    PENDING = "pending"



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
    assessment_leaderboard_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        index=True
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
    attempts = relationship(
        "AssessmentAttempt",
        back_populates="assessment",
        cascade="all, delete-orphan"
    )
    results = relationship(
        "AssessmentResult",
        back_populates="assessment",
        cascade="all, delete-orphan"
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
    result_questions = relationship("AssessmentResultQuestion", back_populates="assessment_question", cascade="all, delete-orphan")


class AssessmentAttempt(Base):
    __tablename__ = "tbl_assessment_attempts"
    __table_args__ = (
        UniqueConstraint("attempt_assessment_id", "attempt_student_id", "attempt_number", name="uq_assessment_student_attempt_number"),
    )

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    attempt_assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_assessments.assessment_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    attempt_student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    attempt_status: Mapped[AttemptStatus] = mapped_column(
        SQLEnum(
            AttemptStatus,
            name="attempt_status_enum",
            values_callable=lambda obj: [e.value for e in obj]
        ),
        default=AttemptStatus.IN_PROGRESS,
        nullable=False,
        index=True
    )
    attempt_question_order: Mapped[list] = mapped_column(
        JSON,
        default=list,
        nullable=False
    )
    attempt_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False
    )
    attempt_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )
    attempt_submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    attempt_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False
    )
    attempt_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    assessment = relationship("Assessment", back_populates="attempts")
    student = relationship("User", foreign_keys=[attempt_student_id], lazy="selectin")
    answers = relationship("AssessmentAttemptAnswer", back_populates="attempt", cascade="all, delete-orphan", lazy="selectin")


class AssessmentAttemptAnswer(Base):
    __tablename__ = "tbl_assessment_attempt_answers"
    __table_args__ = (
        UniqueConstraint("attempt_answer_attempt_id", "attempt_answer_question_id", name="uq_attempt_answer_question"),
    )

    attempt_answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    attempt_answer_attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_assessment_attempts.attempt_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    attempt_answer_question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_assessment_questions.assessment_question_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    attempt_answer_value: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False
    )
    attempt_answer_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False
    )
    attempt_answer_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    attempt = relationship("AssessmentAttempt", back_populates="answers")
    assessment_question = relationship("AssessmentQuestion", foreign_keys=[attempt_answer_question_id], lazy="selectin")


class AssessmentResult(Base):
    __tablename__ = "tbl_assessment_results"
    __table_args__ = (
        UniqueConstraint("result_attempt_id", name="uq_assessment_result_attempt"),
    )

    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    result_attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_assessment_attempts.attempt_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    result_assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_assessments.assessment_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    result_student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    result_total_marks: Mapped[Decimal] = mapped_column(
        Numeric(precision=7, scale=2),
        nullable=False
    )
    result_obtained_marks: Mapped[Decimal] = mapped_column(
        Numeric(precision=7, scale=2),
        default=Decimal("0.00"),
        server_default="0.00",
        nullable=False
    )
    result_percentage: Mapped[Decimal] = mapped_column(
        Numeric(precision=5, scale=2),
        default=Decimal("0.00"),
        server_default="0.00",
        nullable=False
    )
    result_passed: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True
    )
    result_status: Mapped[ResultStatus] = mapped_column(
        SQLEnum(
            ResultStatus,
            name="assessment_result_status_enum",
            values_callable=lambda obj: [e.value for e in obj]
        ),
        default=ResultStatus.COMPLETED,
        nullable=False,
        index=True
    )
    result_correct_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False
    )
    result_incorrect_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False
    )
    result_unanswered_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False
    )
    result_pending_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False
    )
    result_graded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    result_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False
    )
    result_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    attempt = relationship("AssessmentAttempt", foreign_keys=[result_attempt_id], lazy="selectin")
    assessment = relationship("Assessment", back_populates="results")
    student = relationship("User", foreign_keys=[result_student_id], lazy="selectin")
    question_results = relationship(
        "AssessmentResultQuestion",
        back_populates="result",
        cascade="all, delete-orphan",
        lazy="selectin"
    )


class AssessmentResultQuestion(Base):
    __tablename__ = "tbl_assessment_result_questions"
    __table_args__ = (
        UniqueConstraint("result_question_result_id", "result_question_assessment_question_id", name="uq_result_assessment_question"),
    )

    result_question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    result_question_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_assessment_results.result_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    result_question_assessment_question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_assessment_questions.assessment_question_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    result_question_answer_value: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True
    )
    result_question_marks_available: Mapped[Decimal] = mapped_column(
        Numeric(precision=7, scale=2),
        nullable=False
    )
    result_question_marks_awarded: Mapped[Decimal] = mapped_column(
        Numeric(precision=7, scale=2),
        default=Decimal("0.00"),
        server_default="0.00",
        nullable=False
    )
    result_question_correctness: Mapped[CorrectnessStatus] = mapped_column(
        SQLEnum(
            CorrectnessStatus,
            name="assessment_correctness_status_enum",
            values_callable=lambda obj: [e.value for e in obj]
        ),
        default=CorrectnessStatus.PENDING,
        nullable=False
    )
    result_question_grading_status: Mapped[GradingStatus] = mapped_column(
        SQLEnum(
            GradingStatus,
            name="assessment_grading_status_enum",
            values_callable=lambda obj: [e.value for e in obj]
        ),
        default=GradingStatus.PENDING,
        nullable=False
    )
    result_question_feedback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    result_question_graded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_users.user_id", ondelete="SET NULL"),
        nullable=True
    )
    result_question_graded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    result_question_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False
    )
    result_question_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    result = relationship("AssessmentResult", back_populates="question_results")
    assessment_question = relationship("AssessmentQuestion", foreign_keys=[result_question_assessment_question_id], lazy="selectin")
    grader = relationship("User", foreign_keys=[result_question_graded_by], lazy="selectin")


