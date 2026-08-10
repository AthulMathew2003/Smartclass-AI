"""rbac schema

Revision ID: 4fe5c6002ca5
Revises: 01a6df3b0e46
Create Date: 2026-08-06 08:48:15.585511+00:00

"""
from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text, table, column


# revision identifiers, used by Alembic.
revision: str = '4fe5c6002ca5'
down_revision: Union[str, Sequence[str], None] = '01a6df3b0e46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Define table representations
permissions_table = table(
    'tbl_permissions',
    column('permission_id', sa.UUID),
    column('permission_name', sa.String),
    column('permission_description', sa.Text),
    column('permission_created_at', sa.DateTime),
    column('permission_updated_at', sa.DateTime)
)

role_permissions_table = table(
    'tbl_role_permissions',
    column('role_permission_id', sa.UUID),
    column('role_id', sa.UUID),
    column('permission_id', sa.UUID),
    column('role_permission_created_at', sa.DateTime)
)


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create tbl_permissions
    op.create_table(
        'tbl_permissions',
        sa.Column('permission_id', sa.UUID(), nullable=False),
        sa.Column('permission_name', sa.String(length=100), nullable=False),
        sa.Column('permission_description', sa.Text(), nullable=True),
        sa.Column('permission_created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('permission_updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('permission_id'),
        sa.UniqueConstraint('permission_name')
    )

    # 2. Create tbl_role_permissions
    op.create_table(
        'tbl_role_permissions',
        sa.Column('role_permission_id', sa.UUID(), nullable=False),
        sa.Column('role_id', sa.UUID(), nullable=False),
        sa.Column('permission_id', sa.UUID(), nullable=False),
        sa.Column('role_permission_created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['tbl_permissions.permission_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['tbl_roles.role_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_permission_id'),
        sa.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission')
    )

    # 3. Seed permissions
    all_permissions = [
        ("member.create", "Create new organization members"),
        ("member.read", "View organization members"),
        ("member.update", "Edit organization members"),
        ("member.delete", "Remove organization members"),
        ("workspace.create", "Create workspaces"),
        ("workspace.read", "View workspaces"),
        ("workspace.update", "Edit workspaces"),
        ("workspace.delete", "Delete workspaces"),
        ("organization.update", "Update organization settings"),
        ("classroom.create", "Create classrooms"),
        ("classroom.update", "Update classrooms"),
        ("assignment.create", "Create assignments"),
        ("assignment.update", "Update assignments"),
        ("assignment.grade", "Grade student assignments"),
        ("attendance.view", "View attendance records"),
        ("attendance.manage", "Take or update attendance"),
        ("exam.create", "Create exams"),
        ("exam.publish", "Publish exams"),
        ("analytics.view", "View classroom analytics"),
        ("ai.use", "Use AI tutor features"),
        ("settings.manage", "Manage classroom settings")
    ]

    permission_ids_map = {}
    for name, desc in all_permissions:
        perm_id = uuid.uuid4()
        permission_ids_map[name] = perm_id
        op.bulk_insert(
            permissions_table,
            [
                {
                    "permission_id": perm_id,
                    "permission_name": name,
                    "permission_description": desc,
                    "permission_created_at": datetime.now(timezone.utc),
                    "permission_updated_at": datetime.now(timezone.utc)
                }
            ]
        )

    # 4. Fetch seeded global roles to create role-permission mappings
    conn = op.get_bind()
    roles = conn.execute(text("SELECT role_id, role_name FROM tbl_roles WHERE role_organization_id IS NULL")).fetchall()
    roles_map = {r[1]: r[0] for r in roles}

    # Define role-to-permission mappings
    role_perms_mapping = {
        "Owner": list(permission_ids_map.keys()),
        "Admin": [
            "member.create", "member.read", "member.update", "member.delete",
            "workspace.create", "workspace.read", "workspace.update", "workspace.delete",
            "classroom.create", "classroom.update", "assignment.create", "assignment.update",
            "attendance.view", "attendance.manage", "analytics.view"
        ],
        "Teacher": [
            "workspace.read", "classroom.create", "classroom.update",
            "assignment.create", "assignment.update", "assignment.grade",
            "attendance.view", "attendance.manage", "analytics.view", "ai.use"
        ],
        "Student": [
            "workspace.read", "attendance.view", "ai.use"
        ],
        "Parent": [
            "workspace.read", "attendance.view"
        ],
        "Staff": [
            "workspace.read", "attendance.view", "analytics.view"
        ]
    }

    # Insert role-permission mappings
    for role_name, perm_names in role_perms_mapping.items():
        role_id = roles_map.get(role_name)
        if not role_id:
            continue
        for pname in perm_names:
            pid = permission_ids_map.get(pname)
            if pid:
                op.bulk_insert(
                    role_permissions_table,
                    [
                        {
                            "role_permission_id": uuid.uuid4(),
                            "role_id": role_id,
                            "permission_id": pid,
                            "role_permission_created_at": datetime.now(timezone.utc)
                        }
                    ]
                )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('tbl_role_permissions')
    op.drop_table('tbl_permissions')
