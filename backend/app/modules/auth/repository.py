import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.auth.models import OAuthAccount, OAuthProvider, RefreshToken


class AuthRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_oauth_account(self, provider: OAuthProvider, provider_user_id: str) -> Optional[OAuthAccount]:
        """Fetch an OAuth account by provider and provider's user ID."""
        stmt = select(OAuthAccount).where(
            OAuthAccount.oauth_account_provider == provider,
            OAuthAccount.oauth_account_provider_user_id == provider_user_id
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_oauth_account(
        self,
        user_id: uuid.UUID,
        provider: OAuthProvider,
        provider_user_id: str
    ) -> OAuthAccount:
        """Link a third-party OAuth profile to a user account."""
        oauth_acc = OAuthAccount(
            oauth_account_user_id=user_id,
            oauth_account_provider=provider,
            oauth_account_provider_user_id=provider_user_id
        )
        self.db.add(oauth_acc)
        await self.db.flush()
        return oauth_acc

    async def create_refresh_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime
    ) -> RefreshToken:
        """Store a new refresh token hash in the database."""
        token = RefreshToken(
            refresh_token_user_id=user_id,
            refresh_token_hash=token_hash,
            refresh_token_expires_at=expires_at
        )
        self.db.add(token)
        await self.db.flush()
        return token

    async def get_refresh_token_by_hash(self, token_hash: str) -> Optional[RefreshToken]:
        """Fetch an active, non-expired refresh token by its hash."""
        now = datetime.now(timezone.utc)
        stmt = select(RefreshToken).where(
            RefreshToken.refresh_token_hash == token_hash,
            RefreshToken.refresh_token_revoked_at.is_(None),
            RefreshToken.refresh_token_expires_at > now
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def revoke_refresh_token(self, token: RefreshToken) -> RefreshToken:
        """Mark a refresh token as revoked."""
        token.refresh_token_revoked_at = datetime.now(timezone.utc)
        await self.db.flush()
        return token
