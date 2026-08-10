import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import String, Text, DateTime, Enum as SQLEnum, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base
from app.modules.rbac.models import Permission, RolePermission


class OrganizationStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class WorkspaceStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class OrganizationMemberStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Organization(Base):
    __tablename__ = "tbl_organizations"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    organization_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    organization_slug: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    organization_logo: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    organization_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    organization_owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    organization_status: Mapped[OrganizationStatus] = mapped_column(
        SQLEnum(OrganizationStatus, name="organization_status_enum", values_callable=lambda obj: [e.value for e in obj]),
        default=OrganizationStatus.ACTIVE,
        nullable=False
    )
    organization_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    organization_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    workspaces = relationship("Workspace", back_populates="organization", cascade="all, delete-orphan")
    roles = relationship("Role", back_populates="organization", cascade="all, delete-orphan")
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")


class Role(Base):
    __tablename__ = "tbl_roles"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    role_organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_organizations.organization_id", ondelete="CASCADE"),
        nullable=True
    )
    role_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    role_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    role_is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    role_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    role_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    organization = relationship("Organization", back_populates="roles")
    organization_members = relationship("OrganizationMember", back_populates="role")
    workspace_members = relationship("WorkspaceMember", back_populates="role")
    permissions = relationship("Permission", secondary="tbl_role_permissions", back_populates="roles")


class Workspace(Base):
    __tablename__ = "tbl_workspaces"
    __table_args__ = (
        UniqueConstraint(
            "workspace_organization_id",
            "workspace_name",
            name="uq_workspace_org_name"
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    workspace_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_organizations.organization_id", ondelete="CASCADE"),
        nullable=False
    )
    workspace_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    workspace_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    workspace_banner: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    workspace_status: Mapped[WorkspaceStatus] = mapped_column(
        SQLEnum(WorkspaceStatus, name="workspace_status_enum", values_callable=lambda obj: [e.value for e in obj]),
        default=WorkspaceStatus.ACTIVE,
        nullable=False
    )
    workspace_created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    workspace_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    workspace_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    organization = relationship("Organization", back_populates="workspaces")
    members = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")


class OrganizationMember(Base):
    __tablename__ = "tbl_organization_members"
    __table_args__ = (
        UniqueConstraint(
            "organization_member_user_id",
            "organization_member_organization_id",
            name="uq_org_member"
        ),
    )

    organization_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    organization_member_organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_organizations.organization_id", ondelete="CASCADE"),
        nullable=False
    )
    organization_member_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    organization_member_role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_roles.role_id", ondelete="RESTRICT"),
        nullable=False
    )
    organization_member_status: Mapped[OrganizationMemberStatus] = mapped_column(
        SQLEnum(OrganizationMemberStatus, name="org_member_status_enum", values_callable=lambda obj: [e.value for e in obj]),
        default=OrganizationMemberStatus.ACTIVE,
        nullable=False
    )
    organization_member_joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    organization_member_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    organization_member_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    organization = relationship("Organization", back_populates="members")
    role = relationship("Role", back_populates="organization_members")


class WorkspaceMember(Base):
    __tablename__ = "tbl_workspace_members"
    __table_args__ = (
        UniqueConstraint(
            "workspace_member_workspace_id",
            "workspace_member_user_id",
            name="uq_workspace_member"
        ),
    )

    workspace_member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    workspace_member_workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_workspaces.workspace_id", ondelete="CASCADE"),
        nullable=False
    )
    workspace_member_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    workspace_member_role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tbl_roles.role_id", ondelete="RESTRICT"),
        nullable=False
    )
    workspace_member_joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    workspace = relationship("Workspace", back_populates="members")
    role = relationship("Role", back_populates="workspace_members")
