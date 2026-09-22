"""add_assessment_attempts_and_answers

Revision ID: 68b209a41f01
Revises: b819f2910c51
Create Date: 2026-08-22 10:00:00.000000+00:00

"""
from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import text, table, column


# revision identifiers, used by Alembic.
revision: str = '68b209a41f01'
down_revision: Union[str, Sequence[str], None] = 'b819f2910c51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # Create attempt_status_enum
    if is_postgres:
        attempt_status_enum = postgresql.ENUM('in_progress', 'submitted', 'expired', name='attempt_status_enum', create_type=False)
        attempt_status_enum.create(bind, checkfirst=True)
    else:
        attempt_status_enum = sa.Enum('in_progress', 'submitted', 'expired', name='attempt_status_enum')

    # Create tbl_assessment_attempts
    op.create_table(
        'tbl_assessment_attempts',
        sa.Column('attempt_id', sa.UUID(), nullable=False),
        sa.Column('attempt_assessment_id', sa.UUID(), nullable=False),
        sa.Column('attempt_student_id', sa.UUID(), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('attempt_status', attempt_status_enum, nullable=False, server_default=sa.text("'in_progress'")),
        sa.Column('attempt_question_order', sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column('attempt_started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('attempt_submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempt_created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('attempt_updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['attempt_assessment_id'], ['tbl_assessments.assessment_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['attempt_student_id'], ['tbl_users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('attempt_id'),
        sa.UniqueConstraint('attempt_assessment_id', 'attempt_student_id', 'attempt_number', name='uq_assessment_student_attempt_number')
    )
    op.create_index(op.f('ix_tbl_assessment_attempts_attempt_assessment_id'), 'tbl_assessment_attempts', ['attempt_assessment_id'], unique=False)
    op.create_index(op.f('ix_tbl_assessment_attempts_attempt_student_id'), 'tbl_assessment_attempts', ['attempt_student_id'], unique=False)
    op.create_index(op.f('ix_tbl_assessment_attempts_attempt_status'), 'tbl_assessment_attempts', ['attempt_status'], unique=False)

    # Create tbl_assessment_attempt_answers
    op.create_table(
        'tbl_assessment_attempt_answers',
        sa.Column('attempt_answer_id', sa.UUID(), nullable=False),
        sa.Column('attempt_answer_attempt_id', sa.UUID(), nullable=False),
        sa.Column('attempt_answer_question_id', sa.UUID(), nullable=False),
        sa.Column('attempt_answer_value', sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('attempt_answer_created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('attempt_answer_updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['attempt_answer_attempt_id'], ['tbl_assessment_attempts.attempt_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['attempt_answer_question_id'], ['tbl_assessment_questions.assessment_question_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('attempt_answer_id'),
        sa.UniqueConstraint('attempt_answer_attempt_id', 'attempt_answer_question_id', name='uq_attempt_answer_question')
    )
    op.create_index(op.f('ix_tbl_assessment_attempt_answers_attempt_id'), 'tbl_assessment_attempt_answers', ['attempt_answer_attempt_id'], unique=False)
    op.create_index(op.f('ix_tbl_assessment_attempt_answers_question_id'), 'tbl_assessment_attempt_answers', ['attempt_answer_question_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    op.drop_table('tbl_assessment_attempt_answers')
    op.drop_table('tbl_assessment_attempts')

    if is_postgres:
        bind.execute(text("DROP TYPE IF EXISTS attempt_status_enum"))
