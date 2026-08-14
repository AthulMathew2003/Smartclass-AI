import uuid
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class MemberCreateRequest(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    role_id: uuid.UUID
    workspace_ids: List[uuid.UUID] = []
    # Profile photo upload info (required by frontend, optional in schema for flexibility)
    content_type: Optional[str] = None
    file_size: Optional[int] = None


class MemberUpdateRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    role_id: uuid.UUID


class MemberStatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(active|suspended)$")


class WorkspaceBrief(BaseModel):
    workspace_id: uuid.UUID
    workspace_name: str


class MemberResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    profile_image_url: Optional[str] = None
    organization_member_id: uuid.UUID
    status: str
    role_id: uuid.UUID
    role_name: str
    workspaces: List[WorkspaceBrief] = []


class ProfilePhotoUploadInfo(BaseModel):
    key: str
    upload_url: str
    expires_in: int


class MemberCreateResponse(MemberResponse):
    profile_photo_upload: Optional[ProfilePhotoUploadInfo] = None


class ProfilePhotoConfirmRequest(BaseModel):
    key: str = Field(..., min_length=1)


class ProfilePhotoUploadRequest(BaseModel):
    content_type: str = Field(..., min_length=1)
    file_size: int = Field(..., gt=0)


class WorkspaceResponse(BaseModel):
    workspace_id: uuid.UUID
    workspace_name: str
    workspace_description: Optional[str] = None
    workspace_status: str
