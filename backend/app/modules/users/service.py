from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.core.exceptions import ConflictException
from app.core.security import hash_password


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)

    async def create_user(
        self,
        email: str,
        password: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        profile_image: Optional[str] = None,
        phone: Optional[str] = None,
        email_verified: bool = False
    ) -> User:
        """Create a new user, hashing their password if provided."""
        if await self.repo.exists(email):
            raise ConflictException("Email already exists.")

        pwd_hash = hash_password(password) if password else None

        user = await self.repo.create(
            email=email,
            password_hash=pwd_hash,
            first_name=first_name,
            last_name=last_name,
            profile_image=profile_image,
            phone=phone,
            email_verified=email_verified
        )
        return user
