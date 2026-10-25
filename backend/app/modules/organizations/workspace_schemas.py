import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.modules.organizations.models import WorkspaceStatus


class WorkspaceCreateRequest(BaseModel):
    workspace_name: str = Field(..., min_length=2, max_length=255)
    workspace_description: Optional[str] = Field(None, max_length=1000)


class WorkspaceUpdateRequest(BaseModel):
    workspace_name: Optional[str] = Field(None, min_length=2, max_length=255)
    workspace_description: Optional[str] = Field(None, max_length=1000)
    workspace_status: Optional[WorkspaceStatus] = None


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: uuid.UUID
    workspace_organization_id: uuid.UUID
    workspace_name: str
    workspace_description: Optional[str] = None
    workspace_banner: Optional[str] = None
    workspace_status: WorkspaceStatus
    workspace_created_by: uuid.UUID
    workspace_created_at: datetime
    workspace_updated_at: datetime
    member_count: int = 0
    student_count: int = 0
    subject_count: int = 0


class WorkspaceStudentItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    status: Optional[str] = "active"
    joined_at: Optional[datetime] = None


class WorkspaceStudentsData(BaseModel):
    items: List[WorkspaceStudentItem] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1


class WorkspaceStudentsResponse(BaseModel):
    success: bool = True
    message: str = "Workspace students retrieved successfully"
    data: WorkspaceStudentsData
    request_id: Optional[str] = None
