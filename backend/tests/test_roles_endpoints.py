import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.modules.users.service import UserService
from app.modules.organizations.models import Organization
from app.modules.rbac.models import Permission


@pytest.mark.asyncio
async def test_roles_management_endpoints(client: AsyncClient, db_session):
    # 1. Setup users & onboard organization
    user_service = UserService(db_session)
    owner = await user_service.create_user(email="roles_owner@example.com", password="Password123!")
    await db_session.commit()

    # Login Owner
    login_res = await client.post("/api/v1/auth/login", json={"email": "roles_owner@example.com", "password": "Password123!"})
    token_owner = login_res.json()["access_token"]
    headers_owner = {"Authorization": f"Bearer {token_owner}"}

    # Onboard Organization A
    payload_a = {
        "org_name": "Roles Academy A",
        "org_slug": "roles-acad-a",
        "org_type": "School",
        "org_country": "USA",
        "org_state": "NY",
        "org_city": "NYC",
        "org_timezone": "America/New_York",
        "owner_first_name": "Oliver",
        "owner_last_name": "Queen",
        "owner_phone": "1234567890",
        "workspace_name": "Main Campus"
    }
    onboard_res = await client.post("/api/v1/organizations/onboarding", json=payload_a, headers=headers_owner)
    assert onboard_res.status_code == 200
    await db_session.commit()

    org_a = (await db_session.execute(select(Organization).where(Organization.organization_slug == "roles-acad-a"))).scalars().first()
    headers_owner["X-Organization-Id"] = str(org_a.organization_id)

    # 2. List grouped permissions
    perm_res = await client.get("/api/v1/roles/permissions", headers=headers_owner)
    assert perm_res.status_code == 200
    groups = perm_res.json()
    assert len(groups) > 0
    assert "category" in groups[0]
    assert "permissions" in groups[0]

    # Save two permission IDs for role creation
    all_perms = (await db_session.execute(select(Permission))).scalars().all()
    perm_ids = [str(p.permission_id) for p in all_perms[:2]]

    # 3. List roles (should return 6 system roles initially)
    roles_res = await client.get("/api/v1/roles", headers=headers_owner)
    assert roles_res.status_code == 200
    roles = roles_res.json()
    assert len(roles) >= 6
    owner_role = next(r for r in roles if r["role_name"] == "Owner")
    assert owner_role["role_is_system"] is True
    assert owner_role["member_count"] == 1

    # 4. Create custom role "Math Coordinator"
    create_payload = {
        "role_name": "Math Coordinator",
        "role_description": "Oversees mathematics curriculum and exams.",
        "permission_ids": perm_ids
    }
    create_res = await client.post("/api/v1/roles", json=create_payload, headers=headers_owner)
    assert create_res.status_code == 201
    custom_role = create_res.json()
    assert custom_role["role_name"] == "Math Coordinator"
    assert custom_role["role_is_system"] is False
    assert len(custom_role["permissions"]) == 2
    custom_role_id = custom_role["role_id"]

    # Duplicate custom role name -> 409 Conflict
    dup_res = await client.post("/api/v1/roles", json=create_payload, headers=headers_owner)
    assert dup_res.status_code == 409

    # 5. Fetch single role details
    detail_res = await client.get(f"/api/v1/roles/{custom_role_id}", headers=headers_owner)
    assert detail_res.status_code == 200
    assert detail_res.json()["role_name"] == "Math Coordinator"

    # 6. Update custom role
    update_payload = {
        "role_name": "Lead Math Coordinator",
        "role_description": "Lead mathematics coordinator."
    }
    patch_res = await client.patch(f"/api/v1/roles/{custom_role_id}", json=update_payload, headers=headers_owner)
    assert patch_res.status_code == 200
    assert patch_res.json()["role_name"] == "Lead Math Coordinator"

    # 7. Attempting to update a system role -> 403 Forbidden
    sys_patch_res = await client.patch(f"/api/v1/roles/{owner_role['role_id']}", json={"role_name": "Big Boss"}, headers=headers_owner)
    assert sys_patch_res.status_code == 403

    # Attempting to delete a system role -> 403 Forbidden
    sys_del_res = await client.delete(f"/api/v1/roles/{owner_role['role_id']}", headers=headers_owner)
    assert sys_del_res.status_code == 403

    # 8. Delete custom role (0 members assigned) -> 204 No Content
    del_res = await client.delete(f"/api/v1/roles/{custom_role_id}", headers=headers_owner)
    assert del_res.status_code == 204

    # Verify deleted
    get_deleted = await client.get(f"/api/v1/roles/{custom_role_id}", headers=headers_owner)
    assert get_deleted.status_code == 404
