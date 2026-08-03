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
