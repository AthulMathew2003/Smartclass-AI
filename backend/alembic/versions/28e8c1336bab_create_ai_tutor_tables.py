"""create_ai_tutor_tables

Revision ID: 28e8c1336bab
Revises: 69f92fb0c302
Create Date: 2026-09-23 08:43:23.934719+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '28e8c1336bab'
down_revision: Union[str, Sequence[str], None] = '69f92fb0c302'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'tbl_ai_tutor_conversations',
        sa.Column('conversation_id', sa.UUID(), nullable=False),
        sa.Column('conversation_organization_id', sa.UUID(), nullable=False),
        sa.Column('conversation_workspace_id', sa.UUID(), nullable=False),
        sa.Column('conversation_subject_id', sa.UUID(), nullable=False),
        sa.Column('conversation_student_id', sa.UUID(), nullable=False),
        sa.Column('conversation_title', sa.String(length=255), nullable=False),
        sa.Column('conversation_created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('conversation_updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['conversation_organization_id'], ['tbl_organizations.organization_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conversation_student_id'], ['tbl_users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conversation_subject_id'], ['tbl_subjects.subject_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conversation_workspace_id'], ['tbl_workspaces.workspace_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('conversation_id')
    )
    op.create_index(op.f('ix_tbl_ai_tutor_conversations_conversation_id'), 'tbl_ai_tutor_conversations', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_tbl_ai_tutor_conversations_conversation_organization_id'), 'tbl_ai_tutor_conversations', ['conversation_organization_id'], unique=False)
    op.create_index(op.f('ix_tbl_ai_tutor_conversations_conversation_student_id'), 'tbl_ai_tutor_conversations', ['conversation_student_id'], unique=False)
    op.create_index(op.f('ix_tbl_ai_tutor_conversations_conversation_subject_id'), 'tbl_ai_tutor_conversations', ['conversation_subject_id'], unique=False)
    op.create_index(op.f('ix_tbl_ai_tutor_conversations_conversation_workspace_id'), 'tbl_ai_tutor_conversations', ['conversation_workspace_id'], unique=False)

    op.create_table(
        'tbl_ai_tutor_messages',
        sa.Column('message_id', sa.UUID(), nullable=False),
        sa.Column('message_conversation_id', sa.UUID(), nullable=False),
        sa.Column('message_role', sa.String(length=32), nullable=False),
        sa.Column('message_content', sa.Text(), nullable=False),
        sa.Column('message_sources', sa.JSON(), nullable=True),
        sa.Column('message_created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['message_conversation_id'], ['tbl_ai_tutor_conversations.conversation_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('message_id')
    )
    op.create_index(op.f('ix_tbl_ai_tutor_messages_message_conversation_id'), 'tbl_ai_tutor_messages', ['message_conversation_id'], unique=False)
    op.create_index(op.f('ix_tbl_ai_tutor_messages_message_id'), 'tbl_ai_tutor_messages', ['message_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_tbl_ai_tutor_messages_message_id'), table_name='tbl_ai_tutor_messages')
    op.drop_index(op.f('ix_tbl_ai_tutor_messages_message_conversation_id'), table_name='tbl_ai_tutor_messages')
    op.drop_table('tbl_ai_tutor_messages')

    op.drop_index(op.f('ix_tbl_ai_tutor_conversations_conversation_workspace_id'), table_name='tbl_ai_tutor_conversations')
    op.drop_index(op.f('ix_tbl_ai_tutor_conversations_conversation_subject_id'), table_name='tbl_ai_tutor_conversations')
    op.drop_index(op.f('ix_tbl_ai_tutor_conversations_conversation_student_id'), table_name='tbl_ai_tutor_conversations')
    op.drop_index(op.f('ix_tbl_ai_tutor_conversations_conversation_organization_id'), table_name='tbl_ai_tutor_conversations')
    op.drop_index(op.f('ix_tbl_ai_tutor_conversations_conversation_id'), table_name='tbl_ai_tutor_conversations')
    op.drop_table('tbl_ai_tutor_conversations')
