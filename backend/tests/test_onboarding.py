import pytest
from httpx import AsyncClient
from app.modules.users.service import UserService
from app.modules.organizations.service import OrganizationService
from app.modules.organizations.models import Organization, Workspace, Role, OrganizationMember
from app.core.exceptions import ConflictException


@pytest.mark.asyncio
async def test_organization_status_endpoint(client: AsyncClient, db_session):
    # Create test user
    user_service = UserService(db_session)
    user = await user_service.create_user(email="status_user@example.com", password="Password123!")
    await db_session.commit()

    # Get login token
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "status_user@example.com", "password": "Password123!"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify status is has_organization=False
    status_res = await client.get("/api/v1/organizations/status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["has_organization"] is False


@pytest.mark.asyncio
async def test_onboarding_atomic_transaction(client: AsyncClient, db_session):
    # Create test user
    user_service = UserService(db_session)
    user = await user_service.create_user(email="onboard_user@example.com", password="Password123!")
    await db_session.commit()

    # Get login token
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "onboard_user@example.com", "password": "Password123!"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Successful Onboarding
    payload = {
        "org_name": "Wayne Enterprises",
        "org_slug": "wayne-ent",
        "org_type": "Company",
        "org_country": "United States",
        "org_state": "Gotham",
        "org_city": "Gotham City",
        "org_timezone": "America/New_York",
        "owner_first_name": "Bruce",
        "owner_last_name": "Wayne",
        "owner_phone": "1234567890",
        "workspace_name": "Applied Sciences"
    }

    res = await client.post("/api/v1/organizations/onboarding", json=payload, headers=headers)
    assert res.status_code == 200
    assert res.json() == {"success": True, "message": "Organization onboarding completed successfully."}

    # Verify status is now has_organization=True
    status_res = await client.get("/api/v1/organizations/status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["has_organization"] is True
    assert status_res.json()["organization_name"] == "Wayne Enterprises"
    assert status_res.json()["role"] == "Owner"

    # Verify duplicate onboarding name/slug throws ConflictException
    # 1. Create a second user
    user2 = await user_service.create_user(email="onboard_user2@example.com", password="Password123!")
    await db_session.commit()
    login_res2 = await client.post(
        "/api/v1/auth/login",
        json={"email": "onboard_user2@example.com", "password": "Password123!"}
    )
    token2 = login_res2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Attempt duplicate name onboarding
    payload_dup = payload.copy()
    payload_dup["org_slug"] = "different-slug"
    res_dup = await client.post("/api/v1/organizations/onboarding", json=payload_dup, headers=headers2)
    assert res_dup.status_code == 409
