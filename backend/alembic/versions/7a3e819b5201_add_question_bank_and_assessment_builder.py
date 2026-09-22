"""add_question_bank_and_assessment_builder

Revision ID: 7a3e819b5201
Revises: f82910ab3c41
Create Date: 2026-08-18 10:00:00.000000+00:00

"""
from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text, table, column


# revision identifiers, used by Alembic.
revision: str = '7a3e819b5201'
down_revision: Union[str, Sequence[str], None] = 'f82910ab3c41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add Question Bank, assessment builder columns, snapshot questions, and seed assessment.publish permission."""
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Update tbl_assessments with new columns
    op.add_column('tbl_assessments', sa.Column('assessment_passing_marks', sa.Numeric(precision=7, scale=2), nullable=True))
    op.add_column('tbl_assessments', sa.Column('assessment_attempt_limit', sa.Integer(), nullable=False, server_default=sa.text('1')))
    op.add_column('tbl_assessments', sa.Column('assessment_randomize_questions', sa.Boolean(), nullable=False, server_default=sa.text('false')))

    # 2. Recreate / restructure question tables to support Subject Question Bank & Assessment Snapshots
    op.drop_table('tbl_question_options')
    op.drop_table('tbl_assessment_questions')

    from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
    question_type_enum = PG_ENUM('mcq_single', 'mcq_multiple', 'true_false', 'short_answer', name='question_type_enum', create_type=False)
    question_status_enum = PG_ENUM('active', 'archived', name='question_status_enum', create_type=False)

    # Create tbl_questions (Subject Question Bank)
    op.create_table(
        'tbl_questions',
        sa.Column('question_id', sa.UUID(), nullable=False),
        sa.Column('question_subject_id', sa.UUID(), nullable=False),
        sa.Column('question_type', question_type_enum, nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('question_default_marks', sa.Numeric(precision=7, scale=2), nullable=False, server_default=sa.text('1.00')),
        sa.Column('question_explanation', sa.Text(), nullable=True),
        sa.Column('question_status', question_status_enum, nullable=False, server_default=sa.text("'active'")),
        sa.Column('question_created_by', sa.UUID(), nullable=True),
        sa.Column('question_created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('question_updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['question_subject_id'], ['tbl_subjects.subject_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['question_created_by'], ['tbl_users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('question_id')
    )
    op.create_index(op.f('ix_tbl_questions_question_subject_id'), 'tbl_questions', ['question_subject_id'], unique=False)
    op.create_index(op.f('ix_tbl_questions_question_status'), 'tbl_questions', ['question_status'], unique=False)

    # Create tbl_question_options
    op.create_table(
        'tbl_question_options',
        sa.Column('option_id', sa.UUID(), nullable=False),
        sa.Column('option_question_id', sa.UUID(), nullable=False),
        sa.Column('option_text', sa.Text(), nullable=False),
        sa.Column('option_order', sa.Integer(), nullable=False),
        sa.Column('option_is_correct', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.ForeignKeyConstraint(['option_question_id'], ['tbl_questions.question_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('option_id'),
        sa.UniqueConstraint('option_question_id', 'option_order', name='uq_question_option_order')
    )
    op.create_index(op.f('ix_tbl_question_options_option_question_id'), 'tbl_question_options', ['option_question_id'], unique=False)

    # Create tbl_assessment_questions (with Question Snapshot)
    op.create_table(
        'tbl_assessment_questions',
        sa.Column('assessment_question_id', sa.UUID(), nullable=False),
        sa.Column('assessment_question_assessment_id', sa.UUID(), nullable=False),
        sa.Column('assessment_question_question_id', sa.UUID(), nullable=True),
        sa.Column('assessment_question_order', sa.Integer(), nullable=False),
        sa.Column('assessment_question_marks', sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column('assessment_question_snapshot', sa.JSON(), nullable=False),
        sa.Column('assessment_question_created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['assessment_question_assessment_id'], ['tbl_assessments.assessment_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assessment_question_question_id'], ['tbl_questions.question_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('assessment_question_id'),
        sa.UniqueConstraint('assessment_question_assessment_id', 'assessment_question_order', name='uq_assessment_question_order'),
        sa.UniqueConstraint('assessment_question_assessment_id', 'assessment_question_question_id', name='uq_assessment_question_unique_bank_q')
    )
    op.create_index(op.f('ix_tbl_assessment_questions_assessment_id'), 'tbl_assessment_questions', ['assessment_question_assessment_id'], unique=False)
    op.create_index(op.f('ix_tbl_assessment_questions_question_id'), 'tbl_assessment_questions', ['assessment_question_question_id'], unique=False)

    # 3. Seed assessment.publish permission
    permissions_table = table(
        'tbl_permissions',
        column('permission_id', sa.UUID),
        column('permission_name', sa.String),
        column('permission_description', sa.String),
        column('permission_created_at', sa.DateTime(timezone=True)),
        column('permission_updated_at', sa.DateTime(timezone=True))
    )

    perm_uuid = uuid.uuid4()
    now_utc = datetime.now(timezone.utc)
    op.bulk_insert(
        permissions_table,
        [
            {
                'permission_id': perm_uuid,
                'permission_name': 'assessment.publish',
                'permission_description': 'Publish assessments',
                'permission_created_at': now_utc,
                'permission_updated_at': now_utc
            }
        ]
    )

    # Map assessment.publish to Owner, Admin, Teacher roles
    roles = ['Owner', 'Admin', 'Teacher']
    for role_name in roles:
        bind.execute(
            text("""
                INSERT INTO tbl_role_permissions (role_permission_id, role_id, permission_id, role_permission_created_at)
                SELECT :rp_id, r.role_id, p.permission_id, NOW()
                FROM tbl_roles r, tbl_permissions p
                WHERE r.role_name = :role_name
                  AND r.role_organization_id IS NULL
                  AND p.permission_name = 'assessment.publish'
                ON CONFLICT DO NOTHING
            """),
            {
                "rp_id": str(uuid.uuid4()),
                "role_name": role_name
            }
        )


def downgrade() -> None:
    """Downgrade schema: drop tbl_questions, revert tbl_assessment_questions, and remove columns."""
    op.drop_table('tbl_assessment_questions')
    op.drop_table('tbl_question_options')
    op.drop_table('tbl_questions')

    op.drop_column('tbl_assessments', 'assessment_randomize_questions')
    op.drop_column('tbl_assessments', 'assessment_attempt_limit')
    op.drop_column('tbl_assessments', 'assessment_passing_marks')

    bind = op.get_bind()
    bind.execute(
        text("DELETE FROM tbl_role_permissions WHERE permission_id IN (SELECT permission_id FROM tbl_permissions WHERE permission_name = 'assessment.publish')")
    )
    bind.execute(
        text("DELETE FROM tbl_permissions WHERE permission_name = 'assessment.publish'")
    )
