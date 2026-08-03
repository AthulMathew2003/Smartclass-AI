import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import String, Text, DateTime, Enum as SQLEnum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base


class OAuthProvider(str, Enum):
    GOOGLE = "google"
    GITHUB = "github"


class OAuthAccount(Base):
    __tablename__ = "tbl_oauth_accounts"
    __table_args__ = (
        UniqueConstraint(
            "oauth_account_provider",
            "oauth_account_provider_user_id",
            name="uq_provider_user_id"
        ),
    )

    oauth_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    oauth_account_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    oauth_account_provider: Mapped[OAuthProvider] = mapped_column(
        SQLEnum(OAuthProvider, name="oauth_provider_enum", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False
    )
    oauth_account_provider_user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    oauth_account_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user = relationship("User", back_populates="oauth_accounts")


class RefreshToken(Base):
    __tablename__ = "tbl_refresh_tokens"

    refresh_token_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    refresh_token_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True
    )
    refresh_token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    refresh_token_revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    refresh_token_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user = relationship("User", back_populates="refresh_tokens")
