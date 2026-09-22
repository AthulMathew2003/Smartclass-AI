import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class MaterialUploadUrlRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Title of the course material")
    description: Optional[str] = Field(None, max_length=5000, description="Optional description of the material")
    category: str = Field("Notes", min_length=1, max_length=100, description="Category name (e.g. Notes, Lecture, Reference, Lab)")
    original_filename: str = Field(..., min_length=1, max_length=255, description="Client filename with extension")
    content_type: str = Field(..., min_length=1, max_length=100, description="MIME content type")
    file_size: int = Field(..., gt=0, description="File size in bytes")


class MaterialUploadUrlResponse(BaseModel):
    material_id: uuid.UUID
    s3_key: str
    upload_url: str
    expires_in: int = 900


class MaterialConfirmRequest(BaseModel):
    s3_key: str = Field(..., min_length=1, description="Uploaded S3 object key to confirm")


class MaterialUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    category: Optional[str] = Field(None, min_length=1, max_length=100)


class MaterialUploaderSummary(BaseModel):
    user_id: uuid.UUID
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MaterialResponse(BaseModel):
    material_id: uuid.UUID
    subject_id: uuid.UUID
    title: str
    description: Optional[str] = None
    category: str
    original_filename: str
    content_type: str
    file_size: int
    status: str
    s3_key: str
    uploaded_by: Optional[MaterialUploaderSummary] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MaterialDownloadUrlResponse(BaseModel):
    download_url: str
    expires_in: int = 900
    original_filename: str
    content_type: str
