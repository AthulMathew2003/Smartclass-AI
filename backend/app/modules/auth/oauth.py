import base64
import hashlib
import secrets
import urllib.parse
from typing import Tuple
import httpx
from app.core.config import settings


def generate_state() -> str:
    """Generate a high-entropy cryptographically secure state parameter."""
    return secrets.token_urlsafe(32)


def generate_pkce() -> Tuple[str, str]:
    """
    Generate PKCE code verifier and code challenge.
    Returns: (code_verifier, code_challenge)
    """
    code_verifier = secrets.token_urlsafe(64)
    hashed = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = (
        base64.urlsafe_b64encode(hashed)
        .decode("ascii")
        .replace("=", "")
    )
    return code_verifier, code_challenge


def build_google_url(state: str, code_challenge: str) -> str:
    """Generate authorization redirect URL for Google OAuth."""
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)


def build_github_url(state: str) -> str:
    """Generate authorization redirect URL for GitHub OAuth."""
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
        "scope": "user:email",
        "state": state,
    }
    return "https://github.com/login/oauth/authorize?" + urllib.parse.urlencode(params)


async def exchange_google_code(code: str, code_verifier: str) -> dict:
    """Exchange authorization code for access/refresh tokens with Google."""
    url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
        "code_verifier": code_verifier,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=data)
        response.raise_for_status()
        return response.json()


async def exchange_github_code(code: str) -> dict:
    """Exchange authorization code for access token with GitHub."""
    url = "https://github.com/login/oauth/access_token"
    headers = {"Accept": "application/json"}
    data = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "client_secret": settings.GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()
