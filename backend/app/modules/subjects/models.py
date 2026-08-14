import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import String, Text, DateTime, Enum as SQLEnum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base


class SubjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class Subject(Base):
    __tablename__ = "tbl_subjects"
    __table_args__ = (
        UniqueConstraint(
            "subject_workspace_id",
            "subject_name",
            name="uq_subject_workspace_name"
        ),
    )

    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    subject_workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_workspaces.workspace_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    subject_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    subject_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    subject_status: Mapped[SubjectStatus] = mapped_column(
        SQLEnum(SubjectStatus, name="subject_status_enum", values_callable=lambda obj: [e.value for e in obj]),
        default=SubjectStatus.ACTIVE,
        nullable=False
    )
    subject_created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_users.user_id", ondelete="SET NULL"),
        nullable=True
    )
    subject_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    subject_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    _teachers = relationship("SubjectTeacher", back_populates="subject", cascade="all, delete-orphan")


class SubjectTeacher(Base):
    __tablename__ = "tbl_subject_teachers"
    __table_args__ = (
        UniqueConstraint(
            "subject_teacher_subject_id",
            "subject_teacher_user_id",
            name="uq_subject_teacher"
        ),
    )

    subject_teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    subject_teacher_subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_subjects.subject_id", ondelete="CASCADE"),
        nullable=False
    )
    subject_teacher_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    subject_teacher_assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    subject = relationship("Subject", back_populates="_teachers")
    user = relationship("User", foreign_keys=[subject_teacher_user_id], lazy="selectin")
