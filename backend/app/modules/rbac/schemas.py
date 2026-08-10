import uuid
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    permission_id: uuid.UUID
    permission_name: str
    permission_description: Optional[str] = None
    category: str


class PermissionGroupResponse(BaseModel):
    category: str
    permissions: List[PermissionResponse]


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role_id: uuid.UUID
    role_name: str
    role_description: Optional[str] = None
    role_is_system: bool
    role_organization_id: Optional[uuid.UUID] = None
    member_count: int = 0
    permissions: List[PermissionResponse] = []


class RoleCreateRequest(BaseModel):
    role_name: str = Field(..., min_length=2, max_length=100)
    role_description: Optional[str] = Field(None, max_length=500)
    permission_ids: List[uuid.UUID] = []


class RoleUpdateRequest(BaseModel):
    role_name: Optional[str] = Field(None, min_length=2, max_length=100)
    role_description: Optional[str] = Field(None, max_length=500)
    permission_ids: Optional[List[uuid.UUID]] = None


class MyPermissionsResponse(BaseModel):
    organization_id: uuid.UUID
    permissions: List[str]
