import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
from jose import jwt, JWTError
from app.core.config import settings


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token string using SHA-256 before database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(subject: str, email: str, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a short-lived JWT Access Token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "email": email,
        "type": "access"
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT Access Token, returning the payload if valid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def create_refresh_token(subject: str) -> Tuple[str, str, datetime]:
    """
    Generate a secure random refresh token, its SHA-256 hash, and its expiration.
    Returns: (raw_refresh_token, token_hash, expires_at)
    """
    raw_token = secrets.token_urlsafe(64)
    token_hash = hash_refresh_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return raw_token, token_hash, expires_at
