import pytest
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from httpx import AsyncClient, ASGITransport

from app.db.base import Base
from app.db.session import get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


from sqlalchemy import event

@pytest.fixture
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed system roles, permissions, and role-permission mappings for test database
    from app.modules.organizations.models import Role
    from app.modules.organizations.constants import SystemRole
    from app.modules.rbac.models import Permission, RolePermission
    
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        # 1. Seed Roles
        roles_list = [
            (SystemRole.OWNER, "Organization Owner"),
            (SystemRole.ADMIN, "Administrator"),
            (SystemRole.TEACHER, "Faculty Member"),
            (SystemRole.STUDENT, "Student Scholar"),
            (SystemRole.PARENT, "Parent or Guardian"),
            (SystemRole.STAFF, "Administrative Staff")
        ]
        db_roles = {}
        for name, desc in roles_list:
            role = Role(
                role_organization_id=None,
                role_name=name,
                role_description=desc,
                role_is_system=True
            )
            session.add(role)
            db_roles[name] = role

        # 2. Seed Permissions
        all_permissions = [
            ("member.create", "Create new organization members"),
            ("member.read", "View organization members"),
            ("member.update", "Edit organization members"),
            ("member.delete", "Remove organization members"),
            ("workspace.create", "Create workspaces"),
            ("workspace.read", "View workspaces"),
            ("workspace.update", "Edit workspaces"),
            ("workspace.delete", "Delete workspaces"),
            ("organization.update", "Update organization settings"),
            ("subject.create", "Create subjects"),
            ("subject.read", "View subjects"),
            ("subject.update", "Update subjects"),
            ("subject.delete", "Archive subjects"),
            ("subject.teacher.add", "Add teachers to subjects"),
            ("subject.teacher.remove", "Remove teachers from subjects"),
            ("assignment.create", "Create assignments"),
            ("assignment.update", "Update assignments"),
            ("assignment.grade", "Grade student assignments"),
            ("attendance.view", "View attendance records"),
            ("attendance.manage", "Take or update attendance"),
            ("exam.create", "Create exams"),
            ("exam.publish", "Publish exams"),
            ("analytics.view", "View analytics"),
            ("ai.use", "Use AI tutor features"),
            ("settings.manage", "Manage settings")
        ]
        db_perms = {}
        for name, desc in all_permissions:
            perm = Permission(
                permission_name=name,
                permission_description=desc
            )
            session.add(perm)
            db_perms[name] = perm
            
        await session.flush()

        # 3. Map Permissions to Roles
        role_perms_mapping = {
            "Owner": list(db_perms.keys()),
            "Admin": [
                "member.create", "member.read", "member.update", "member.delete",
                "workspace.create", "workspace.read", "workspace.update", "workspace.delete",
                "subject.create", "subject.read", "subject.update", "subject.delete",
                "subject.teacher.add", "subject.teacher.remove", "assignment.create", "assignment.update",
                "attendance.view", "attendance.manage", "analytics.view"
            ],
            "Teacher": [
                "workspace.read", "subject.create", "subject.read", "subject.update",
                "subject.teacher.add", "subject.teacher.remove",
                "assignment.create", "assignment.update", "assignment.grade",
                "attendance.view", "attendance.manage", "analytics.view", "ai.use"
            ],
            "Student": [
                "workspace.read", "subject.read", "attendance.view", "ai.use"
            ],
            "Parent": [
                "workspace.read", "attendance.view"
            ],
            "Staff": [
                "workspace.read", "attendance.view", "analytics.view"
            ]
        }

        for role_name, perm_names in role_perms_mapping.items():
            role_obj = db_roles.get(role_name)
            if not role_obj:
                continue
            for pname in perm_names:
                perm_obj = db_perms.get(pname)
                if perm_obj:
                    rp = RolePermission(
                        role_id=role_obj.role_id,
                        permission_id=perm_obj.permission_id
                    )
                    session.add(rp)
        await session.commit()
        
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    connection = await test_engine.connect()
    transaction = await connection.begin()

    session_factory = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    session = session_factory()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
