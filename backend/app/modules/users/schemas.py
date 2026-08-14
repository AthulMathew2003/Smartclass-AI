import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict
from app.modules.users.models import UserStatus


class UserBase(BaseModel):
    user_email: EmailStr
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None
    user_profile_image: Optional[str] = None
    user_phone: Optional[str] = None


class UserResponse(UserBase):
    user_id: uuid.UUID
    user_email_verified: bool
    user_status: UserStatus
    user_last_login_at: Optional[datetime] = None
    user_created_at: datetime
    user_updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserInfo(BaseModel):
    id: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_image: Optional[str] = None
    profile_image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
