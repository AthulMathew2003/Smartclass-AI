"""refactor_classroom_to_subject

Revision ID: 1c5e47569ffa
Revises: c770538dddfh
Create Date: 2026-08-13 06:36:34.534953+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1c5e47569ffa'
down_revision: Union[str, Sequence[str], None] = 'c770538dddfh'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Rename table and columns
    op.rename_table('tbl_classrooms', 'tbl_subjects')
    op.alter_column('tbl_subjects', 'classroom_id', new_column_name='subject_id')
    op.alter_column('tbl_subjects', 'classroom_workspace_id', new_column_name='subject_workspace_id')
    op.alter_column('tbl_subjects', 'classroom_name', new_column_name='subject_name')
    op.alter_column('tbl_subjects', 'classroom_description', new_column_name='subject_description')
    op.alter_column('tbl_subjects', 'classroom_status', new_column_name='subject_status')
    op.alter_column('tbl_subjects', 'classroom_created_by', new_column_name='subject_created_by')
    op.alter_column('tbl_subjects', 'classroom_created_at', new_column_name='subject_created_at')
    op.alter_column('tbl_subjects', 'classroom_updated_at', new_column_name='subject_updated_at')

    # Rename enum
    op.execute("ALTER TYPE classroom_status_enum RENAME TO subject_status_enum")

    # Rename index and constraint
    op.execute("ALTER INDEX ix_tbl_classrooms_classroom_workspace_id RENAME TO ix_tbl_subjects_subject_workspace_id")
    op.execute("ALTER TABLE tbl_subjects RENAME CONSTRAINT uq_classroom_workspace_name TO uq_subject_workspace_name")

    # 2. Create tbl_subject_teachers
    op.create_table('tbl_subject_teachers',
        sa.Column('subject_teacher_id', sa.UUID(), nullable=False),
        sa.Column('subject_teacher_subject_id', sa.UUID(), nullable=False),
        sa.Column('subject_teacher_user_id', sa.UUID(), nullable=False),
        sa.Column('subject_teacher_assigned_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['subject_teacher_subject_id'], ['tbl_subjects.subject_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subject_teacher_user_id'], ['tbl_users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('subject_teacher_id'),
        sa.UniqueConstraint('subject_teacher_subject_id', 'subject_teacher_user_id', name='uq_subject_teacher')
    )

    # 3. Migrate data
    op.execute('''
        INSERT INTO tbl_subject_teachers (subject_teacher_id, subject_teacher_subject_id, subject_teacher_user_id, subject_teacher_assigned_at)
        SELECT classroom_member_id, classroom_member_classroom_id, classroom_member_user_id, classroom_member_joined_at 
        FROM tbl_classroom_members WHERE classroom_member_type = 'TEACHER'
    ''')

    # 4. Drop tbl_classroom_members and its enum
    op.drop_table('tbl_classroom_members')
    op.execute("DROP TYPE classroom_member_type_enum")

    # 5. Rename permissions in tbl_permissions
    op.execute("UPDATE tbl_permissions SET permission_name = 'subject.create' WHERE permission_name = 'classroom.create'")
    op.execute("UPDATE tbl_permissions SET permission_name = 'subject.read' WHERE permission_name = 'classroom.read'")
    op.execute("UPDATE tbl_permissions SET permission_name = 'subject.update' WHERE permission_name = 'classroom.update'")
    op.execute("UPDATE tbl_permissions SET permission_name = 'subject.delete' WHERE permission_name = 'classroom.delete'")
    op.execute("UPDATE tbl_permissions SET permission_name = 'subject.teacher.add' WHERE permission_name = 'classroom.member.add'")
    op.execute("UPDATE tbl_permissions SET permission_name = 'subject.teacher.remove' WHERE permission_name = 'classroom.member.remove'")


def downgrade() -> None:
    # Reverse operations
    op.execute("UPDATE tbl_permissions SET permission_name = 'classroom.create' WHERE permission_name = 'subject.create'")
    op.execute("UPDATE tbl_permissions SET permission_name = 'classroom.read' WHERE permission_name = 'subject.read'")
    op.execute("UPDATE tbl_permissions SET permission_name = 'classroom.update' WHERE permission_name = 'subject.update'")
    op.execute("UPDATE tbl_permissions SET permission_name = 'classroom.delete' WHERE permission_name = 'subject.delete'")
    op.execute("UPDATE tbl_permissions SET permission_name = 'classroom.member.add' WHERE permission_name = 'subject.teacher.add'")
    op.execute("UPDATE tbl_permissions SET permission_name = 'classroom.member.remove' WHERE permission_name = 'subject.teacher.remove'")

    op.execute("CREATE TYPE classroom_member_type_enum AS ENUM ('TEACHER', 'STUDENT')")
    op.create_table('tbl_classroom_members',
        sa.Column('classroom_member_id', sa.UUID(), autoincrement=False, nullable=False),
        sa.Column('classroom_member_classroom_id', sa.UUID(), autoincrement=False, nullable=False),
        sa.Column('classroom_member_user_id', sa.UUID(), autoincrement=False, nullable=False),
        sa.Column('classroom_member_type', postgresql.ENUM('TEACHER', 'STUDENT', name='classroom_member_type_enum'), autoincrement=False, nullable=False),
        sa.Column('classroom_member_joined_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(['classroom_member_classroom_id'], ['tbl_subjects.subject_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['classroom_member_user_id'], ['tbl_users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('classroom_member_id'),
        sa.UniqueConstraint('classroom_member_classroom_id', 'classroom_member_user_id', name='uq_classroom_member')
    )

    op.execute('''
        INSERT INTO tbl_classroom_members (classroom_member_id, classroom_member_classroom_id, classroom_member_user_id, classroom_member_type, classroom_member_joined_at)
        SELECT subject_teacher_id, subject_teacher_subject_id, subject_teacher_user_id, 'TEACHER', subject_teacher_assigned_at 
        FROM tbl_subject_teachers
    ''')

    op.drop_table('tbl_subject_teachers')

    op.execute("ALTER TABLE tbl_subjects RENAME CONSTRAINT uq_subject_workspace_name TO uq_classroom_workspace_name")
    op.execute("ALTER INDEX ix_tbl_subjects_subject_workspace_id RENAME TO ix_tbl_classrooms_classroom_workspace_id")
    
    op.execute("ALTER TYPE subject_status_enum RENAME TO classroom_status_enum")

    op.alter_column('tbl_subjects', 'subject_updated_at', new_column_name='classroom_updated_at')
    op.alter_column('tbl_subjects', 'subject_created_at', new_column_name='classroom_created_at')
    op.alter_column('tbl_subjects', 'subject_created_by', new_column_name='classroom_created_by')
    op.alter_column('tbl_subjects', 'subject_status', new_column_name='classroom_status')
    op.alter_column('tbl_subjects', 'subject_description', new_column_name='classroom_description')
    op.alter_column('tbl_subjects', 'subject_name', new_column_name='classroom_name')
    op.alter_column('tbl_subjects', 'subject_workspace_id', new_column_name='classroom_workspace_id')
    op.alter_column('tbl_subjects', 'subject_id', new_column_name='classroom_id')
    op.rename_table('tbl_subjects', 'tbl_classrooms')
