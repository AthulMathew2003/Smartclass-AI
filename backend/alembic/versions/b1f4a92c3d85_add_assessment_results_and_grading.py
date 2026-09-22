"""add_assessment_results_and_grading

Revision ID: b1f4a92c3d85
Revises: a9f3b2c1d874
Create Date: 2026-09-22 12:30:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b1f4a92c3d85'
down_revision: Union[str, Sequence[str], None] = 'a9f3b2c1d874'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Define Enum types
    if is_postgres:
        result_status_enum = postgresql.ENUM(
            'pending_manual_grading', 'completed',
            name='assessment_result_status_enum',
            create_type=False
        )
        result_status_enum.create(bind, checkfirst=True)

        grading_status_enum = postgresql.ENUM(
            'pending', 'graded',
            name='assessment_grading_status_enum',
            create_type=False
        )
        grading_status_enum.create(bind, checkfirst=True)

        correctness_status_enum = postgresql.ENUM(
            'correct', 'incorrect', 'unanswered', 'pending',
            name='assessment_correctness_status_enum',
            create_type=False
        )
        correctness_status_enum.create(bind, checkfirst=True)
    else:
        result_status_enum = sa.Enum('pending_manual_grading', 'completed', name='assessment_result_status_enum')
        grading_status_enum = sa.Enum('pending', 'graded', name='assessment_grading_status_enum')
        correctness_status_enum = sa.Enum('correct', 'incorrect', 'unanswered', 'pending', name='assessment_correctness_status_enum')

    # 2. Create tbl_assessment_results
    op.create_table(
        'tbl_assessment_results',
        sa.Column('result_id', sa.UUID(), primary_key=True),
        sa.Column('result_attempt_id', sa.UUID(), sa.ForeignKey('tbl_assessment_attempts.attempt_id', ondelete='CASCADE'), nullable=False),
        sa.Column('result_assessment_id', sa.UUID(), sa.ForeignKey('tbl_assessments.assessment_id', ondelete='CASCADE'), nullable=False),
        sa.Column('result_student_id', sa.UUID(), sa.ForeignKey('tbl_users.user_id', ondelete='CASCADE'), nullable=False),
        sa.Column('result_total_marks', sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column('result_obtained_marks', sa.Numeric(precision=7, scale=2), nullable=False, server_default='0.00'),
        sa.Column('result_percentage', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.00'),
        sa.Column('result_passed', sa.Boolean(), nullable=True),
        sa.Column('result_status', result_status_enum, nullable=False, server_default=sa.text("'completed'")),
        sa.Column('result_correct_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('result_incorrect_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('result_unanswered_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('result_pending_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('result_graded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result_created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('result_updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('result_attempt_id', name='uq_assessment_result_attempt')
    )

    op.create_index(op.f('ix_tbl_assessment_results_result_attempt_id'), 'tbl_assessment_results', ['result_attempt_id'], unique=True)
    op.create_index(op.f('ix_tbl_assessment_results_result_assessment_id'), 'tbl_assessment_results', ['result_assessment_id'], unique=False)
    op.create_index(op.f('ix_tbl_assessment_results_result_student_id'), 'tbl_assessment_results', ['result_student_id'], unique=False)
    op.create_index(op.f('ix_tbl_assessment_results_result_status'), 'tbl_assessment_results', ['result_status'], unique=False)

    # 3. Create tbl_assessment_result_questions
    op.create_table(
        'tbl_assessment_result_questions',
        sa.Column('result_question_id', sa.UUID(), primary_key=True),
        sa.Column('result_question_result_id', sa.UUID(), sa.ForeignKey('tbl_assessment_results.result_id', ondelete='CASCADE'), nullable=False),
        sa.Column('result_question_assessment_question_id', sa.UUID(), sa.ForeignKey('tbl_assessment_questions.assessment_question_id', ondelete='CASCADE'), nullable=False),
        sa.Column('result_question_answer_value', sa.JSON(), nullable=True),
        sa.Column('result_question_marks_available', sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column('result_question_marks_awarded', sa.Numeric(precision=7, scale=2), nullable=False, server_default='0.00'),
        sa.Column('result_question_correctness', correctness_status_enum, nullable=False, server_default=sa.text("'pending'")),
        sa.Column('result_question_grading_status', grading_status_enum, nullable=False, server_default=sa.text("'pending'")),
        sa.Column('result_question_feedback', sa.Text(), nullable=True),
        sa.Column('result_question_graded_by', sa.UUID(), sa.ForeignKey('tbl_users.user_id', ondelete='SET NULL'), nullable=True),
        sa.Column('result_question_graded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result_question_created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('result_question_updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('result_question_result_id', 'result_question_assessment_question_id', name='uq_result_assessment_question')
    )

    op.create_index(op.f('ix_tbl_assessment_result_questions_result_id'), 'tbl_assessment_result_questions', ['result_question_result_id'], unique=False)
    op.create_index(op.f('ix_tbl_assessment_result_questions_question_id'), 'tbl_assessment_result_questions', ['result_question_assessment_question_id'], unique=False)


def downgrade() -> None:
    op.drop_table('tbl_assessment_result_questions')
    op.drop_table('tbl_assessment_results')

    sa.Enum(name='assessment_correctness_status_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='assessment_grading_status_enum').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='assessment_result_status_enum').drop(op.get_bind(), checkfirst=True)
