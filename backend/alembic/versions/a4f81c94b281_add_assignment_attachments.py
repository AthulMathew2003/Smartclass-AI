"""add_assignment_attachments

Revision ID: a4f81c94b281
Revises: 92379ec57d82
Create Date: 2026-08-14 10:00:00.000000+00:00

"""
from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4f81c94b281'
down_revision: Union[str, Sequence[str], None] = '92379ec57d82'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add tbl_assignment_attachments."""
    op.create_table(
        'tbl_assignment_attachments',
        sa.Column('attachment_id', sa.UUID(), nullable=False),
        sa.Column('attachment_assignment_id', sa.UUID(), nullable=False),
        sa.Column('attachment_s3_key', sa.Text(), nullable=False),
        sa.Column('attachment_original_filename', sa.String(length=255), nullable=False),
        sa.Column('attachment_content_type', sa.String(length=100), nullable=False),
        sa.Column('attachment_size', sa.BigInteger(), nullable=False),
        sa.Column('attachment_created_by', sa.UUID(), nullable=True),
        sa.Column('attachment_created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['attachment_assignment_id'],
            ['tbl_assignments.assignment_id'],
            name=op.f('fk_tbl_assignment_attachments_attachment_assignment_id_tbl_assignments'),
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['attachment_created_by'],
            ['tbl_users.user_id'],
            name=op.f('fk_tbl_assignment_attachments_attachment_created_by_tbl_users'),
            ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('attachment_id', name=op.f('pk_tbl_assignment_attachments'))
    )
    op.create_index(
        op.f('ix_tbl_assignment_attachments_attachment_assignment_id'),
        'tbl_assignment_attachments',
        ['attachment_assignment_id'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_tbl_assignment_attachments_attachment_assignment_id'),
        table_name='tbl_assignment_attachments'
    )
    op.drop_table('tbl_assignment_attachments')
