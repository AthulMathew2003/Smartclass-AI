"""add_assessments_foundation

Revision ID: e71829a3b901
Revises: d5e81c029fa1
Create Date: 2026-08-18 09:15:00.000000+00:00

"""
from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text, table, column


# revision identifiers, used by Alembic.
revision: str = 'e71829a3b901'
down_revision: Union[str, Sequence[str], None] = 'd5e81c029fa1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create tbl_assessments and seed assessment permissions."""
    # 1. Create tbl_assessments
    op.create_table(
        'tbl_assessments',
        sa.Column('assessment_id', sa.UUID(), nullable=False),
        sa.Column('assessment_subject_id', sa.UUID(), nullable=False),
        sa.Column('assessment_title', sa.String(length=255), nullable=False),
        sa.Column('assessment_description', sa.Text(), nullable=True),
        sa.Column(
            'assessment_type',
            sa.Enum('quiz', 'exam', 'practice', name='assessment_type_enum'),
            server_default='quiz',
            nullable=False
        ),
        sa.Column(
            'assessment_status',
            sa.Enum('draft', 'published', 'active', 'closed', 'archived', name='assessment_status_enum'),
            server_default='draft',
            nullable=False
        ),
        sa.Column('assessment_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('assessment_start_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('assessment_end_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('assessment_total_marks', sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column('assessment_created_by', sa.UUID(), nullable=True),
        sa.Column('assessment_created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('assessment_updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['assessment_created_by'], ['tbl_users.user_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['assessment_subject_id'], ['tbl_subjects.subject_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('assessment_id')
    )
    op.create_index(op.f('ix_tbl_assessments_assessment_subject_id'), 'tbl_assessments', ['assessment_subject_id'], unique=False)
    op.create_index(op.f('ix_tbl_assessments_assessment_status'), 'tbl_assessments', ['assessment_status'], unique=False)
    op.create_index(op.f('ix_tbl_assessments_assessment_start_at'), 'tbl_assessments', ['assessment_start_at'], unique=False)
    op.create_index(op.f('ix_tbl_assessments_assessment_end_at'), 'tbl_assessments', ['assessment_end_at'], unique=False)

    # 2. Seed assessment permissions
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

    new_permissions = [
        ("assessment.create", "Create assessments"),
        ("assessment.read", "View assessments"),
        ("assessment.update", "Update assessments"),
        ("assessment.delete", "Archive or delete assessments"),
    ]

    conn = op.get_bind()
    existing_perms = conn.execute(text("SELECT permission_name, permission_id FROM tbl_permissions")).fetchall()
    existing_perms_map = {p[0]: p[1] for p in existing_perms}

    permission_ids_map = {}
    for name, desc in new_permissions:
        if name in existing_perms_map:
            permission_ids_map[name] = existing_perms_map[name]
        else:
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

    # 3. Map permissions to system roles
    roles = conn.execute(text("SELECT role_id, role_name FROM tbl_roles WHERE role_organization_id IS NULL")).fetchall()
    roles_map = {r[1]: r[0] for r in roles}

    role_perms_mapping = {
        "Owner": ["assessment.create", "assessment.read", "assessment.update", "assessment.delete"],
        "Admin": ["assessment.create", "assessment.read", "assessment.update", "assessment.delete"],
        "Teacher": ["assessment.create", "assessment.read", "assessment.update", "assessment.delete"],
        "Student": ["assessment.read"],
        "Parent": ["assessment.read"],
        "Staff": ["assessment.read"],
    }

    for role_name, perm_names in role_perms_mapping.items():
        role_id = roles_map.get(role_name)
        if not role_id:
            continue
        for pname in perm_names:
            pid = permission_ids_map.get(pname)
            if pid:
                exists = conn.execute(
                    text("SELECT 1 FROM tbl_role_permissions WHERE role_id = :r_id AND permission_id = :p_id"),
                    {"r_id": role_id, "p_id": pid}
                ).fetchone()
                if not exists:
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
    conn = op.get_bind()
    # Delete role-permission mappings for assessment permissions
    conn.execute(
        text("""
            DELETE FROM tbl_role_permissions 
            WHERE permission_id IN (
                SELECT permission_id FROM tbl_permissions 
                WHERE permission_name IN ('assessment.create', 'assessment.read', 'assessment.update', 'assessment.delete')
            )
        """)
    )
    conn.execute(text("DELETE FROM tbl_permissions WHERE permission_name IN ('assessment.create', 'assessment.read', 'assessment.update', 'assessment.delete')"))
    op.drop_table('tbl_assessments')
    op.execute("DROP TYPE IF EXISTS assessment_status_enum")
    op.execute("DROP TYPE IF EXISTS assessment_type_enum")
