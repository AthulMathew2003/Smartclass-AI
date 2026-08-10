import pytest
import uuid
from httpx import AsyncClient
from app.modules.users.service import UserService
from app.modules.organizations.service import OrganizationService
from app.modules.organizations.member_service import MemberService
from app.modules.organizations.models import Organization, Workspace, Role, OrganizationMember
from app.modules.users.models import User
from app.core.exceptions import ConflictException


@pytest.mark.asyncio
async def test_member_management_flows(client: AsyncClient, db_session):
    # 1. Setup Owner User and Onboard Organization
    user_service = UserService(db_session)
    owner = await user_service.create_user(email="owner@smartclass.com", password="Password123!")
    await db_session.commit()

    # Login Owner
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@smartclass.com", "password": "Password123!"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Onboard Org
    onboard_payload = {
        "org_name": "Skyline Academy",
        "org_slug": "skyline-academy",
        "org_type": "School",
        "org_country": "Canada",
        "org_state": "Ontario",
        "org_city": "Toronto",
        "org_timezone": "America/Toronto",
        "owner_first_name": "Clark",
        "owner_last_name": "Kent",
        "owner_phone": "1112223333",
        "workspace_name": "Homeroom 9A"
    }
    await client.post("/api/v1/organizations/onboarding", json=onboard_payload, headers=headers)
    await db_session.commit()

    # Fetch organization details
    org_memberships_res = await client.get("/api/v1/organizations/memberships", headers=headers)
    org_id = org_memberships_res.json()[0]["organization_id"]
    headers["X-Organization-Id"] = org_id

    # Fetch roles
    roles_res = await client.get("/api/v1/organizations/roles", headers=headers)
    roles_data = roles_res.json()
    teacher_role_id = next(r["role_id"] for r in roles_data if r["role_name"] == "Teacher")
    owner_role_id = next(r["role_id"] for r in roles_data if r["role_name"] == "Owner")

    # Fetch workspace
    ws_res = await client.get("/api/v1/workspaces", headers=headers)
    workspace_id = ws_res.json()[0]["workspace_id"]

    # 2. Check Email for Unregistered Email
    check_res = await client.get(
        f"/api/v1/organizations/members/check-email?email=new_teacher@skyline.com",
        headers=headers
    )
    assert check_res.status_code == 200
    assert check_res.json()["exists"] is False

    # 3. Add Brand New Member (should create user + temp password + memberships)
    add_payload = {
        "email": "new_teacher@skyline.com",
        "first_name": "Lois",
        "last_name": "Lane",
        "phone": "5556667777",
        "role_id": teacher_role_id,
        "workspace_ids": [workspace_id]
    }
    add_res = await client.post("/api/v1/organizations/members", json=add_payload, headers=headers)
    assert add_res.status_code == 200
    assert add_res.json()["email"] == "new_teacher@skyline.com"
    assert add_res.json()["role_name"] == "Teacher"
    assert len(add_res.json()["workspaces"]) == 1

    # Verify user exists in tbl_users
    res_user = await db_session.get(User, uuid.UUID(add_res.json()["user_id"]))
    assert res_user is not None
    assert res_user.user_first_name == "Lois"

    # 4. Check Email for Registered Email
    check_res2 = await client.get(
        f"/api/v1/organizations/members/check-email?email=new_teacher@skyline.com",
        headers=headers
    )
    assert check_res2.status_code == 200
    assert check_res2.json()["exists"] is True
    assert check_res2.json()["first_name"] == "Lois"

    # 5. List Members
    list_res = await client.get("/api/v1/organizations/members", headers=headers)
    assert list_res.status_code == 200
    # Should find 2 members: Owner (Clark) and Teacher (Lois)
    assert len(list_res.json()) == 2

    # 6. Attempt to modify or demote the owner role (should throw Forbidden)
    owner_member_id = next(m["organization_member_id"] for m in list_res.json() if m["email"] == "owner@smartclass.com")
    edit_owner_payload = {
        "first_name": "Clark",
        "last_name": "Kent",
        "phone": "111",
        "role_id": teacher_role_id
    }
    edit_owner_res = await client.patch(
        f"/api/v1/organizations/members/{owner_member_id}",
        json=edit_owner_payload,
        headers=headers
    )
    assert edit_owner_res.status_code == 403

    # 7. Suspend Teacher
    teacher_member_id = next(m["organization_member_id"] for m in list_res.json() if m["email"] == "new_teacher@skyline.com")
    status_payload = {"status": "suspended"}
    status_res = await client.patch(
        f"/api/v1/organizations/members/{teacher_member_id}/status",
        json=status_payload,
        headers=headers
    )
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "suspended"

    # Test workspace assignments sync endpoint
    assign_ws_res = await client.patch(
        f"/api/v1/organizations/members/{res_user.user_id}/workspaces",
        json=[workspace_id],
        headers=headers
    )
    assert assign_ws_res.status_code == 200

    # Verify user status remains active globally
    from app.modules.users.models import UserStatus
    await db_session.refresh(res_user)
    assert res_user.user_status == UserStatus.ACTIVE

    # Verify access is forbidden for the suspended member
    from app.modules.auth.jwt import create_access_token
    lois_token = create_access_token(subject=str(res_user.user_id), email=res_user.user_email)
    lois_headers = {
        "Authorization": f"Bearer {lois_token}",
        "X-Organization-Id": str(org_id)
    }
    res_workspaces = await client.get("/api/v1/workspaces", headers=lois_headers)
    assert res_workspaces.status_code == 403
    assert "suspended" in res_workspaces.json()["message"].lower()

    # 8. Remove Member (Soft Delete)
    del_res = await client.delete(f"/api/v1/organizations/members/{teacher_member_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify teacher user still exists in DB (profile is not deleted)
    teacher_db = await db_session.get(User, res_user.user_id)
    assert teacher_db is not None


@pytest.mark.asyncio
async def test_cross_org_workspace_assignment_and_archived(client: AsyncClient, db_session):
    # Setup two distinct organizations
    user_service = UserService(db_session)
    owner1 = await user_service.create_user(email="owner1@smartclass.com", password="Password123!")
    owner2 = await user_service.create_user(email="owner2@smartclass.com", password="Password123!")
    await db_session.commit()

    # Login Owner 1
    login1_res = await client.post("/api/v1/auth/login", json={"email": "owner1@smartclass.com", "password": "Password123!"})
    token1 = login1_res.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # Login Owner 2
    login2_res = await client.post("/api/v1/auth/login", json={"email": "owner2@smartclass.com", "password": "Password123!"})
    token2 = login2_res.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Onboard Org 1
    await client.post("/api/v1/organizations/onboarding", json={
        "org_name": "Org 1", "org_slug": "org-1", "org_type": "School", "org_country": "US", "org_state": "NY", "org_city": "NYC",
        "org_timezone": "UTC", "owner_first_name": "O1", "owner_last_name": "O1", "owner_phone": "1", "workspace_name": "WS1"
    }, headers=headers1)
    
    # Onboard Org 2
    await client.post("/api/v1/organizations/onboarding", json={
        "org_name": "Org 2", "org_slug": "org-2", "org_type": "School", "org_country": "US", "org_state": "NY", "org_city": "NYC",
        "org_timezone": "UTC", "owner_first_name": "O2", "owner_last_name": "O2", "owner_phone": "2", "workspace_name": "WS2"
    }, headers=headers2)
    await db_session.commit()

    # Get Org 1 Details
    org1_res = await client.get("/api/v1/organizations/memberships", headers=headers1)
    org1_id = org1_res.json()[0]["organization_id"]
    headers1["X-Organization-Id"] = org1_id

    # Get Org 2 Details
    org2_res = await client.get("/api/v1/organizations/memberships", headers=headers2)
    org2_id = org2_res.json()[0]["organization_id"]
    headers2["X-Organization-Id"] = org2_id

    # Get Workspace 2 (from Org 2)
    ws2_res = await client.get("/api/v1/workspaces", headers=headers2)
    ws2_id = ws2_res.json()[0]["workspace_id"]

    # Get Roles for Org 1
    roles1_res = await client.get("/api/v1/organizations/roles", headers=headers1)
    teacher_role1_id = next(r["role_id"] for r in roles1_res.json() if r["role_name"] == "Teacher")

    # 1. Test Cross-Tenant Assignment
    # Org 1 owner tries to assign a member to Workspace 2 (which belongs to Org 2)
    add_payload = {
        "email": "hacker@smartclass.com",
        "first_name": "H",
        "last_name": "H",
        "role_id": teacher_role1_id,
        "workspace_ids": [ws2_id]
    }
    # This should ideally return 400 or 403, but currently returns 200 because of the missing validation.
    cross_org_add_res = await client.post("/api/v1/organizations/members", json=add_payload, headers=headers1)
    assert cross_org_add_res.status_code == 403

    # 2. Test Archived Workspace Assignment
    # Archive Workspace 1 in Org 1
    ws1_res = await client.get("/api/v1/workspaces", headers=headers1)
    ws1_id = ws1_res.json()[0]["workspace_id"]
    await client.delete(f"/api/v1/workspaces/{ws1_id}", headers=headers1)

    add_archived_payload = {
        "email": "archived_assign@smartclass.com",
        "first_name": "A",
        "last_name": "A",
        "role_id": teacher_role1_id,
        "workspace_ids": [ws1_id]
    }
    archived_add_res = await client.post("/api/v1/organizations/members", json=add_archived_payload, headers=headers1)
    assert archived_add_res.status_code == 409
