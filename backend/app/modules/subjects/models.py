import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import String, Text, DateTime, BigInteger, Enum as SQLEnum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base


class SubjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class SubjectMaterialStatus(str, Enum):
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

    workspace = relationship("Workspace", foreign_keys=[subject_workspace_id], lazy="selectin")
    _teachers = relationship("SubjectTeacher", back_populates="subject", cascade="all, delete-orphan")
    materials = relationship("SubjectMaterial", back_populates="subject", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="subject", cascade="all, delete-orphan")
    assessments = relationship("Assessment", back_populates="subject", cascade="all, delete-orphan")
    questions = relationship("QuestionBankItem", back_populates="subject", cascade="all, delete-orphan")


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


class SubjectMaterial(Base):
    __tablename__ = "tbl_subject_materials"

    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    material_subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_subjects.subject_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    material_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    material_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    material_category: Mapped[str] = mapped_column(
        String(100),
        default="Notes",
        nullable=False
    )
    material_original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    material_content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    material_file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )
    material_s3_key: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    material_status: Mapped[SubjectMaterialStatus] = mapped_column(
        SQLEnum(SubjectMaterialStatus, name="subject_material_status_enum", values_callable=lambda obj: [e.value for e in obj]),
        default=SubjectMaterialStatus.ACTIVE,
        nullable=False,
        index=True
    )
    material_uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_users.user_id", ondelete="SET NULL"),
        nullable=True
    )
    material_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    material_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    subject = relationship("Subject", back_populates="materials")
    uploader = relationship("User", foreign_keys=[material_uploaded_by], lazy="selectin")

