import secrets
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Response, Request, Query, status
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.db.session import get_db
from app.core.config import settings
from app.core.security import verify_password
from app.core.exceptions import UnauthorizedException, ConflictException, NotFoundException
from app.modules.users.schemas import UserInfo
from app.modules.users.models import User, UserStatus
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService
from app.modules.auth.models import OAuthProvider
from app.modules.auth.schemas import RegisterRequest, LoginRequest, TokenResponse
from app.modules.auth.repository import AuthRepository
from app.modules.auth.service import AuthService
from app.modules.auth.jwt import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    decode_access_token,
)
from app.modules.auth.oauth import (
    generate_state,
    generate_pkce,
    build_google_url,
    build_github_url,
    exchange_google_code,
    exchange_github_code,
)
from app.modules.auth.dependencies import get_current_user

router = APIRouter()

COOKIE_REFRESH = "refresh_token"
COOKIE_OAUTH_STATE = "oauth_state"
COOKIE_OAUTH_PKCE = "oauth_pkce"


def _set_refresh_cookie(response: Response, token: str, expires_at: datetime):
    max_age = int((expires_at - datetime.now(timezone.utc)).total_seconds())
    response.set_cookie(
        key=COOKIE_REFRESH,
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=max_age,
        path="/"
    )


def _clear_refresh_cookie(response: Response):
    response.delete_cookie(
        key=COOKIE_REFRESH,
        path="/",
        secure=True,
        samesite="none"
    )


@router.post("/register", response_model=TokenResponse)
async def register(payload: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """Register a new Organization Owner."""
    user_service = UserService(db)
    auth_service = AuthService(db)

    # 1. Create user
    user = await user_service.create_user(
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name
    )

    # 2. Issue session tokens
    access_token = create_access_token(subject=str(user.user_id), email=user.user_email)
    raw_rt, rt_hash, expires_at = create_refresh_token(subject=str(user.user_id))

    await auth_service.create_refresh_token(user_id=user.user_id, token_hash=rt_hash, expires_at=expires_at)
    await db.commit()

    _set_refresh_cookie(response, raw_rt, expires_at)

    user_info = UserInfo(
        id=str(user.user_id),
        email=user.user_email,
        first_name=user.user_first_name,
        last_name=user.user_last_name,
        profile_image=user.user_profile_image
    )
    return TokenResponse(access_token=access_token, user=user_info)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """Authenticate and log in with Email & Password."""
    user_repo = UserRepository(db)
    auth_service = AuthService(db)

    user = await user_repo.get_by_email(payload.email)
    if not user or not user.user_password_hash:
        raise UnauthorizedException("Invalid email or password.")

    if not verify_password(payload.password, user.user_password_hash):
        raise UnauthorizedException("Invalid email or password.")

    # Update last login
    await user_repo.update(user, user_last_login_at=datetime.now(timezone.utc))

    # Issue session tokens
    access_token = create_access_token(subject=str(user.user_id), email=user.user_email)
    raw_rt, rt_hash, expires_at = create_refresh_token(subject=str(user.user_id))

    await auth_service.create_refresh_token(user_id=user.user_id, token_hash=rt_hash, expires_at=expires_at)
    await db.commit()

    _set_refresh_cookie(response, raw_rt, expires_at)

    user_info = UserInfo(
        id=str(user.user_id),
        email=user.user_email,
        first_name=user.user_first_name,
        last_name=user.user_last_name,
        profile_image=user.user_profile_image
    )
    return TokenResponse(access_token=access_token, user=user_info)


@router.get("/google")
async def google_login(action: str = Query("login")):
    """Redirect to Google's OAuth consent screen."""
    state_rand = secrets.token_urlsafe(16)
    state = f"{action}:{state_rand}"
    verifier, challenge = generate_pkce()

    url = build_google_url(state=state, code_challenge=challenge)
    response = RedirectResponse(url=url)
    
    # Store state and PKCE verifier in HttpOnly cookies
    response.set_cookie(key=COOKIE_OAUTH_STATE, value=state, httponly=True, max_age=600, path="/")
    response.set_cookie(key=COOKIE_OAUTH_PKCE, value=verifier, httponly=True, max_age=600, path="/")
    return response


@router.get("/google/callback")
async def google_callback(
    request: Request,
    response: Response,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Handle Google OAuth callback code exchange."""
    if error or not code:
        err_msg = urllib.parse.quote(error or "Authorization code missing")
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error={err_msg}")

    # Validate state CSRF
    cookie_state = request.cookies.get(COOKIE_OAUTH_STATE)
    if not state or state != cookie_state:
        err_msg = urllib.parse.quote("State verification failed.")
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error={err_msg}")

    action = state.split(":")[0] if ":" in state else "login"
    verifier = request.cookies.get(COOKIE_OAUTH_PKCE)

    try:
        token_data = await exchange_google_code(code=code, code_verifier=verifier)
        
        # Fetch profile
        async with httpx.AsyncClient() as client:
            p_resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token_data['access_token']}"}
            )
            p_resp.raise_for_status()
            profile = p_resp.json()

        email = profile.get("email")
        if not email:
            raise UnauthorizedException("Email permission required from Google profile.")

        user_repo = UserRepository(db)
        auth_service = AuthService(db)
        user = await user_repo.get_by_email(email)

        if not user:
            if action == "register":
                # Create owner account
                user = await user_repo.create(
                    email=email,
                    first_name=profile.get("given_name"),
                    last_name=profile.get("family_name"),
                    profile_image=profile.get("picture"),
                    email_verified=profile.get("email_verified", False)
                )
                await auth_service.link_oauth(user_id=user.user_id, provider=OAuthProvider.GOOGLE, provider_user_id=profile["sub"])
            else:
                # Reject login if no user account exists
                err_msg = urllib.parse.quote("This account isn't associated with any SmartClass AI organization.")
                return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error={err_msg}")
        else:
            # Ensure linked (auto-linking)
            existing_link = await AuthRepository(db).get_oauth_account(OAuthProvider.GOOGLE, profile["sub"])
            if not existing_link:
                await auth_service.link_oauth(user_id=user.user_id, provider=OAuthProvider.GOOGLE, provider_user_id=profile["sub"])

        # Update last login
        await user_repo.update(user, user_last_login_at=datetime.now(timezone.utc))

        # Log in session
        access_token = create_access_token(subject=str(user.user_id), email=user.user_email)
        raw_rt, rt_hash, expires_at = create_refresh_token(subject=str(user.user_id))
        await auth_service.create_refresh_token(user_id=user.user_id, token_hash=rt_hash, expires_at=expires_at)
        await db.commit()

        # Redirect to frontend callback route
        redir_res = RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback")
        _set_refresh_cookie(redir_res, raw_rt, expires_at)
        redir_res.set_cookie(key="initial_access_token", value=access_token, httponly=False, max_age=60, path="/")
        redir_res.delete_cookie(key=COOKIE_OAUTH_STATE, path="/")
        redir_res.delete_cookie(key=COOKIE_OAUTH_PKCE, path="/")
        return redir_res

    except Exception as e:
        err_msg = urllib.parse.quote(str(e))
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error={err_msg}")


@router.get("/github")
async def github_login(action: str = Query("login")):
    """Redirect to GitHub's OAuth consent page."""
    state_rand = secrets.token_urlsafe(16)
    state = f"{action}:{state_rand}"
    
    url = build_github_url(state=state)
    response = RedirectResponse(url=url)
    response.set_cookie(key=COOKIE_OAUTH_STATE, value=state, httponly=True, max_age=600, path="/")
    return response


@router.get("/github/callback")
async def github_callback(
    request: Request,
    response: Response,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Handle GitHub OAuth callback logic."""
    if error or not code:
        err_msg = urllib.parse.quote(error or "Authorization code missing")
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error={err_msg}")

    cookie_state = request.cookies.get(COOKIE_OAUTH_STATE)
    if not state or state != cookie_state:
        err_msg = urllib.parse.quote("State verification failed.")
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error={err_msg}")

    action = state.split(":")[0] if ":" in state else "login"

    try:
        token_data = await exchange_github_code(code=code)
        access_token = token_data.get("access_token")
        if not access_token:
            raise UnauthorizedException("Failed to retrieve access token from GitHub.")

        # Fetch profile
        async with httpx.AsyncClient() as client:
            p_resp = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
            )
            p_resp.raise_for_status()
            profile = p_resp.json()

            # Retrieve email
            email = profile.get("email")
            if not email:
                email_resp = await client.get(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
                )
                email_resp.raise_for_status()
                emails = email_resp.json()
                for email_info in emails:
                    if email_info.get("primary") and email_info.get("verified"):
                        email = email_info.get("email")
                        break
                if not email and emails:
                    email = emails[0].get("email")

        if not email:
            raise UnauthorizedException("Email permission required from GitHub profile.")

        user_repo = UserRepository(db)
        auth_service = AuthService(db)
        user = await user_repo.get_by_email(email)

        provider_user_id = str(profile["id"])

        if not user:
            if action == "register":
                name = profile.get("name") or ""
                name_parts = name.split(" ")
                first_name = name_parts[0] if name_parts else ""
                last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

                user = await user_repo.create(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    profile_image=profile.get("avatar_url"),
                    email_verified=True
                )
                await auth_service.link_oauth(user_id=user.user_id, provider=OAuthProvider.GITHUB, provider_user_id=provider_user_id)
            else:
                err_msg = urllib.parse.quote("This account isn't associated with any SmartClass AI organization.")
                return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error={err_msg}")
        else:
            existing_link = await AuthRepository(db).get_oauth_account(OAuthProvider.GITHUB, provider_user_id)
            if not existing_link:
                await auth_service.link_oauth(user_id=user.user_id, provider=OAuthProvider.GITHUB, provider_user_id=provider_user_id)

        # Update last login
        await user_repo.update(user, user_last_login_at=datetime.now(timezone.utc))

        # Log in session
        access_token = create_access_token(subject=str(user.user_id), email=user.user_email)
        raw_rt, rt_hash, expires_at = create_refresh_token(subject=str(user.user_id))
        await auth_service.create_refresh_token(user_id=user.user_id, token_hash=rt_hash, expires_at=expires_at)
        await db.commit()

        redir_res = RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback")
        _set_refresh_cookie(redir_res, raw_rt, expires_at)
        redir_res.set_cookie(key="initial_access_token", value=access_token, httponly=False, max_age=60, path="/")
        redir_res.delete_cookie(key=COOKIE_OAUTH_STATE, path="/")
        return redir_res

    except Exception as e:
        err_msg = urllib.parse.quote(str(e))
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error={err_msg}")


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    """Rotate and refresh session tokens."""
    raw_rt = request.cookies.get(COOKIE_REFRESH)
    if not raw_rt:
        raise UnauthorizedException("Refresh token missing.")

    rt_hash = hash_refresh_token(raw_rt)
    auth_service = AuthService(db)
    user_repo = UserRepository(db)

    token_row = await auth_service.repo.get_refresh_token_by_hash(rt_hash)
    if not token_row:
        raise UnauthorizedException("Invalid or revoked refresh token.")

    user = await user_repo.get_by_id(token_row.refresh_token_user_id)
    if not user:
        raise UnauthorizedException("User not found.")

    # Revoke old token
    await auth_service.repo.revoke_refresh_token(token_row)

    # Issue new token session
    access_token = create_access_token(subject=str(user.user_id), email=user.user_email)
    raw_new_rt, new_rt_hash, expires_at = create_refresh_token(subject=str(user.user_id))
    await auth_service.create_refresh_token(user_id=user.user_id, token_hash=new_rt_hash, expires_at=expires_at)
    await db.commit()

    _set_refresh_cookie(response, raw_new_rt, expires_at)

    user_info = UserInfo(
        id=str(user.user_id),
        email=user.user_email,
        first_name=user.user_first_name,
        last_name=user.user_last_name,
        profile_image=user.user_profile_image
    )
    return TokenResponse(access_token=access_token, user=user_info)


@router.post("/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    """Log out user, revoking refresh tokens and clearing cookies."""
    raw_rt = request.cookies.get(COOKIE_REFRESH)
    if raw_rt:
        rt_hash = hash_refresh_token(raw_rt)
        auth_service = AuthService(db)
        token_row = await auth_service.repo.get_refresh_token_by_hash(rt_hash)
        if token_row:
            await auth_service.repo.revoke_refresh_token(token_row)
            await db.commit()

    _clear_refresh_cookie(response)
    response.delete_cookie(key="initial_access_token", path="/")
    return {"success": True, "message": "Successfully logged out."}


@router.get("/me", response_model=UserInfo)
async def get_me(current_user: User = Depends(get_current_user)):
    """Fetch current user profile details."""
    return UserInfo(
        id=str(current_user.user_id),
        email=current_user.user_email,
        first_name=current_user.user_first_name,
        last_name=current_user.user_last_name,
        profile_image=current_user.user_profile_image
    )


@router.get("/check-email")
async def check_email(email: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Check email availability."""
    user_repo = UserRepository(db)
    exists_flag = await user_repo.exists(email)
    return {"available": not exists_flag}
