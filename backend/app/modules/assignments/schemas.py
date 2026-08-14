import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, AliasChoices
from app.modules.assignments.models import AssignmentStatus, SubmissionStatus


class AssignmentCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    subject_id: uuid.UUID = Field(..., validation_alias=AliasChoices("subject_id", "assignment_subject_id"))
    assignment_title: str = Field(..., min_length=1, max_length=255, validation_alias=AliasChoices("title", "assignment_title"), description="Title of the assignment")
    assignment_description: Optional[str] = Field(None, validation_alias=AliasChoices("description", "assignment_description"), description="Detailed instructions or description")
    assignment_status: Optional[AssignmentStatus] = Field(AssignmentStatus.DRAFT, validation_alias=AliasChoices("status", "assignment_status"), description="Initial assignment status")
    assignment_due_at: Optional[datetime] = Field(None, validation_alias=AliasChoices("due_at", "assignment_due_at"), description="Due date and time (UTC)")


class AssignmentUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    assignment_title: Optional[str] = Field(None, min_length=1, max_length=255, validation_alias=AliasChoices("title", "assignment_title"))
    assignment_description: Optional[str] = Field(None, validation_alias=AliasChoices("description", "assignment_description"))
    assignment_due_at: Optional[datetime] = Field(None, validation_alias=AliasChoices("due_at", "assignment_due_at"))


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    assignment_id: uuid.UUID
    assignment_subject_id: uuid.UUID
    assignment_title: str
    assignment_description: Optional[str] = None
    assignment_status: AssignmentStatus
    assignment_due_at: Optional[datetime] = None
    assignment_created_by: Optional[uuid.UUID] = None
    assignment_created_at: datetime
    assignment_updated_at: datetime


class AttachmentUploadUrlRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., min_length=1, max_length=100)
    file_size: int = Field(..., gt=0)


class AttachmentUploadUrlResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    attachment_id: uuid.UUID
    s3_key: str
    upload_url: str
    expires_in: int = 900


class AttachmentConfirmRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    attachment_id: uuid.UUID
    s3_key: str
    original_filename: str = Field(..., min_length=1, max_length=255, validation_alias=AliasChoices("original_filename", "filename", "attachment_original_filename"))
    content_type: str = Field(..., min_length=1, max_length=100, validation_alias=AliasChoices("content_type", "attachment_content_type"))
    file_size: int = Field(..., gt=0, validation_alias=AliasChoices("file_size", "size", "attachment_size"))


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    attachment_id: uuid.UUID
    assignment_id: uuid.UUID = Field(..., validation_alias=AliasChoices("assignment_id", "attachment_assignment_id"))
    original_filename: str = Field(..., validation_alias=AliasChoices("original_filename", "attachment_original_filename"))
    content_type: str = Field(..., validation_alias=AliasChoices("content_type", "attachment_content_type"))
    size: int = Field(..., validation_alias=AliasChoices("size", "attachment_size"))
    created_by: Optional[uuid.UUID] = Field(None, validation_alias=AliasChoices("created_by", "attachment_created_by"))
    created_at: datetime = Field(..., validation_alias=AliasChoices("created_at", "attachment_created_at"))


class AttachmentDownloadUrlResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    attachment_id: uuid.UUID
    original_filename: str
    download_url: str
    expires_in: int = 900


class SubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    submission_id: uuid.UUID
    submission_assignment_id: uuid.UUID
    submission_student_id: uuid.UUID
    submission_status: SubmissionStatus
    submission_submitted_at: Optional[datetime] = None
    submission_grade: Optional[float] = None
    submission_feedback: Optional[str] = None
    submission_graded_by: Optional[uuid.UUID] = None
    submission_graded_at: Optional[datetime] = None
    submission_created_at: datetime
    submission_updated_at: datetime
