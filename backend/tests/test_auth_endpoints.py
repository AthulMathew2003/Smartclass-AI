import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_login_flow(client: AsyncClient):
    # 1. Register Owner
    reg_payload = {
        "email": "owner@example.com",
        "password": "SecretPassword123!",
        "first_name": "Julius",
        "last_name": "Sterling"
    }
    response = await client.post("/api/v1/auth/register", json=reg_payload)
    assert response.status_code == 200
    res_json = response.json()
    assert "access_token" in res_json
    assert res_json["user"]["email"] == "owner@example.com"

    # Save token for me/profile test
    access_token = res_json["access_token"]

    # 2. Duplicate registration check
    response_dup = await client.post("/api/v1/auth/register", json=reg_payload)
    assert response_dup.status_code == 409

    # 3. Login
    login_payload = {
        "email": "owner@example.com",
        "password": "SecretPassword123!"
    }
    response_login = await client.post("/api/v1/auth/login", json=login_payload)
    assert response_login.status_code == 200
    assert "access_token" in response_login.json()

    # Invalid login credentials check
    login_payload_invalid = {
        "email": "owner@example.com",
        "password": "WrongPassword!"
    }
    response_invalid = await client.post("/api/v1/auth/login", json=login_payload_invalid)
    assert response_invalid.status_code == 401

    # 4. Get Current User /me
    headers = {"Authorization": f"Bearer {access_token}"}
    response_me = await client.get("/api/v1/auth/me", headers=headers)
    assert response_me.status_code == 200
    assert response_me.json()["email"] == "owner@example.com"


@pytest.mark.asyncio
async def test_validation_endpoints(client: AsyncClient):
    # 1. Check email uniqueness
    response_email = await client.get("/api/v1/auth/check-email?email=check_unique@example.com")
    assert response_email.status_code == 200
    assert response_email.json() == {"available": True}

    # 2. Check organization name/slug availability
    response_name = await client.get("/api/v1/organizations/check-name?name=Stark Academy")
    assert response_name.status_code == 200
    assert response_name.json() == {"available": True}

    response_slug = await client.get("/api/v1/organizations/check-slug?slug=stark-academy")
    assert response_slug.status_code == 200
    assert response_slug.json() == {"available": True}


@pytest.mark.asyncio
async def test_suspended_user_flow(client: AsyncClient, db_session):
    from app.modules.users.service import UserService
    from app.modules.users.models import UserStatus
    from app.modules.users.repository import UserRepository

    user_service = UserService(db_session)
    user_repo = UserRepository(db_session)

    # 1. Create a user
    user = await user_service.create_user(email="suspended@example.com", password="Password123!")
    await db_session.commit()

    # 2. Try logging in (should succeed)
    login_payload = {
        "email": "suspended@example.com",
        "password": "Password123!"
    }
    response_ok = await client.post("/api/v1/auth/login", json=login_payload)
    assert response_ok.status_code == 200
    assert "access_token" in response_ok.json()

    # 3. Suspend user
    await user_repo.update(user, user_status=UserStatus.SUSPENDED)
    await db_session.commit()

    # 4. Try logging in again (should fail with 403)
    response_fail = await client.post("/api/v1/auth/login", json=login_payload)
    assert response_fail.status_code == 403
    assert "suspended" in response_fail.json()["message"].lower()

    # 5. Try calling protected endpoint /me using the old token (should fail with 401)
    old_token = response_ok.json()["access_token"]
    headers = {"Authorization": f"Bearer {old_token}"}
    response_me = await client.get("/api/v1/auth/me", headers=headers)
    assert response_me.status_code == 401
    assert "suspended" in response_me.json()["message"].lower()
