"""unique workspace name per org

Revision ID: 005_uniq_ws_name_per_org
Revises: 4fe5c6002ca5
Create Date: 2026-08-10 22:12:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_uniq_ws_name_per_org'
down_revision: Union[str, Sequence[str], None] = '4fe5c6002ca5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        'uq_workspace_org_name',
        'tbl_workspaces',
        ['workspace_organization_id', 'workspace_name']
    )


def downgrade() -> None:
    op.drop_constraint(
        'uq_workspace_org_name',
        'tbl_workspaces',
        type_='unique'
    )
