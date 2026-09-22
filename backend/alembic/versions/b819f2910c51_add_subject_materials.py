"""add_subject_materials

Revision ID: b819f2910c51
Revises: 7a3e819b5201
Create Date: 2026-08-20 10:00:00.000000+00:00

"""
from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import text, table, column


# revision identifiers, used by Alembic.
revision: str = 'b819f2910c51'
down_revision: Union[str, Sequence[str], None] = '7a3e819b5201'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


permissions_table = table(
    'tbl_permissions',
    column('permission_id', sa.UUID),
    column('permission_name', sa.String),
    column('permission_description', sa.Text),
    column('permission_created_at', sa.DateTime),
    column('permission_updated_at', sa.DateTime)
)

role_permissions_table = table(
    'tbl_role_permissions',
    column('role_permission_id', sa.UUID),
    column('role_id', sa.UUID),
    column('permission_id', sa.UUID),
    column('role_permission_created_at', sa.DateTime)
)


def upgrade() -> None:
    """Upgrade schema to add tbl_subject_materials and seed permissions."""
    # 1. Create tbl_subject_materials
    op.create_table(
        'tbl_subject_materials',
        sa.Column('material_id', sa.UUID(), nullable=False),
        sa.Column('material_subject_id', sa.UUID(), nullable=False),
        sa.Column('material_title', sa.String(length=255), nullable=False),
        sa.Column('material_description', sa.Text(), nullable=True),
        sa.Column('material_category', sa.String(length=100), nullable=False, server_default='Notes'),
        sa.Column('material_original_filename', sa.String(length=255), nullable=False),
        sa.Column('material_content_type', sa.String(length=100), nullable=False),
        sa.Column('material_file_size', sa.BigInteger(), nullable=False),
        sa.Column('material_s3_key', sa.Text(), nullable=False),
        sa.Column(
            'material_status',
            sa.Enum('active', 'archived', name='subject_material_status_enum'),
            nullable=False,
            server_default='active'
        ),
        sa.Column('material_uploaded_by', sa.UUID(), nullable=True),
        sa.Column('material_created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('material_updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['material_subject_id'],
            ['tbl_subjects.subject_id'],
            name=op.f('fk_tbl_subject_materials_material_subject_id_tbl_subjects'),
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['material_uploaded_by'],
            ['tbl_users.user_id'],
            name=op.f('fk_tbl_subject_materials_material_uploaded_by_tbl_users'),
            ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('material_id', name=op.f('pk_tbl_subject_materials'))
    )
    op.create_index(
        op.f('ix_tbl_subject_materials_material_subject_id'),
        'tbl_subject_materials',
        ['material_subject_id'],
        unique=False
    )
    op.create_index(
        op.f('ix_tbl_subject_materials_material_status'),
        'tbl_subject_materials',
        ['material_status'],
        unique=False
    )
    op.create_index(
        op.f('ix_tbl_subject_materials_material_created_at'),
        'tbl_subject_materials',
        ['material_created_at'],
        unique=False
    )

    # 2. Seed subject material permissions
    new_permissions = [
        ("subject.material.create", "Upload course materials to subjects"),
        ("subject.material.read", "View and download course materials"),
        ("subject.material.update", "Update course material metadata"),
        ("subject.material.delete", "Archive or delete course materials"),
    ]

    conn = op.get_bind()
    existing_perms = conn.execute(text("SELECT permission_name, permission_id FROM tbl_permissions")).fetchall()
    existing_perms_map = {p[0]: p[1] for p in existing_perms}

    permission_ids_map = {}
    for name, desc in new_permissions:
        if name in existing_perms_map:
            permission_ids_map[name] = existing_perms_map[name]
        else:
            perm_id = uuid.uuid4()
            permission_ids_map[name] = perm_id
            op.bulk_insert(
                permissions_table,
                [
                    {
                        "permission_id": perm_id,
                        "permission_name": name,
                        "permission_description": desc,
                        "permission_created_at": datetime.now(timezone.utc),
                        "permission_updated_at": datetime.now(timezone.utc)
                    }
                ]
            )

    # 3. Map permissions to system roles
    roles = conn.execute(text("SELECT role_id, role_name FROM tbl_roles WHERE role_organization_id IS NULL")).fetchall()
    roles_map = {r[1]: r[0] for r in roles}

    role_perms_mapping = {
        "Owner": ["subject.material.create", "subject.material.read", "subject.material.update", "subject.material.delete"],
        "Admin": ["subject.material.create", "subject.material.read", "subject.material.update", "subject.material.delete"],
        "Teacher": ["subject.material.create", "subject.material.read", "subject.material.update", "subject.material.delete"],
        "Student": ["subject.material.read"],
        "Parent": ["subject.material.read"],
        "Staff": ["subject.material.read"],
    }

    for role_name, perm_names in role_perms_mapping.items():
        role_id = roles_map.get(role_name)
        if not role_id:
            continue
        for pname in perm_names:
            pid = permission_ids_map.get(pname)
            if pid:
                exists = conn.execute(
                    text("SELECT 1 FROM tbl_role_permissions WHERE role_id = :r_id AND permission_id = :p_id"),
                    {"r_id": role_id, "p_id": pid}
                ).fetchone()
                if not exists:
                    op.bulk_insert(
                        role_permissions_table,
                        [
                            {
                                "role_permission_id": uuid.uuid4(),
                                "role_id": role_id,
                                "permission_id": pid,
                                "role_permission_created_at": datetime.now(timezone.utc)
                            }
                        ]
                    )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()

    # 1. Clean up role permissions for material permissions
    conn.execute(
        text("""
            DELETE FROM tbl_role_permissions 
            WHERE permission_id IN (
                SELECT permission_id FROM tbl_permissions 
                WHERE permission_name IN (
                    'subject.material.create', 
                    'subject.material.read', 
                    'subject.material.update', 
                    'subject.material.delete'
                )
            )
        """)
    )

    # 2. Clean up permissions
    conn.execute(
        text("""
            DELETE FROM tbl_permissions 
            WHERE permission_name IN (
                'subject.material.create', 
                'subject.material.read', 
                'subject.material.update', 
                'subject.material.delete'
            )
        """)
    )

    # 3. Drop table and indexes
    op.drop_index(op.f('ix_tbl_subject_materials_material_created_at'), table_name='tbl_subject_materials')
    op.drop_index(op.f('ix_tbl_subject_materials_material_status'), table_name='tbl_subject_materials')
    op.drop_index(op.f('ix_tbl_subject_materials_material_subject_id'), table_name='tbl_subject_materials')
    op.drop_table('tbl_subject_materials')

    # 4. Drop Enum
    op.execute("DROP TYPE IF EXISTS subject_material_status_enum")
