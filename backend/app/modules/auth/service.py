import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.auth.models import OAuthAccount, OAuthProvider, RefreshToken
from app.modules.auth.repository import AuthRepository
from app.core.exceptions import ConflictException, NotFoundException


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AuthRepository(db)

    async def link_oauth(
        self,
        user_id: uuid.UUID,
        provider: OAuthProvider,
        provider_user_id: str
    ) -> OAuthAccount:
        """Link an OAuth account profile, raising an error if already linked elsewhere."""
        existing = await self.repo.get_oauth_account(provider, provider_user_id)
        if existing:
            raise ConflictException("This external account is already linked to a user.")

        return await self.repo.create_oauth_account(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id
        )

    async def create_refresh_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime
    ) -> RefreshToken:
        """Create and commit a refresh token row."""
        return await self.repo.create_refresh_token(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at
        )

    async def revoke_refresh_token(self, token_hash: str) -> None:
        """Locate and revoke a valid refresh token using its hashed representation."""
        token = await self.repo.get_refresh_token_by_hash(token_hash)
        if not token:
            raise NotFoundException("Active token not found or already revoked.")
        await self.repo.revoke_refresh_token(token)
