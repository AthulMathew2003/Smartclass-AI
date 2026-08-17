"""remove_submission_versioning

Revision ID: d5e81c029fa1
Revises: 67b49258031f
Create Date: 2026-08-17 17:00:00.000000+00:00

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision: str = 'd5e81c029fa1'
down_revision: Union[str, Sequence[str], None] = '67b49258031f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: remove versioning, link submission attachments directly to submission."""
    # 1. Drop tbl_submission_attachments and recreate with attachment_submission_id
    op.execute("DROP TABLE IF EXISTS tbl_submission_attachments CASCADE;")

    op.create_table(
        'tbl_submission_attachments',
        sa.Column('attachment_id', sa.UUID(), nullable=False),
        sa.Column('attachment_submission_id', sa.UUID(), nullable=False),
        sa.Column('attachment_s3_key', sa.Text(), nullable=False),
        sa.Column('attachment_original_filename', sa.String(length=255), nullable=False),
        sa.Column('attachment_content_type', sa.String(length=100), nullable=False),
        sa.Column('attachment_size', sa.BigInteger(), nullable=False),
        sa.Column('attachment_created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ['attachment_submission_id'],
            ['tbl_assignment_submissions.submission_id'],
            name=op.f('fk_tbl_submission_attachments_attachment_submission_id_tbl_assignment_submissions'),
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('attachment_id', name=op.f('pk_tbl_submission_attachments'))
    )
    op.create_index(
        op.f('ix_tbl_submission_attachments_attachment_submission_id'),
        'tbl_submission_attachments',
        ['attachment_submission_id'],
        unique=False
    )

    # 2. Drop tbl_submission_versions and its enum if exists
    op.execute("DROP TABLE IF EXISTS tbl_submission_versions CASCADE;")
    op.execute("DROP TYPE IF EXISTS submission_version_status_enum CASCADE;")

    # 3. Drop submission_current_version column from tbl_assignment_submissions if exists
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'tbl_assignment_submissions' 
                AND column_name = 'submission_current_version'
            ) THEN
                ALTER TABLE tbl_assignment_submissions DROP COLUMN submission_current_version;
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        'tbl_assignment_submissions',
        sa.Column('submission_current_version', sa.Integer(), server_default='1', nullable=False)
    )
