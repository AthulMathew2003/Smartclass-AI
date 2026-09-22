"""add_attempt_expires_at

Revision ID: a9f3b2c1d874
Revises: 68b209a41f01
Create Date: 2026-09-22 11:30:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9f3b2c1d874'
down_revision: Union[str, Sequence[str], None] = '68b209a41f01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add attempt_expires_at column (nullable — NULL means no time limit)
    op.add_column(
        'tbl_assessment_attempts',
        sa.Column('attempt_expires_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index(
        op.f('ix_tbl_assessment_attempts_attempt_expires_at'),
        'tbl_assessment_attempts',
        ['attempt_expires_at'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_tbl_assessment_attempts_attempt_expires_at'),
        table_name='tbl_assessment_attempts'
    )
    op.drop_column('tbl_assessment_attempts', 'attempt_expires_at')
