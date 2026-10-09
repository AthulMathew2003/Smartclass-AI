"""add teacher member read permission

Revision ID: d29f81a7b451
Revises: 28e8c1336bab
Create Date: 2026-09-24 12:30:00.000000+00:00

"""
from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text, table, column


# revision identifiers, used by Alembic.
revision: str = 'd29f81a7b451'
down_revision: Union[str, Sequence[str], None] = '28e8c1336bab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema safely adding member.read to Teacher system role."""
    conn = op.get_bind()
    teacher_role = conn.execute(
        text("SELECT role_id FROM tbl_roles WHERE role_name = 'Teacher' AND role_organization_id IS NULL")
    ).fetchone()
    if not teacher_role:
        return
    teacher_role_id = teacher_role[0]

    perm = conn.execute(
        text("SELECT permission_id FROM tbl_permissions WHERE permission_name = 'member.read'")
    ).fetchone()
    if not perm:
        return
    perm_id = perm[0]

    role_permissions_table = table(
        'tbl_role_permissions',
        column('role_permission_id', sa.UUID),
        column('role_id', sa.UUID),
        column('permission_id', sa.UUID),
        column('role_permission_created_at', sa.DateTime)
    )

    exists = conn.execute(
        text("SELECT 1 FROM tbl_role_permissions WHERE role_id = :rid AND permission_id = :pid"),
        {"rid": teacher_role_id, "pid": perm_id}
    ).fetchone()

    if not exists:
        op.bulk_insert(
            role_permissions_table,
            [
                {
                    "role_permission_id": uuid.uuid4(),
                    "role_id": teacher_role_id,
                    "permission_id": perm_id,
                    "role_permission_created_at": datetime.now(timezone.utc)
                }
            ]
        )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    teacher_role = conn.execute(
        text("SELECT role_id FROM tbl_roles WHERE role_name = 'Teacher' AND role_organization_id IS NULL")
    ).fetchone()
    if teacher_role:
        teacher_role_id = teacher_role[0]
        conn.execute(
            text("""
                DELETE FROM tbl_role_permissions 
                WHERE role_id = :rid AND permission_id IN (
                    SELECT permission_id FROM tbl_permissions WHERE permission_name = 'member.read'
                )
            """),
            {"rid": teacher_role_id}
        )
