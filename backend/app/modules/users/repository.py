import uuid
from typing import Optional
from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.models import User, UserStatus


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> Optional[User]:
        """Fetch a user by email address, ignoring deleted users."""
        stmt = select(User).where(
            User.user_email == email.lower().strip(),
            User.user_status != UserStatus.DELETED
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Fetch a user by user_id UUID, ignoring deleted users."""
        stmt = select(User).where(
            User.user_id == user_id,
            User.user_status != UserStatus.DELETED
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create(
        self,
        email: str,
        password_hash: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        profile_image: Optional[str] = None,
        phone: Optional[str] = None,
        email_verified: bool = False
    ) -> User:
        """Create a new user in the database."""
        user = User(
            user_email=email.lower().strip(),
            user_password_hash=password_hash,
            user_first_name=first_name,
            user_last_name=last_name,
            user_profile_image=profile_image,
            user_phone=phone,
            user_email_verified=email_verified,
            user_status=UserStatus.ACTIVE
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def update(self, user: User, **kwargs) -> User:
        """Update fields of an existing user."""
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        await self.db.flush()
        return user

    async def exists(self, email: str) -> bool:
        """Check if a user exists with the given email address."""
        stmt = select(exists().where(
            User.user_email == email.lower().strip(),
            User.user_status != UserStatus.DELETED
        ))
        result = await self.db.execute(stmt)
        return bool(result.scalar())
