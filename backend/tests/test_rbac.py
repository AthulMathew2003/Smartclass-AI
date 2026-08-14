import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy import select
from app.modules.users.service import UserService
from app.modules.organizations.service import OrganizationService
from app.modules.organizations.member_service import MemberService
from app.modules.organizations.models import Organization, Role
from app.modules.rbac.constants import SystemRole, MemberPermission, WorkspacePermission
from app.modules.rbac.dependencies import get_current_organization, require_permission
from app.modules.auth.dependencies import get_current_user
from fastapi import APIRouter, Depends, FastAPI
from app.db.session import get_db

# Create a dummy test router to verify dependencies
test_router = APIRouter()

@test_router.get("/test-owner-perm")
async def test_owner_endpoint(
    org: Organization = Depends(get_current_organization),
    _=Depends(require_permission(MemberPermission.CREATE))
):
    return {"allowed": True}

@test_router.get("/test-org-update")
async def test_org_update_endpoint(
    org: Organization = Depends(get_current_organization),
    _=Depends(require_permission("organization.update"))
):
    return {"allowed": True}

@test_router.get("/test-unknown")
async def test_unknown_endpoint(
    org: Organization = Depends(get_current_organization),
    _=Depends(require_permission("nonexistent.permission"))
):
    return {"allowed": True}


@pytest.mark.asyncio
async def test_rbac_validation_cases(client: AsyncClient, db_session):
    # Register test router on the app for test calls
    from app.main import app
    app.include_router(test_router, prefix="/api/v1/test-rbac")

    # 1. Setup users
    user_service = UserService(db_session)
    owner = await user_service.create_user(email="rbac_owner@example.com", password="Password123!")
    teacher_user = await user_service.create_user(email="rbac_teacher@example.com", password="Password123!")
    await db_session.commit()

    # Login Owner
    login_owner = await client.post("/api/v1/auth/login", json={"email": "rbac_owner@example.com", "password": "Password123!"})
    token_owner = login_owner.json()["access_token"]
    headers_owner = {"Authorization": f"Bearer {token_owner}"}

    # Onboard Organization
    payload = {
        "org_name": "RBAC Academy",
        "org_slug": "rbac-acad",
        "org_type": "School",
        "org_country": "USA",
        "org_state": "NY",
        "org_city": "NYC",
        "org_timezone": "America/New_York",
        "owner_first_name": "Bruce",
        "owner_last_name": "Wayne",
        "owner_phone": "1234567890",
        "workspace_name": "Default WS"
    }
    await client.post("/api/v1/organizations/onboarding", json=payload, headers=headers_owner)
    await db_session.commit()

    # Get Org and Teacher Role
    org = (await db_session.execute(select(Organization).where(Organization.organization_slug == "rbac-acad"))).scalars().first()
    roles = (await db_session.execute(select(Role).where(Role.role_name == SystemRole.TEACHER))).scalars().all()
    teacher_role = [r for r in roles if r.role_organization_id is None][0]

    # Add Teacher as member
    member_service = MemberService(db_session)
    from app.modules.organizations.member_schemas import MemberCreateRequest
    await member_service.create_member(org.organization_id, MemberCreateRequest(
        email="rbac_teacher@example.com",
        first_name="Clark",
        last_name="Kent",
        role_id=teacher_role.role_id,
        workspace_ids=[]
    ))
    await db_session.commit()

    # Login Teacher
    login_teacher = await client.post("/api/v1/auth/login", json={"email": "rbac_teacher@example.com", "password": "Password123!"})
    token_teacher = login_teacher.json()["access_token"]
    headers_teacher = {"Authorization": f"Bearer {token_teacher}", "X-Organization-Id": str(org.organization_id)}

    # Add Org ID header to Owner
    headers_owner["X-Organization-Id"] = str(org.organization_id)

    # 1. Owner has Member Create permission -> 200 OK
    res_owner = await client.get("/api/v1/test-rbac/test-owner-perm", headers=headers_owner)
    assert res_owner.status_code == 200
    assert res_owner.json() == {"allowed": True}

    # 2. Teacher DOES NOT have Member Create permission -> 403 Forbidden
    res_teacher = await client.get("/api/v1/test-rbac/test-owner-perm", headers=headers_teacher)
    assert res_teacher.status_code == 403

    # 3. Owner has Organization Update permission -> 200 OK
    res_owner_update = await client.get("/api/v1/test-rbac/test-org-update", headers=headers_owner)
    assert res_owner_update.status_code == 200

    # 4. Teacher DOES NOT have Organization Update permission -> 403 Forbidden
    res_teacher_update = await client.get("/api/v1/test-rbac/test-org-update", headers=headers_teacher)
    assert res_teacher_update.status_code == 403

    # 5. Accessing with unknown permission -> 403 Forbidden
    res_unknown = await client.get("/api/v1/test-rbac/test-unknown", headers=headers_owner)
    assert res_unknown.status_code == 403

    # 6. Suspended membership -> 403 Forbidden
    # Suspend Teacher
    from app.modules.organizations.models import OrganizationMember
    stmt = select(OrganizationMember).where(OrganizationMember.organization_member_user_id == teacher_user.user_id)
    membership = (await db_session.execute(stmt)).scalars().first()
    membership.organization_member_status = "suspended"
    await db_session.commit()

    res_suspended = await client.get("/api/v1/test-rbac/test-owner-perm", headers=headers_teacher)
    assert res_suspended.status_code == 403


@pytest.mark.asyncio
async def test_me_permissions_endpoint(client: AsyncClient, db_session):
    """Test GET /api/v1/roles/me/permissions for different roles and edge cases."""

    # 1. Setup users
    user_service = UserService(db_session)
    owner = await user_service.create_user(email="perm_owner@example.com", password="Password123!")
    teacher_user = await user_service.create_user(email="perm_teacher@example.com", password="Password123!")
    student_user = await user_service.create_user(email="perm_student@example.com", password="Password123!")
    multi_user = await user_service.create_user(email="perm_multi@example.com", password="Password123!")
    await db_session.commit()

    # Login Owner
    login_owner = await client.post("/api/v1/auth/login", json={"email": "perm_owner@example.com", "password": "Password123!"})
    token_owner = login_owner.json()["access_token"]
    headers_owner = {"Authorization": f"Bearer {token_owner}"}

    # Onboard Organization A
    payload = {
        "org_name": "Perm Academy A",
        "org_slug": "perm-acad-a",
        "org_type": "School",
        "org_country": "USA",
        "org_state": "CA",
        "org_city": "LA",
        "org_timezone": "America/Los_Angeles",
        "owner_first_name": "Perm",
        "owner_last_name": "Owner",
        "owner_phone": "1234567890",
        "workspace_name": "Main WS A"
    }
    await client.post("/api/v1/organizations/onboarding", json=payload, headers=headers_owner)
    await db_session.commit()

    # Get Org A
    org_a = (await db_session.execute(select(Organization).where(Organization.organization_slug == "perm-acad-a"))).scalars().first()
    headers_owner["X-Organization-Id"] = str(org_a.organization_id)

    # Get system roles
    teacher_role = (await db_session.execute(select(Role).where(Role.role_name == SystemRole.TEACHER, Role.role_organization_id.is_(None)))).scalars().first()
    student_role = (await db_session.execute(select(Role).where(Role.role_name == SystemRole.STUDENT, Role.role_organization_id.is_(None)))).scalars().first()

    # Add Teacher and Student as members of Org A
    member_service = MemberService(db_session)
    from app.modules.organizations.member_schemas import MemberCreateRequest
    await member_service.create_member(org_a.organization_id, MemberCreateRequest(
        email="perm_teacher@example.com", first_name="Teach", last_name="Er", role_id=teacher_role.role_id, workspace_ids=[]
    ))
    await member_service.create_member(org_a.organization_id, MemberCreateRequest(
        email="perm_student@example.com", first_name="Stud", last_name="Ent", role_id=student_role.role_id, workspace_ids=[]
    ))
    # Add multi_user as Teacher in Org A
    await member_service.create_member(org_a.organization_id, MemberCreateRequest(
        email="perm_multi@example.com", first_name="Multi", last_name="User", role_id=teacher_role.role_id, workspace_ids=[]
    ))
    await db_session.commit()

    # Login Teacher, Student, Multi
    login_teacher = await client.post("/api/v1/auth/login", json={"email": "perm_teacher@example.com", "password": "Password123!"})
    token_teacher = login_teacher.json()["access_token"]
    headers_teacher = {"Authorization": f"Bearer {token_teacher}", "X-Organization-Id": str(org_a.organization_id)}

    login_student = await client.post("/api/v1/auth/login", json={"email": "perm_student@example.com", "password": "Password123!"})
    token_student = login_student.json()["access_token"]
    headers_student = {"Authorization": f"Bearer {token_student}", "X-Organization-Id": str(org_a.organization_id)}

    login_multi = await client.post("/api/v1/auth/login", json={"email": "perm_multi@example.com", "password": "Password123!"})
    token_multi = login_multi.json()["access_token"]
    headers_multi = {"Authorization": f"Bearer {token_multi}", "X-Organization-Id": str(org_a.organization_id)}

    # ── Test 1: Owner gets all 25 permissions ──
    res = await client.get("/api/v1/roles/me/permissions", headers=headers_owner)
    assert res.status_code == 200
    data = res.json()
    assert data["organization_id"] == str(org_a.organization_id)
    assert len(data["permissions"]) == 25

    # ── Test 2: Teacher gets exactly 13 permissions ──
    res = await client.get("/api/v1/roles/me/permissions", headers=headers_teacher)
    assert res.status_code == 200
    teacher_perms = res.json()["permissions"]
    assert len(teacher_perms) == 13
    assert "workspace.read" in teacher_perms
    assert "subject.create" in teacher_perms
    assert "ai.use" in teacher_perms
    assert "member.create" not in teacher_perms
    assert "settings.manage" not in teacher_perms

    # ── Test 3: Student gets exactly 4 permissions ──
    res = await client.get("/api/v1/roles/me/permissions", headers=headers_student)
    assert res.status_code == 200
    student_perms = res.json()["permissions"]
    assert len(student_perms) == 4
    assert set(student_perms) == {"workspace.read", "attendance.view", "ai.use", "subject.read"}

    # ── Test 4: Suspended membership returns 403 ──
    from app.modules.organizations.models import OrganizationMember
    stmt = select(OrganizationMember).where(
        OrganizationMember.organization_member_user_id == student_user.user_id,
        OrganizationMember.organization_member_organization_id == org_a.organization_id
    )
    membership = (await db_session.execute(stmt)).scalars().first()
    membership.organization_member_status = "suspended"
    await db_session.commit()

    res = await client.get("/api/v1/roles/me/permissions", headers=headers_student)
    assert res.status_code == 403

    # Reactivate for subsequent tests
    membership.organization_member_status = "active"
    await db_session.commit()

    # ── Test 5: Wrong organization returns 403 ──
    fake_org_headers = {**headers_student, "X-Organization-Id": str(uuid.uuid4())}
    res = await client.get("/api/v1/roles/me/permissions", headers=fake_org_headers)
    assert res.status_code == 403

    # ── Test 6: Multi-org isolation ──
    # Create Org B with multi_user as Owner-onboarder
    # We'll register a new owner for Org B and add multi_user as Student
    owner_b = await user_service.create_user(email="perm_owner_b@example.com", password="Password123!")
    await db_session.commit()
    login_owner_b = await client.post("/api/v1/auth/login", json={"email": "perm_owner_b@example.com", "password": "Password123!"})
    token_owner_b = login_owner_b.json()["access_token"]
    headers_owner_b = {"Authorization": f"Bearer {token_owner_b}"}

    payload_b = {
        "org_name": "Perm Academy B",
        "org_slug": "perm-acad-b",
        "org_type": "School",
        "org_country": "USA",
        "org_state": "NY",
        "org_city": "NYC",
        "org_timezone": "America/New_York",
        "owner_first_name": "PermB",
        "owner_last_name": "Owner",
        "owner_phone": "9876543210",
        "workspace_name": "Main WS B"
    }
    await client.post("/api/v1/organizations/onboarding", json=payload_b, headers=headers_owner_b)
    await db_session.commit()

    org_b = (await db_session.execute(select(Organization).where(Organization.organization_slug == "perm-acad-b"))).scalars().first()
    headers_owner_b["X-Organization-Id"] = str(org_b.organization_id)

    # Add multi_user as Student in Org B
    member_service_b = MemberService(db_session)
    await member_service_b.create_member(org_b.organization_id, MemberCreateRequest(
        email="perm_multi@example.com", first_name="Multi", last_name="User", role_id=student_role.role_id, workspace_ids=[]
    ))
    await db_session.commit()

    # Multi user in Org A (Teacher) → 13 permissions (includes subject.teacher.add & subject.teacher.remove)
    res_a = await client.get("/api/v1/roles/me/permissions", headers=headers_multi)
    assert res_a.status_code == 200
    assert len(res_a.json()["permissions"]) == 13

    # Multi user in Org B (Student) → 4 permissions
    headers_multi_b = {**headers_multi, "X-Organization-Id": str(org_b.organization_id)}
    res_b = await client.get("/api/v1/roles/me/permissions", headers=headers_multi_b)
    assert res_b.status_code == 200
    assert len(res_b.json()["permissions"]) == 4
    assert set(res_b.json()["permissions"]) == {"workspace.read", "attendance.view", "ai.use", "subject.read"}

    # Verify org IDs match in response
    assert res_a.json()["organization_id"] == str(org_a.organization_id)
    assert res_b.json()["organization_id"] == str(org_b.organization_id)
