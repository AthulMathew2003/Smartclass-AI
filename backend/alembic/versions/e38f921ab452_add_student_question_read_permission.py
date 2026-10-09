"""add student question read permission

Revision ID: e38f921ab452
Revises: d29f81a7b451
Create Date: 2026-09-25 10:05:00.000000+00:00

"""
from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text, table, column


# revision identifiers, used by Alembic.
revision: str = 'e38f921ab452'
down_revision: Union[str, Sequence[str], None] = 'd29f81a7b451'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: assign question.read to Student, Parent, and Staff system roles."""
    conn = op.get_bind()

    perm = conn.execute(
        text("SELECT permission_id FROM tbl_permissions WHERE permission_name = 'question.read'")
    ).fetchone()
    if not perm:
        return
    perm_id = perm[0]

    roles = conn.execute(
        text("SELECT role_id, role_name FROM tbl_roles WHERE role_name IN ('Student', 'Parent', 'Staff') AND role_organization_id IS NULL")
    ).fetchall()

    role_permissions_table = table(
        'tbl_role_permissions',
        column('role_permission_id', sa.UUID),
        column('role_id', sa.UUID),
        column('permission_id', sa.UUID),
        column('role_permission_created_at', sa.DateTime)
    )

    for role_id, role_name in roles:
        exists = conn.execute(
            text("SELECT 1 FROM tbl_role_permissions WHERE role_id = :rid AND permission_id = :pid"),
            {"rid": role_id, "pid": perm_id}
        ).fetchone()

        if not exists:
            op.bulk_insert(
                role_permissions_table,
                [
                    {
                        "role_permission_id": uuid.uuid4(),
                        "role_id": role_id,
                        "permission_id": perm_id,
                        "role_permission_created_at": datetime.now(timezone.utc)
                    }
                ]
            )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    conn.execute(
        text("""
            DELETE FROM tbl_role_permissions 
            WHERE permission_id IN (
                SELECT permission_id FROM tbl_permissions WHERE permission_name = 'question.read'
            ) AND role_id IN (
                SELECT role_id FROM tbl_roles WHERE role_name IN ('Student', 'Parent', 'Staff') AND role_organization_id IS NULL
            )
        """)
    )
