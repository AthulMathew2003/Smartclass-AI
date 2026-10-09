import uuid
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict


class AiTutorSourceItem(BaseModel):
    material_id: uuid.UUID
    title: str
    filename: str
    page_number: Optional[int] = None
    slide_number: Optional[int] = None


class AiTutorMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    sources: Optional[List[AiTutorSourceItem]] = None
    created_at: datetime


class AiTutorConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversation_id: uuid.UUID
    subject_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class AiTutorConversationDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversation_id: uuid.UUID
    subject_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[AiTutorMessageResponse] = []


class AiTutorCreateConversationRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255)


class AiTutorSendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class AiTutorSendMessageResponse(BaseModel):
    user_message: AiTutorMessageResponse
    assistant_message: AiTutorMessageResponse
