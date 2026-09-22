"""add_assessment_questions_and_options

Revision ID: f82910ab3c41
Revises: e71829a3b901
Create Date: 2026-08-18 09:37:00.000000+00:00

"""
from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text, table, column


# revision identifiers, used by Alembic.
revision: str = 'f82910ab3c41'
down_revision: Union[str, Sequence[str], None] = 'e71829a3b901'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create tbl_assessment_questions, tbl_question_options, and seed permissions."""
    # 1. Create tbl_assessment_questions
    op.create_table(
        'tbl_assessment_questions',
        sa.Column('question_id', sa.UUID(), nullable=False),
        sa.Column('question_assessment_id', sa.UUID(), nullable=False),
        sa.Column(
            'question_type',
            sa.Enum('mcq_single', 'mcq_multiple', 'true_false', 'short_answer', name='question_type_enum'),
            nullable=False
        ),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('question_marks', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('question_order', sa.Integer(), nullable=False),
        sa.Column('question_explanation', sa.Text(), nullable=True),
        sa.Column(
            'question_status',
            sa.Enum('active', 'archived', name='question_status_enum'),
            server_default='active',
            nullable=False
        ),
        sa.Column('question_created_by', sa.UUID(), nullable=True),
        sa.Column('question_created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('question_updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['question_assessment_id'], ['tbl_assessments.assessment_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['question_created_by'], ['tbl_users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('question_id'),
        sa.UniqueConstraint('question_assessment_id', 'question_order', name='uq_assessment_question_order')
    )
    op.create_index(op.f('ix_tbl_assessment_questions_question_assessment_id'), 'tbl_assessment_questions', ['question_assessment_id'], unique=False)
    op.create_index(op.f('ix_tbl_assessment_questions_question_status'), 'tbl_assessment_questions', ['question_status'], unique=False)
    op.create_index(op.f('ix_tbl_assessment_questions_question_order'), 'tbl_assessment_questions', ['question_order'], unique=False)

    # 2. Create tbl_question_options
    op.create_table(
        'tbl_question_options',
        sa.Column('option_id', sa.UUID(), nullable=False),
        sa.Column('option_question_id', sa.UUID(), nullable=False),
        sa.Column('option_text', sa.Text(), nullable=False),
        sa.Column('option_order', sa.Integer(), nullable=False),
        sa.Column('option_is_correct', sa.Boolean(), server_default='false', nullable=False),
        sa.ForeignKeyConstraint(['option_question_id'], ['tbl_assessment_questions.question_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('option_id'),
        sa.UniqueConstraint('option_question_id', 'option_order', name='uq_question_option_order')
    )
    op.create_index(op.f('ix_tbl_question_options_option_question_id'), 'tbl_question_options', ['option_question_id'], unique=False)

    # 3. Seed question permissions
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
        ("question.create", "Create assessment questions"),
        ("question.read", "View assessment questions"),
        ("question.update", "Update assessment questions"),
        ("question.delete", "Archive or delete assessment questions"),
        ("question.reorder", "Reorder assessment questions"),
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
        "Owner": ["question.create", "question.read", "question.update", "question.delete", "question.reorder"],
        "Admin": ["question.create", "question.read", "question.update", "question.delete", "question.reorder"],
        "Teacher": ["question.create", "question.read", "question.update", "question.delete", "question.reorder"],
        "Student": ["question.read"],
        "Parent": ["question.read"],
        "Staff": ["question.read"],
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
    conn.execute(
        text("""
            DELETE FROM tbl_role_permissions 
            WHERE permission_id IN (
                SELECT permission_id FROM tbl_permissions 
                WHERE permission_name IN ('question.create', 'question.read', 'question.update', 'question.delete', 'question.reorder')
            )
        """)
    )
    conn.execute(text("DELETE FROM tbl_permissions WHERE permission_name IN ('question.create', 'question.read', 'question.update', 'question.delete', 'question.reorder')"))
    op.drop_table('tbl_question_options')
    op.drop_table('tbl_assessment_questions')
    op.execute("DROP TYPE IF EXISTS question_status_enum")
    op.execute("DROP TYPE IF EXISTS question_type_enum")
