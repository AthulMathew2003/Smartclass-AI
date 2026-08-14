"""add teacher classroom member permissions

Revision ID: c770538dddfh
Revises: c770538dddff
Create Date: 2026-08-13 09:30:00.000000+00:00

"""
from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text, table, column


# revision identifiers, used by Alembic.
revision: str = 'c770538dddfh'
down_revision: Union[str, Sequence[str], None] = 'c770538dddff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema safely adding classroom.member.add and classroom.member.remove to Teacher role."""
    conn = op.get_bind()
    teacher_role = conn.execute(text("SELECT role_id FROM tbl_roles WHERE role_name = 'Teacher' AND role_organization_id IS NULL")).fetchone()
    if not teacher_role:
        return
    teacher_role_id = teacher_role[0]

    perms = conn.execute(text("SELECT permission_id, permission_name FROM tbl_permissions WHERE permission_name IN ('classroom.member.add', 'classroom.member.remove')")).fetchall()

    role_permissions_table = table(
        'tbl_role_permissions',
        column('role_permission_id', sa.UUID),
        column('role_id', sa.UUID),
        column('permission_id', sa.UUID),
        column('role_permission_created_at', sa.DateTime)
    )

    for pid, pname in perms:
        exists = conn.execute(
            text("SELECT 1 FROM tbl_role_permissions WHERE role_id = :rid AND permission_id = :pid"),
            {"rid": teacher_role_id, "pid": pid}
        ).fetchone()
        if not exists:
            op.bulk_insert(
                role_permissions_table,
                [
                    {
                        "role_permission_id": uuid.uuid4(),
                        "role_id": teacher_role_id,
                        "permission_id": pid,
                        "role_permission_created_at": datetime.now(timezone.utc)
                    }
                ]
            )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    teacher_role = conn.execute(text("SELECT role_id FROM tbl_roles WHERE role_name = 'Teacher' AND role_organization_id IS NULL")).fetchone()
    if teacher_role:
        teacher_role_id = teacher_role[0]
        conn.execute(
            text("""
                DELETE FROM tbl_role_permissions 
                WHERE role_id = :rid AND permission_id IN (
                    SELECT permission_id FROM tbl_permissions WHERE permission_name IN ('classroom.member.add', 'classroom.member.remove')
                )
            """),
            {"rid": teacher_role_id}
        )
