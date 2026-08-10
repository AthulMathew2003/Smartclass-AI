import pytest
import uuid
from httpx import AsyncClient
from app.modules.users.service import UserService
from app.modules.organizations.service import OrganizationService
from app.modules.organizations.models import Organization, Workspace, Role, OrganizationMember
from app.core.exceptions import ConflictException
from sqlalchemy import select


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


@pytest.mark.asyncio
async def test_owner_can_own_only_one_organization(client: AsyncClient, db_session):
    user_service = UserService(db_session)
    user = await user_service.create_user(email="one_owner@example.com", password="Password123!")
    await db_session.commit()

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "one_owner@example.com", "password": "Password123!"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "org_name": "Wayne Enterprises One",
        "org_slug": "wayne-ent-one",
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

    # Onboard first organization
    res1 = await client.post("/api/v1/organizations/onboarding", json=payload, headers=headers)
    assert res1.status_code == 200

    # Attempt to onboard second organization (should fail with 409)
    payload2 = payload.copy()
    payload2["org_name"] = "Wayne Enterprises Two"
    payload2["org_slug"] = "wayne-ent-two"
    res2 = await client.post("/api/v1/organizations/onboarding", json=payload2, headers=headers)
    assert res2.status_code == 409


@pytest.mark.asyncio
async def test_user_can_belong_to_multiple_organizations(client: AsyncClient, db_session):
    from app.modules.organizations.member_service import MemberService
    from app.modules.organizations.repository import OrganizationRepository

    user_service = UserService(db_session)
    # Create Owner 1, Owner 2, and Member user
    owner1 = await user_service.create_user(email="owner1@example.com", password="Password123!")
    owner2 = await user_service.create_user(email="owner2@example.com", password="Password123!")
    member_user = await user_service.create_user(email="member@example.com", password="Password123!")
    await db_session.commit()

    # Onboard Org 1
    login_owner1 = await client.post("/api/v1/auth/login", json={"email": "owner1@example.com", "password": "Password123!"})
    token1 = login_owner1.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}
    payload1 = {
        "org_name": "Org One", "org_slug": "org-one", "org_type": "School", "org_country": "USA", "org_state": "CA", "org_city": "LA", "org_timezone": "America/Los_Angeles", "owner_first_name": "Owner", "owner_last_name": "One", "owner_phone": "1", "workspace_name": "WS1"
    }
    await client.post("/api/v1/organizations/onboarding", json=payload1, headers=headers1)

    # Onboard Org 2
    login_owner2 = await client.post("/api/v1/auth/login", json={"email": "owner2@example.com", "password": "Password123!"})
    token2 = login_owner2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}
    payload2 = {
        "org_name": "Org Two", "org_slug": "org-two", "org_type": "School", "org_country": "USA", "org_state": "CA", "org_city": "LA", "org_timezone": "America/Los_Angeles", "owner_first_name": "Owner", "owner_last_name": "Two", "owner_phone": "2", "workspace_name": "WS2"
    }
    await client.post("/api/v1/organizations/onboarding", json=payload2, headers=headers2)
    await db_session.commit()

    # Query organization details
    repo = OrganizationRepository(db_session)
    org1 = (await db_session.execute(select(Organization).where(Organization.organization_slug == "org-one"))).scalars().first()
    org2 = (await db_session.execute(select(Organization).where(Organization.organization_slug == "org-two"))).scalars().first()

    # Fetch role Teacher
    role1 = (await repo.get_roles(org1.organization_id))[0] # just pick any system role

    # Add member_user to both organizations
    member_service = MemberService(db_session)
    from app.modules.organizations.member_schemas import MemberCreateRequest
    await member_service.create_member(org1.organization_id, MemberCreateRequest(email="member@example.com", first_name="M", last_name="U", role_id=role1.role_id, workspace_ids=[]))
    await member_service.create_member(org2.organization_id, MemberCreateRequest(email="member@example.com", first_name="M", last_name="U", role_id=role1.role_id, workspace_ids=[]))
    await db_session.commit()

    # Verify member has memberships in both organizations
    memberships = await repo.list_memberships(member_user.user_id)
    assert len(memberships) == 2


@pytest.mark.asyncio
async def test_global_roles_seeded_only_once(client: AsyncClient, db_session):
    user_service = UserService(db_session)
    user = await user_service.create_user(email="roles_seed@example.com", password="Password123!")
    await db_session.commit()

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "roles_seed@example.com", "password": "Password123!"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "org_name": "Wayne Enterprises Seed",
        "org_slug": "wayne-ent-seed",
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

    # Onboard
    await client.post("/api/v1/organizations/onboarding", json=payload, headers=headers)
    await db_session.commit()

    # Check database count of global Owner roles
    stmt = select(Role).where(Role.role_organization_id.is_(None), Role.role_name == "Owner")
    res = await db_session.execute(stmt)
    assert len(res.scalars().all()) == 1


@pytest.mark.asyncio
async def test_organization_status_endpoint_scoping(client: AsyncClient, db_session):
    from app.modules.organizations.member_service import MemberService
    from app.modules.organizations.repository import OrganizationRepository

    user_service = UserService(db_session)
    owner = await user_service.create_user(email="status_owner@example.com", password="Password123!")
    member_user = await user_service.create_user(email="status_member@example.com", password="Password123!")
    await db_session.commit()

    # Owner onboards Org
    login_owner = await client.post("/api/v1/auth/login", json={"email": "status_owner@example.com", "password": "Password123!"})
    token_owner = login_owner.json()["access_token"]
    headers_owner = {"Authorization": f"Bearer {token_owner}"}
    payload = {
        "org_name": "Status Org", "org_slug": "status-org", "org_type": "School", "org_country": "USA", "org_state": "CA", "org_city": "LA", "org_timezone": "America/Los_Angeles", "owner_first_name": "Owner", "owner_last_name": "One", "owner_phone": "1", "workspace_name": "WS"
    }
    await client.post("/api/v1/organizations/onboarding", json=payload, headers=headers_owner)
    await db_session.commit()

    # Get Org ID
    org = (await db_session.execute(select(Organization).where(Organization.organization_slug == "status-org"))).scalars().first()

    # Add member_user to Org
    repo = OrganizationRepository(db_session)
    role = (await repo.get_roles(org.organization_id))[0]
    member_service = MemberService(db_session)
    from app.modules.organizations.member_schemas import MemberCreateRequest
    await member_service.create_member(org.organization_id, MemberCreateRequest(email="status_member@example.com", first_name="M", last_name="U", role_id=role.role_id, workspace_ids=[]))
    await db_session.commit()

    # Log in member_user and call status
    login_member = await client.post("/api/v1/auth/login", json={"email": "status_member@example.com", "password": "Password123!"})
    token_member = login_member.json()["access_token"]
    headers_member = {"Authorization": f"Bearer {token_member}"}

    # Member is not an owner, status should return has_organization = False
    status_res = await client.get("/api/v1/organizations/status", headers=headers_member)
    assert status_res.status_code == 200
    assert status_res.json()["has_organization"] is False
