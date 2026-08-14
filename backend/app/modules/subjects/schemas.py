import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.modules.subjects.models import SubjectStatus


class SubjectCreateRequest(BaseModel):
    workspace_id: uuid.UUID
    subject_name: str = Field(..., min_length=2, max_length=255)
    subject_description: Optional[str] = Field(None, max_length=1000)


class SubjectUpdateRequest(BaseModel):
    subject_name: Optional[str] = Field(None, min_length=2, max_length=255)
    subject_description: Optional[str] = Field(None, max_length=1000)


class SubjectTeacherAddRequest(BaseModel):
    user_id: uuid.UUID


class SubjectTeacherResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subject_teacher_id: uuid.UUID
    subject_teacher_subject_id: uuid.UUID
    subject_teacher_user_id: uuid.UUID
    subject_teacher_assigned_at: datetime
    user_email: Optional[str] = None
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None


class SubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subject_id: uuid.UUID
    subject_workspace_id: uuid.UUID
    subject_name: str
    subject_description: Optional[str] = None
    subject_status: SubjectStatus
    subject_created_by: Optional[uuid.UUID] = None
    subject_created_at: datetime
    subject_updated_at: datetime
    teacher_count: int = 0
    teachers: List[SubjectTeacherResponse] = Field(default_factory=list)
