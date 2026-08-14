import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.modules.assignments.models import AssignmentStatus, SubmissionStatus


class AssignmentCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    subject_id: uuid.UUID = Field(..., alias="assignment_subject_id")
    assignment_title: str = Field(..., min_length=1, max_length=255, alias="title", description="Title of the assignment")
    assignment_description: Optional[str] = Field(None, alias="description", description="Detailed instructions or description")
    assignment_status: Optional[AssignmentStatus] = Field(AssignmentStatus.DRAFT, alias="status", description="Initial assignment status")
    assignment_due_at: Optional[datetime] = Field(None, alias="due_at", description="Due date and time (UTC)")


class AssignmentUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    assignment_title: Optional[str] = Field(None, min_length=1, max_length=255, alias="title")
    assignment_description: Optional[str] = Field(None, alias="description")
    assignment_status: Optional[AssignmentStatus] = Field(None, alias="status")
    assignment_due_at: Optional[datetime] = Field(None, alias="due_at")


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
