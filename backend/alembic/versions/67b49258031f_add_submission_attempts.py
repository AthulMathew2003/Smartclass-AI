"""add_submission_versions_and_attachments

Revision ID: 67b49258031f
Revises: a4f81c94b281
Create Date: 2026-08-17 07:12:15.188350+00:00

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision: str = '67b49258031f'
down_revision: Union[str, Sequence[str], None] = 'a4f81c94b281'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add submission versions and submission attachments."""
    # 1. Add submission_current_version to tbl_assignment_submissions if not exists
    op.add_column(
        'tbl_assignment_submissions',
        sa.Column('submission_current_version', sa.Integer(), server_default='1', nullable=False)
    )

    # 2. Create tbl_submission_versions
    op.create_table(
        'tbl_submission_versions',
        sa.Column('version_id', sa.UUID(), nullable=False),
        sa.Column('version_submission_id', sa.UUID(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column(
            'version_status',
            sa.Enum('draft', 'submitted', 'late', 'graded', 'returned', name='submission_version_status_enum'),
            server_default='submitted',
            nullable=False
        ),
        sa.Column('version_submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version_grade', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('version_feedback', sa.Text(), nullable=True),
        sa.Column('version_graded_by', sa.UUID(), nullable=True),
        sa.Column('version_graded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version_created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ['version_submission_id'],
            ['tbl_assignment_submissions.submission_id'],
            name=op.f('fk_tbl_submission_versions_version_submission_id_tbl_assignment_submissions'),
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['version_graded_by'],
            ['tbl_users.user_id'],
            name=op.f('fk_tbl_submission_versions_version_graded_by_tbl_users'),
            ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('version_id', name=op.f('pk_tbl_submission_versions')),
        sa.UniqueConstraint('version_submission_id', 'version_number', name='uq_submission_version_number')
    )
    op.create_index(
        op.f('ix_tbl_submission_versions_version_submission_id'),
        'tbl_submission_versions',
        ['version_submission_id'],
        unique=False
    )
    op.create_index(
        op.f('ix_tbl_submission_versions_version_status'),
        'tbl_submission_versions',
        ['version_status'],
        unique=False
    )

    # 3. Create tbl_submission_attachments
    op.create_table(
        'tbl_submission_attachments',
        sa.Column('attachment_id', sa.UUID(), nullable=False),
        sa.Column('attachment_version_id', sa.UUID(), nullable=False),
        sa.Column('attachment_s3_key', sa.Text(), nullable=False),
        sa.Column('attachment_original_filename', sa.String(length=255), nullable=False),
        sa.Column('attachment_content_type', sa.String(length=100), nullable=False),
        sa.Column('attachment_size', sa.BigInteger(), nullable=False),
        sa.Column('attachment_created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ['attachment_version_id'],
            ['tbl_submission_versions.version_id'],
            name=op.f('fk_tbl_submission_attachments_attachment_version_id_tbl_submission_versions'),
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('attachment_id', name=op.f('pk_tbl_submission_attachments'))
    )
    op.create_index(
        op.f('ix_tbl_submission_attachments_attachment_version_id'),
        'tbl_submission_attachments',
        ['attachment_version_id'],
        unique=False
    )

    # 4. Migrate existing submissions into tbl_submission_versions as version 1
    conn = op.get_bind()
    existing_subs = conn.execute(
        text("SELECT submission_id, submission_status, submission_submitted_at, submission_grade, submission_feedback, submission_graded_by, submission_graded_at, submission_created_at FROM tbl_assignment_submissions")
    ).fetchall()

    for s in existing_subs:
        conn.execute(
            text("""
                INSERT INTO tbl_submission_versions (
                    version_id, version_submission_id, version_number, version_status,
                    version_submitted_at, version_grade, version_feedback, version_graded_by, version_graded_at, version_created_at
                ) VALUES (
                    :v_id, :sub_id, 1, :v_status,
                    :sub_at, :grade, :feedback, :graded_by, :graded_at, :created_at
                )
            """),
            {
                "v_id": uuid.uuid4(),
                "sub_id": s[0],
                "v_status": s[1],
                "sub_at": s[2],
                "grade": s[3],
                "feedback": s[4],
                "graded_by": s[5],
                "graded_at": s[6],
                "created_at": s[7]
            }
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_tbl_submission_attachments_attachment_version_id'), table_name='tbl_submission_attachments')
    op.drop_table('tbl_submission_attachments')
    op.drop_index(op.f('ix_tbl_submission_versions_version_status'), table_name='tbl_submission_versions')
    op.drop_index(op.f('ix_tbl_submission_versions_version_submission_id'), table_name='tbl_submission_versions')
    op.drop_table('tbl_submission_versions')
    op.execute("DROP TYPE submission_version_status_enum")
    op.drop_column('tbl_assignment_submissions', 'submission_current_version')

