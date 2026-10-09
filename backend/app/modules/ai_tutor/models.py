import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base


class AiTutorConversation(Base):
    __tablename__ = "tbl_ai_tutor_conversations"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    conversation_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_organizations.organization_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    conversation_workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_workspaces.workspace_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    conversation_subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_subjects.subject_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    conversation_student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    conversation_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="New Conversation"
    )
    conversation_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    conversation_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    messages: Mapped[List["AiTutorMessage"]] = relationship(
        "AiTutorMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AiTutorMessage.message_created_at"
    )


class AiTutorMessage(Base):
    __tablename__ = "tbl_ai_tutor_messages"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    message_conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_ai_tutor_conversations.conversation_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    message_role: Mapped[str] = mapped_column(
        String(32),
        nullable=False
    )  # "user" or "assistant"
    message_content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    message_sources: Mapped[Optional[Any]] = mapped_column(
        JSON,
        nullable=True
    )
    message_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    conversation: Mapped["AiTutorConversation"] = relationship(
        "AiTutorConversation",
        back_populates="messages"
    )
