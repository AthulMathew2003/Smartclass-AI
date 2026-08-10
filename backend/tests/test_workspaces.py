import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.modules.users.service import UserService
from app.modules.organizations.models import Organization, OrganizationStatus, OrganizationMember, OrganizationMemberStatus, WorkspaceStatus, Role
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.member_service import MemberService


@pytest.mark.asyncio
async def test_workspace_crud_and_security(client: AsyncClient, db_session):
    user_service = UserService(db_session)
    
    # 1. Create two owners for two separate organizations
    owner_a = await user_service.create_user(email="ws_owner_a@example.com", password="Password123!")
    owner_b = await user_service.create_user(email="ws_owner_b@example.com", password="Password123!")
    student_a = await user_service.create_user(email="ws_student_a@example.com", password="Password123!")
    await db_session.commit()

    # Login Owner A
    login_a = await client.post("/api/v1/auth/login", json={"email": "ws_owner_a@example.com", "password": "Password123!"})
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Onboard Org A
    payload_a = {
        "org_name": "Workspace Org A",
        "org_slug": "ws-org-a",
        "org_type": "School",
        "org_country": "USA",
        "org_state": "NY",
        "org_city": "NYC",
        "org_timezone": "America/New_York",
        "owner_first_name": "Arthur",
        "owner_last_name": "Pendelton",
        "owner_phone": "1234567890",
        "workspace_name": "Main Hall"
    }
    onboard_a = await client.post("/api/v1/organizations/onboarding", json=payload_a, headers=headers_a)
    assert onboard_a.status_code == 200
    await db_session.commit()

    org_a = (await db_session.execute(select(Organization).where(Organization.organization_slug == "ws-org-a"))).scalars().first()
    headers_a["X-Organization-Id"] = str(org_a.organization_id)

    # Login Owner B
    login_b = await client.post("/api/v1/auth/login", json={"email": "ws_owner_b@example.com", "password": "Password123!"})
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Onboard Org B
    payload_b = {
        "org_name": "Workspace Org B",
        "org_slug": "ws-org-b",
        "org_type": "School",
        "org_country": "USA",
        "org_state": "NY",
        "org_city": "NYC",
        "org_timezone": "America/New_York",
        "owner_first_name": "Bruce",
        "owner_last_name": "Wayne",
        "owner_phone": "1234567890",
        "workspace_name": "Batcave"
    }
    onboard_b = await client.post("/api/v1/organizations/onboarding", json=payload_b, headers=headers_b)
    assert onboard_b.status_code == 200
    await db_session.commit()

    org_b = (await db_session.execute(select(Organization).where(Organization.organization_slug == "ws-org-b"))).scalars().first()
    headers_b["X-Organization-Id"] = str(org_b.organization_id)

    # Add Student A to Org A
    from app.modules.rbac.repository import RBACRepository
    rbac_repo = RBACRepository(db_session)
    roles = await rbac_repo.get_roles_for_organization(org_a.organization_id)
    student_role = next(r for r in roles if r.role_name == "Student")

    member_service = MemberService(db_session)
    await member_service.create_member(org_a.organization_id, type("Req", (), {
        "email": "ws_student_a@example.com",
        "first_name": "Student",
        "last_name": "One",
        "phone": None,
        "role_id": student_role.role_id,
        "workspace_ids": []
    })())
    await db_session.commit()

    # Login Student A
    login_student = await client.post("/api/v1/auth/login", json={"email": "ws_student_a@example.com", "password": "Password123!"})
    token_student = login_student.json()["access_token"]
    headers_student = {"Authorization": f"Bearer {token_student}", "X-Organization-Id": str(org_a.organization_id)}

    # 2. Test authorized user (Owner A) can create workspace
    create_ws_payload = {
        "workspace_name": "Science Lab",
        "workspace_description": "Physics and Chemistry experiments."
    }
    create_res = await client.post("/api/v1/workspaces", json=create_ws_payload, headers=headers_a)
    assert create_res.status_code == 201
    ws_data = create_res.json()
    assert ws_data["workspace_name"] == "Science Lab"
    ws_a_id = ws_data["workspace_id"]

    # 3. Test unauthorized user (Student A) cannot create workspace
    student_create_res = await client.post("/api/v1/workspaces", json={"workspace_name": "Student Zone"}, headers=headers_student)
    assert student_create_res.status_code == 403

    # 4. Duplicate workspace name in SAME organization -> 409 Conflict
    dup_res = await client.post("/api/v1/workspaces", json={"workspace_name": "Science Lab"}, headers=headers_a)
    assert dup_res.status_code == 409

    # 5. Same workspace name in DIFFERENT organization (Org B) -> 201 Created (Allowed)
    org_b_create_res = await client.post("/api/v1/workspaces", json={"workspace_name": "Science Lab"}, headers=headers_b)
    assert org_b_create_res.status_code == 201
    assert org_b_create_res.json()["workspace_organization_id"] == str(org_b.organization_id)

    # 6. Authorized user can GET list & single workspace
    get_res = await client.get(f"/api/v1/workspaces/{ws_a_id}", headers=headers_a)
    assert get_res.status_code == 200
    assert get_res.json()["workspace_name"] == "Science Lab"

    # 7. Cross-organization workspace access -> 403 Forbidden
    # Owner B tries to access Workspace A in Org A
    headers_b_wrong_org = {"Authorization": f"Bearer {token_b}", "X-Organization-Id": str(org_b.organization_id)}
    cross_get_res = await client.get(f"/api/v1/workspaces/{ws_a_id}", headers=headers_b_wrong_org)
    assert cross_get_res.status_code == 403

    # 8. Authorized user can update workspace
    update_payload = {
        "workspace_name": "Advanced Science Lab",
        "workspace_description": "Updated lab description."
    }
    update_res = await client.patch(f"/api/v1/workspaces/{ws_a_id}", json=update_payload, headers=headers_a)
    assert update_res.status_code == 200
    assert update_res.json()["workspace_name"] == "Advanced Science Lab"

    # 9. Unauthorized user (Student A) cannot update workspace -> 403
    student_update_res = await client.patch(f"/api/v1/workspaces/{ws_a_id}", json={"workspace_name": "Hacked Lab"}, headers=headers_student)
    assert student_update_res.status_code == 403

    # Cross-organization update attempt -> 403
    cross_update_res = await client.patch(f"/api/v1/workspaces/{ws_a_id}", json={"workspace_name": "Stolen Lab"}, headers=headers_b_wrong_org)
    assert cross_update_res.status_code == 403

    # 10. Authorized user can archive workspace (soft delete)
    archive_res = await client.delete(f"/api/v1/workspaces/{ws_a_id}", headers=headers_a)
    assert archive_res.status_code == 200
    assert archive_res.json()["workspace_status"] == WorkspaceStatus.ARCHIVED.value

    # Unauthorized user (Student A) cannot archive workspace -> 403
    student_archive_res = await client.delete(f"/api/v1/workspaces/{ws_a_id}", headers=headers_student)
    assert student_archive_res.status_code == 403

    # 11. Inactive/Suspended Membership cannot manipulate workspaces
    # Suspend Student A's membership in Org A
    mem_a = (await db_session.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_member_user_id == student_a.user_id,
            OrganizationMember.organization_member_organization_id == org_a.organization_id
        )
    )).scalars().first()
    mem_a.organization_member_status = OrganizationMemberStatus.SUSPENDED
    await db_session.commit()

    suspended_mem_res = await client.get("/api/v1/workspaces", headers=headers_student)
    assert suspended_mem_res.status_code == 403

    # 12. Inactive/Suspended Organization cannot manipulate workspaces
    org_a.organization_status = OrganizationStatus.SUSPENDED
    await db_session.commit()

    suspended_org_res = await client.get("/api/v1/workspaces", headers=headers_a)
    assert suspended_org_res.status_code == 403
