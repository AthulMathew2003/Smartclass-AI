"""add_qp_draft_tables

Revision ID: 56ecf7acb3d4
Revises: f2b93d4e5a01
Create Date: 2026-10-21 18:21:59.890942+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '56ecf7acb3d4'
down_revision: Union[str, Sequence[str], None] = 'f2b93d4e5a01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Define Enum types
    if is_postgres:
        qp_draft_status_enum = postgresql.ENUM(
            'generating', 'ready', 'failed', 'converted',
            name='qp_draft_status_enum',
            create_type=False
        )
        qp_draft_status_enum.create(bind, checkfirst=True)
    else:
        qp_draft_status_enum = sa.Enum(
            'generating', 'ready', 'failed', 'converted',
            name='qp_draft_status_enum'
        )

    # 2. Create tbl_qp_drafts
    op.create_table(
        'tbl_qp_drafts',
        sa.Column('draft_id', sa.UUID(), nullable=False),
        sa.Column('draft_subject_id', sa.UUID(), nullable=False),
        sa.Column('draft_created_by', sa.UUID(), nullable=True),
        sa.Column('draft_title', sa.String(length=255), nullable=False),
        sa.Column('draft_description', sa.Text(), nullable=True),
        sa.Column('draft_status', qp_draft_status_enum, nullable=False),
        sa.Column('draft_config', sa.JSON(), nullable=False),
        sa.Column('draft_validation_result', sa.JSON(), nullable=True),
        sa.Column('draft_generation_error', sa.Text(), nullable=True),
        sa.Column('draft_converted_assessment_id', sa.UUID(), nullable=True),
        sa.Column('draft_created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('draft_updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['draft_converted_assessment_id'], ['tbl_assessments.assessment_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['draft_created_by'], ['tbl_users.user_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['draft_subject_id'], ['tbl_subjects.subject_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('draft_id')
    )
    op.create_index(op.f('ix_tbl_qp_drafts_draft_status'), 'tbl_qp_drafts', ['draft_status'], unique=False)
    op.create_index(op.f('ix_tbl_qp_drafts_draft_subject_id'), 'tbl_qp_drafts', ['draft_subject_id'], unique=False)

    # 3. Create tbl_qp_draft_questions
    op.create_table(
        'tbl_qp_draft_questions',
        sa.Column('dq_id', sa.UUID(), nullable=False),
        sa.Column('dq_draft_id', sa.UUID(), nullable=False),
        sa.Column('dq_order', sa.Integer(), nullable=False),
        sa.Column('dq_question_type', sa.String(length=32), nullable=False),
        sa.Column('dq_question_text', sa.Text(), nullable=False),
        sa.Column('dq_marks', sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column('dq_difficulty', sa.String(length=16), nullable=False),
        sa.Column('dq_options', sa.JSON(), nullable=True),
        sa.Column('dq_expected_answer', sa.Text(), nullable=True),
        sa.Column('dq_rubric', sa.Text(), nullable=True),
        sa.Column('dq_explanation', sa.Text(), nullable=True),
        sa.Column('dq_source_material_ids', sa.JSON(), nullable=False),
        sa.Column('dq_source_chunks', sa.JSON(), nullable=True),
        sa.Column('dq_generation_metadata', sa.JSON(), nullable=True),
        sa.Column('dq_is_flagged', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('dq_created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('dq_updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['dq_draft_id'], ['tbl_qp_drafts.draft_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('dq_id')
    )
    op.create_index(op.f('ix_tbl_qp_draft_questions_dq_draft_id'), 'tbl_qp_draft_questions', ['dq_draft_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    op.drop_index(op.f('ix_tbl_qp_draft_questions_dq_draft_id'), table_name='tbl_qp_draft_questions')
    op.drop_table('tbl_qp_draft_questions')
    op.drop_index(op.f('ix_tbl_qp_drafts_draft_subject_id'), table_name='tbl_qp_drafts')
    op.drop_index(op.f('ix_tbl_qp_drafts_draft_status'), table_name='tbl_qp_drafts')
    op.drop_table('tbl_qp_drafts')

    if is_postgres:
        op.execute("DROP TYPE IF EXISTS qp_draft_status_enum")
