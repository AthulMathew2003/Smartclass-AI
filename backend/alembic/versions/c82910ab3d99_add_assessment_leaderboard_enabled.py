"""add_assessment_leaderboard_enabled

Revision ID: c82910ab3d99
Revises: b1f4a92c3d85
Create Date: 2026-09-22 15:30:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c82910ab3d99'
down_revision: Union[str, Sequence[str], None] = 'b1f4a92c3d85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'tbl_assessments',
        sa.Column('assessment_leaderboard_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )
    op.create_index(
        'ix_tbl_assessments_assessment_leaderboard_enabled',
        'tbl_assessments',
        ['assessment_leaderboard_enabled']
    )


def downgrade() -> None:
    op.drop_index('ix_tbl_assessments_assessment_leaderboard_enabled', table_name='tbl_assessments')
    op.drop_column('tbl_assessments', 'assessment_leaderboard_enabled')
