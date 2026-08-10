"""seed system roles

Revision ID: 01a6df3b0e46
Revises: 004_org_geo_columns
Create Date: 2026-08-06 08:18:51.998637+00:00

"""
from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision: str = '01a6df3b0e46'
down_revision: Union[str, Sequence[str], None] = '004_org_geo_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Define table representation
roles_table = table(
    'tbl_roles',
    column('role_id', sa.UUID),
    column('role_organization_id', sa.UUID),
    column('role_name', sa.String),
    column('role_description', sa.Text),
    column('role_is_system', sa.Boolean),
    column('role_created_at', sa.DateTime),
    column('role_updated_at', sa.DateTime)
)


def upgrade() -> None:
    """Upgrade schema."""
    op.bulk_insert(
        roles_table,
        [
            {
                "role_id": uuid.uuid4(),
                "role_organization_id": None,
                "role_name": "Owner",
                "role_description": "Organization Owner",
                "role_is_system": True,
                "role_created_at": datetime.now(timezone.utc),
                "role_updated_at": datetime.now(timezone.utc)
            },
            {
                "role_id": uuid.uuid4(),
                "role_organization_id": None,
                "role_name": "Admin",
                "role_description": "Administrator",
                "role_is_system": True,
                "role_created_at": datetime.now(timezone.utc),
                "role_updated_at": datetime.now(timezone.utc)
            },
            {
                "role_id": uuid.uuid4(),
                "role_organization_id": None,
                "role_name": "Teacher",
                "role_description": "Faculty Member",
                "role_is_system": True,
                "role_created_at": datetime.now(timezone.utc),
                "role_updated_at": datetime.now(timezone.utc)
            },
            {
                "role_id": uuid.uuid4(),
                "role_organization_id": None,
                "role_name": "Student",
                "role_description": "Student Scholar",
                "role_is_system": True,
                "role_created_at": datetime.now(timezone.utc),
                "role_updated_at": datetime.now(timezone.utc)
            },
            {
                "role_id": uuid.uuid4(),
                "role_organization_id": None,
                "role_name": "Parent",
                "role_description": "Parent or Guardian",
                "role_is_system": True,
                "role_created_at": datetime.now(timezone.utc),
                "role_updated_at": datetime.now(timezone.utc)
            },
            {
                "role_id": uuid.uuid4(),
                "role_organization_id": None,
                "role_name": "Staff",
                "role_description": "Administrative Staff",
                "role_is_system": True,
                "role_created_at": datetime.now(timezone.utc),
                "role_updated_at": datetime.now(timezone.utc)
            }
        ]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM tbl_roles WHERE role_organization_id IS NULL AND role_is_system = TRUE")
