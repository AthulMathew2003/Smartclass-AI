"""add_assignments_and_submissions

Revision ID: 92379ec57d82
Revises: 1c5e47569ffa
Create Date: 2026-08-14 09:33:58.377805+00:00

"""
from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text, table, column


# revision identifiers, used by Alembic.
revision: str = '92379ec57d82'
down_revision: Union[str, Sequence[str], None] = '1c5e47569ffa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create tbl_assignments
    op.create_table(
        'tbl_assignments',
        sa.Column('assignment_id', sa.UUID(), nullable=False),
        sa.Column('assignment_subject_id', sa.UUID(), nullable=False),
        sa.Column('assignment_title', sa.String(length=255), nullable=False),
        sa.Column('assignment_description', sa.Text(), nullable=True),
        sa.Column(
            'assignment_status',
            sa.Enum('draft', 'published', 'closed', 'archived', name='assignment_status_enum'),
            server_default='draft',
            nullable=False
        ),
        sa.Column('assignment_due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('assignment_created_by', sa.UUID(), nullable=True),
        sa.Column('assignment_created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('assignment_updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['assignment_created_by'], ['tbl_users.user_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['assignment_subject_id'], ['tbl_subjects.subject_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('assignment_id')
    )
    op.create_index(op.f('ix_tbl_assignments_assignment_subject_id'), 'tbl_assignments', ['assignment_subject_id'], unique=False)
    op.create_index(op.f('ix_tbl_assignments_assignment_status'), 'tbl_assignments', ['assignment_status'], unique=False)
    op.create_index(op.f('ix_tbl_assignments_assignment_due_at'), 'tbl_assignments', ['assignment_due_at'], unique=False)

    # 2. Create tbl_assignment_submissions
    op.create_table(
        'tbl_assignment_submissions',
        sa.Column('submission_id', sa.UUID(), nullable=False),
        sa.Column('submission_assignment_id', sa.UUID(), nullable=False),
        sa.Column('submission_student_id', sa.UUID(), nullable=False),
        sa.Column(
            'submission_status',
            sa.Enum('draft', 'submitted', 'late', 'graded', 'returned', name='submission_status_enum'),
            server_default='draft',
            nullable=False
        ),
        sa.Column('submission_submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('submission_grade', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('submission_feedback', sa.Text(), nullable=True),
        sa.Column('submission_graded_by', sa.UUID(), nullable=True),
        sa.Column('submission_graded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('submission_created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('submission_updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['submission_assignment_id'], ['tbl_assignments.assignment_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['submission_student_id'], ['tbl_users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['submission_graded_by'], ['tbl_users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('submission_id'),
        sa.UniqueConstraint('submission_assignment_id', 'submission_student_id', name='uq_assignment_student_submission')
    )
    op.create_index(op.f('ix_tbl_assignment_submissions_submission_assignment_id'), 'tbl_assignment_submissions', ['submission_assignment_id'], unique=False)
    op.create_index(op.f('ix_tbl_assignment_submissions_submission_student_id'), 'tbl_assignment_submissions', ['submission_student_id'], unique=False)
    op.create_index(op.f('ix_tbl_assignment_submissions_submission_status'), 'tbl_assignment_submissions', ['submission_status'], unique=False)

    # 3. Seed assignment permissions if not already present
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
        ("assignment.read", "View assignments"),
        ("assignment.delete", "Archive or delete assignments"),
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

    # 4. Map permissions to system roles
    roles = conn.execute(text("SELECT role_id, role_name FROM tbl_roles WHERE role_organization_id IS NULL")).fetchall()
    roles_map = {r[1]: r[0] for r in roles}

    role_perms_mapping = {
        "Owner": ["assignment.read", "assignment.delete"],
        "Admin": ["assignment.read", "assignment.delete"],
        "Teacher": ["assignment.read", "assignment.delete"],
        "Student": ["assignment.read"],
        "Parent": ["assignment.read"],
        "Staff": ["assignment.read"],
    }

    for role_name, perm_names in role_perms_mapping.items():
        role_id = roles_map.get(role_name)
        if not role_id:
            continue
        for pname in perm_names:
            pid = permission_ids_map.get(pname)
            if pid:
                # Check if mapping already exists
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
    conn.execute(text("DELETE FROM tbl_permissions WHERE permission_name IN ('assignment.read', 'assignment.delete')"))
    op.drop_table('tbl_assignment_submissions')
    op.execute("DROP TYPE submission_status_enum")
    op.drop_table('tbl_assignments')
    op.execute("DROP TYPE assignment_status_enum")
