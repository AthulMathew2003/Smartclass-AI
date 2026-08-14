import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import String, Text, DateTime, Numeric, Enum as SQLEnum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base


class AssignmentStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"
    ARCHIVED = "archived"


class SubmissionStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    LATE = "late"
    GRADED = "graded"
    RETURNED = "returned"


class Assignment(Base):
    __tablename__ = "tbl_assignments"

    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    assignment_subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_subjects.subject_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    assignment_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    assignment_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    assignment_status: Mapped[AssignmentStatus] = mapped_column(
        SQLEnum(
            AssignmentStatus,
            name="assignment_status_enum",
            values_callable=lambda obj: [e.value for e in obj]
        ),
        default=AssignmentStatus.DRAFT,
        nullable=False,
        index=True
    )
    assignment_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )
    assignment_created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_users.user_id", ondelete="SET NULL"),
        nullable=True
    )
    assignment_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    assignment_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    subject = relationship("Subject", back_populates="assignments")
    submissions = relationship("AssignmentSubmission", back_populates="assignment", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[assignment_created_by], lazy="selectin")


class AssignmentSubmission(Base):
    __tablename__ = "tbl_assignment_submissions"
    __table_args__ = (
        UniqueConstraint(
            "submission_assignment_id",
            "submission_student_id",
            name="uq_assignment_student_submission"
        ),
    )

    submission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    submission_assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_assignments.assignment_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    submission_student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    submission_status: Mapped[SubmissionStatus] = mapped_column(
        SQLEnum(
            SubmissionStatus,
            name="submission_status_enum",
            values_callable=lambda obj: [e.value for e in obj]
        ),
        default=SubmissionStatus.DRAFT,
        nullable=False,
        index=True
    )
    submission_submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    submission_grade: Mapped[float | None] = mapped_column(
        Numeric(precision=5, scale=2),
        nullable=True
    )
    submission_feedback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    submission_graded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_users.user_id", ondelete="SET NULL"),
        nullable=True
    )
    submission_graded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    submission_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    submission_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("User", foreign_keys=[submission_student_id], lazy="selectin")
    grader = relationship("User", foreign_keys=[submission_graded_by], lazy="selectin")
