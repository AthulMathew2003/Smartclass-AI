"""add_ai_grading_columns

Revision ID: f2b93d4e5a01
Revises: e38f921ab452
Create Date: 2026-10-21 22:30:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f2b93d4e5a01'
down_revision: Union[str, Sequence[str], None] = 'e38f921ab452'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Define Enum types
    if is_postgres:
        grading_source_enum = postgresql.ENUM(
            'objective', 'ai', 'teacher',
            name='assessment_grading_source_enum',
            create_type=False
        )
        grading_source_enum.create(bind, checkfirst=True)

        ai_eval_status_enum = postgresql.ENUM(
            'none', 'completed', 'review_required', 'failed', 'skipped',
            name='assessment_ai_evaluation_status_enum',
            create_type=False
        )
        ai_eval_status_enum.create(bind, checkfirst=True)
    else:
        grading_source_enum = sa.Enum('objective', 'ai', 'teacher', name='assessment_grading_source_enum')
        ai_eval_status_enum = sa.Enum('none', 'completed', 'review_required', 'failed', 'skipped', name='assessment_ai_evaluation_status_enum')

    # 2. Add question criteria columns to tbl_questions
    op.add_column('tbl_questions', sa.Column('question_expected_answer', sa.Text(), nullable=True))
    op.add_column('tbl_questions', sa.Column('question_rubric', sa.Text(), nullable=True))

    # 3. Add AI semantic grading and teacher review columns to tbl_assessment_result_questions
    op.add_column(
        'tbl_assessment_result_questions',
        sa.Column('result_question_grading_source', grading_source_enum, nullable=False, server_default=sa.text("'objective'"))
    )
    op.add_column(
        'tbl_assessment_result_questions',
        sa.Column('result_question_ai_evaluation_status', ai_eval_status_enum, nullable=False, server_default=sa.text("'none'"))
    )
    op.add_column(
        'tbl_assessment_result_questions',
        sa.Column('result_question_ai_suggested_marks', sa.Numeric(precision=7, scale=2), nullable=True)
    )
    op.add_column(
        'tbl_assessment_result_questions',
        sa.Column('result_question_ai_confidence', sa.Numeric(precision=3, scale=2), nullable=True)
    )
    op.add_column(
        'tbl_assessment_result_questions',
        sa.Column('result_question_ai_explanation', sa.Text(), nullable=True)
    )
    op.add_column(
        'tbl_assessment_result_questions',
        sa.Column('result_question_ai_evaluation', sa.JSON(), nullable=True)
    )
    op.add_column(
        'tbl_assessment_result_questions',
        sa.Column('result_question_teacher_reviewed', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    op.drop_column('tbl_assessment_result_questions', 'result_question_teacher_reviewed')
    op.drop_column('tbl_assessment_result_questions', 'result_question_ai_evaluation')
    op.drop_column('tbl_assessment_result_questions', 'result_question_ai_explanation')
    op.drop_column('tbl_assessment_result_questions', 'result_question_ai_confidence')
    op.drop_column('tbl_assessment_result_questions', 'result_question_ai_suggested_marks')
    op.drop_column('tbl_assessment_result_questions', 'result_question_ai_evaluation_status')
    op.drop_column('tbl_assessment_result_questions', 'result_question_grading_source')

    op.drop_column('tbl_questions', 'question_rubric')
    op.drop_column('tbl_questions', 'question_expected_answer')

    if is_postgres:
        op.execute("DROP TYPE IF EXISTS assessment_ai_evaluation_status_enum")
        op.execute("DROP TYPE IF EXISTS assessment_grading_source_enum")
