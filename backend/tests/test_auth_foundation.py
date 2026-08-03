import pytest
from datetime import datetime, timezone, timedelta
from app.modules.users.models import User, UserStatus
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService
from app.modules.auth.models import OAuthProvider
from app.modules.auth.service import AuthService
from app.modules.auth.jwt import (
    create_access_token,
    decode_access_token,
    create_refresh_token,
    hash_refresh_token,
)
from app.modules.auth.oauth import generate_state, generate_pkce
from app.core.exceptions import ConflictException, NotFoundException
from app.core.security import verify_password


@pytest.mark.asyncio
async def test_user_repository_and_service(db_session):
    user_service = UserService(db_session)
    user_repo = UserRepository(db_session)

    # 1. Test create user via service
    email = "test@example.com"
    password = "SecurePassword123!"
    user = await user_service.create_user(
        email=email,
        password=password,
        first_name="Alice",
        last_name="Smith"
    )

    assert user.user_id is not None
    assert user.user_email == email
    assert verify_password(password, user.user_password_hash) is True
    assert user.user_status == UserStatus.ACTIVE

    # Commit transactions in test scope
    await db_session.commit()

    # 2. Test duplicate user creation throws ConflictException
    with pytest.raises(ConflictException):
        await user_service.create_user(email=email, password=password)

    # 3. Test Repository exists check
    assert await user_repo.exists(email) is True
    assert await user_repo.exists("nonexistent@example.com") is False

    # 4. Test Repository get checks
    user_by_email = await user_repo.get_by_email(email)
    assert user_by_email is not None
    assert user_by_email.user_id == user.user_id

    user_by_id = await user_repo.get_by_id(user.user_id)
    assert user_by_id is not None
    assert user_by_id.user_email == email

    # 5. Test Update user properties
    updated_user = await user_repo.update(user, user_first_name="Bob", user_phone="1234567890")
    assert updated_user.user_first_name == "Bob"
    assert updated_user.user_phone == "1234567890"


@pytest.mark.asyncio
async def test_auth_services_and_tokens(db_session):
    user_service = UserService(db_session)
    auth_service = AuthService(db_session)

    # Create dummy user
    user = await user_service.create_user(email="auth_test@example.com", password="Password1!")
    await db_session.commit()

    # 1. Create access token and decode it
    access_token = create_access_token(subject=str(user.user_id), email=user.user_email)
    decoded = decode_access_token(access_token)
    assert decoded is not None
    assert decoded["sub"] == str(user.user_id)
    assert decoded["email"] == user.user_email

    # 2. Create refresh token and verify DB entry
    raw_rt, rt_hash, expires_at = create_refresh_token(subject=str(user.user_id))
    db_token = await auth_service.create_refresh_token(
        user_id=user.user_id,
        token_hash=rt_hash,
        expires_at=expires_at
    )
    await db_session.commit()

    assert db_token.refresh_token_hash == rt_hash
    assert db_token.refresh_token_user_id == user.user_id

    # 3. Revoke token
    await auth_service.revoke_refresh_token(rt_hash)
    await db_session.commit()

    # Revoking again should raise NotFoundException
    with pytest.raises(NotFoundException):
        await auth_service.revoke_refresh_token(rt_hash)

    # 4. Link OAuth Account
    oauth = await auth_service.link_oauth(
        user_id=user.user_id,
        provider=OAuthProvider.GOOGLE,
        provider_user_id="google-id-12345"
    )
    await db_session.commit()

    assert oauth.oauth_account_provider == OAuthProvider.GOOGLE
    assert oauth.oauth_account_provider_user_id == "google-id-12345"
    assert oauth.oauth_account_user_id == user.user_id

    # Linking the same provider profile again raises ConflictException
    with pytest.raises(ConflictException):
        await auth_service.link_oauth(
            user_id=user.user_id,
            provider=OAuthProvider.GOOGLE,
            provider_user_id="google-id-12345"
        )


def test_oauth_utility_helpers():
    state = generate_state()
    assert len(state) > 10

    verifier, challenge = generate_pkce()
    assert len(verifier) > 10
    assert len(challenge) > 10
