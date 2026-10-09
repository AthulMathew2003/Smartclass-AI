"""add_rag_material_indexing_columns

Revision ID: 69f92fb0c302
Revises: c82910ab3d99
Create Date: 2026-09-23 07:18:15.256775+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '69f92fb0c302'
down_revision: Union[str, Sequence[str], None] = 'c82910ab3d99'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    material_index_status_enum = postgresql.ENUM(
        'pending', 'processing', 'indexed', 'failed', 'unsupported',
        name='material_index_status_enum'
    )
    material_index_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'tbl_subject_materials',
        sa.Column(
            'material_index_status',
            material_index_status_enum,
            server_default='pending',
            nullable=False
        )
    )
    op.create_index(
        op.f('ix_tbl_subject_materials_material_index_status'),
        'tbl_subject_materials',
        ['material_index_status'],
        unique=False
    )
    op.add_column(
        'tbl_subject_materials',
        sa.Column('material_indexed_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'tbl_subject_materials',
        sa.Column('material_index_error', sa.Text(), nullable=True)
    )
    op.add_column(
        'tbl_subject_materials',
        sa.Column('material_content_hash', sa.String(length=64), nullable=True)
    )
    op.add_column(
        'tbl_subject_materials',
        sa.Column('material_chunk_count', sa.BigInteger(), server_default='0', nullable=False)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tbl_subject_materials', 'material_chunk_count')
    op.drop_column('tbl_subject_materials', 'material_content_hash')
    op.drop_column('tbl_subject_materials', 'material_index_error')
    op.drop_column('tbl_subject_materials', 'material_indexed_at')
    op.drop_index(
        op.f('ix_tbl_subject_materials_material_index_status'),
        table_name='tbl_subject_materials'
    )
    op.drop_column('tbl_subject_materials', 'material_index_status')
    
    material_index_status_enum = postgresql.ENUM(
        'pending', 'processing', 'indexed', 'failed', 'unsupported',
        name='material_index_status_enum'
    )
    material_index_status_enum.drop(op.get_bind(), checkfirst=True)
