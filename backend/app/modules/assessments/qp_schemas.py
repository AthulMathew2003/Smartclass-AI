"""
Pydantic schemas for Question Paper Generation (Step 10.16).

All request / response models are fully typed and validated.
Internal generation metadata (prompts, raw Gemini responses) is never
included in API responses.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Enums ──────────────────────────────────────────────────────

class QpDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    MIXED = "mixed"


class QpQuestionType(str, Enum):
    MCQ_SINGLE = "mcq_single"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"


class QpDraftStatus(str, Enum):
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    CONVERTED = "converted"


# ── Section Config ──────────────────────────────────────────────

class QpSectionConfig(BaseModel):
    """Optional paper section (e.g. Part A, Part B)."""
    section_title: str = Field(..., min_length=1, max_length=100)
    section_instructions: Optional[str] = Field(None, max_length=2000)
    question_types: List[QpQuestionType]
    question_count: int = Field(..., ge=1, le=50)
    marks_per_question: Optional[float] = Field(None, gt=0, le=100)
    difficulty: Optional[QpDifficulty] = QpDifficulty.MIXED


# ── Generation Config ───────────────────────────────────────────

class QpGenerateRequest(BaseModel):
    """Full configuration for generating a question paper draft."""

    # Paper metadata
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)

    # Source materials — validated server-side to belong to the subject
    material_ids: List[uuid.UUID] = Field(..., min_length=1, max_length=20)

    # Optional topic/chapter focus
    topics: Optional[List[str]] = Field(
        None, max_length=10,
        description="Optional list of topics or chapters to focus on"
    )

    # Paper dimensions
    total_marks: float = Field(..., gt=0, le=500)
    duration_minutes: Optional[int] = Field(None, ge=10, le=1440)

    # Overall difficulty distribution
    difficulty: QpDifficulty = QpDifficulty.MIXED

    # Simple flat configuration — either total_questions OR sections
    total_questions: Optional[int] = Field(None, ge=1, le=100)
    question_types: Optional[List[QpQuestionType]] = Field(
        None, description="If flat config, which question types to include"
    )

    # Optional section-wise configuration (overrides flat config)
    sections: Optional[List[QpSectionConfig]] = Field(None, max_length=10)

    # Answer key and rubric generation
    generate_answer_key: bool = True
    generate_rubrics: bool = True

    # Custom instructions for generation
    additional_instructions: Optional[str] = Field(
        None, max_length=1000,
        description="Extra guidance such as topics to emphasize or avoid"
    )

    @field_validator("material_ids")
    @classmethod
    def validate_material_ids(cls, v: List[uuid.UUID]) -> List[uuid.UUID]:
        if len(set(str(m) for m in v)) != len(v):
            raise ValueError("Duplicate material IDs are not allowed.")
        return v

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Title cannot be empty or whitespace only.")
        return stripped

    @model_validator(mode="after")
    def validate_config(self) -> "QpGenerateRequest":
        if self.sections is None and self.total_questions is None:
            raise ValueError(
                "Either 'total_questions' or 'sections' must be provided."
            )
        if self.sections is None and self.question_types is None:
            raise ValueError(
                "Either 'sections' or 'question_types' must be provided for flat config."
            )
        return self


# ── Draft Question Schemas ──────────────────────────────────────

class QpOptionInput(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    is_correct: bool = False


class QpDraftQuestionUpdateInput(BaseModel):
    """Used by teachers when editing a single question in the draft."""
    question_text: Optional[str] = Field(None, min_length=1, max_length=10000)
    marks: Optional[float] = Field(None, gt=0, le=100)
    difficulty: Optional[QpDifficulty] = None
    options: Optional[List[QpOptionInput]] = Field(None, max_length=10)
    expected_answer: Optional[str] = Field(None, max_length=5000)
    rubric: Optional[str] = Field(None, max_length=5000)
    explanation: Optional[str] = Field(None, max_length=5000)
    is_flagged: Optional[bool] = None


class QpRegenerateQuestionRequest(BaseModel):
    """Regenerate one question, optionally overriding type or difficulty."""
    question_type: Optional[QpQuestionType] = None
    difficulty: Optional[QpDifficulty] = None
    marks: Optional[float] = Field(None, gt=0, le=100)
    additional_instructions: Optional[str] = Field(None, max_length=500)


# ── Convert Draft → Assessment ──────────────────────────────────

class QpConvertRequest(BaseModel):
    """Convert an approved draft to a SmartClass assessment."""
    assessment_type: str = Field("exam", description="quiz | exam | practice")
    passing_marks: Optional[float] = Field(None, ge=0)
    attempt_limit: int = Field(1, ge=1, le=10)
    randomize_questions: bool = False
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None


# ── Response Schemas ────────────────────────────────────────────

class QpSourceChunk(BaseModel):
    material_id: uuid.UUID
    material_title: str
    chunk_index: int
    page_number: Optional[int] = None
    slide_number: Optional[int] = None
    content_preview: str = ""  # First ~150 chars for teacher reference


class QpDraftQuestionResponse(BaseModel):
    dq_id: uuid.UUID
    dq_order: int
    dq_question_type: str
    dq_question_text: str
    dq_marks: float
    dq_difficulty: str
    dq_options: Optional[List[Dict[str, Any]]] = None
    dq_expected_answer: Optional[str] = None  # Teacher-only
    dq_rubric: Optional[str] = None            # Teacher-only
    dq_explanation: Optional[str] = None       # Teacher-only
    dq_source_material_ids: List[str] = []
    dq_source_chunks: Optional[List[Any]] = None  # Teacher-only
    dq_is_flagged: bool = False
    dq_created_at: datetime
    dq_updated_at: datetime

    model_config = {"from_attributes": True}


class QpValidationIssue(BaseModel):
    severity: str  # "error" | "warning"
    question_index: Optional[int] = None
    message: str


class QpValidationResult(BaseModel):
    is_valid: bool
    total_marks_actual: float
    total_marks_expected: float
    question_count_actual: int
    issues: List[QpValidationIssue] = []
    flagged_count: int = 0


class QpMaterialSummary(BaseModel):
    material_id: uuid.UUID
    title: str
    original_filename: str
    index_status: str
    chunk_count: int


class QpDraftResponse(BaseModel):
    draft_id: uuid.UUID
    draft_subject_id: uuid.UUID
    draft_title: str
    draft_description: Optional[str] = None
    draft_status: str
    draft_config: Dict[str, Any]
    draft_validation_result: Optional[Dict[str, Any]] = None
    draft_generation_error: Optional[str] = None
    draft_converted_assessment_id: Optional[uuid.UUID] = None
    draft_created_at: datetime
    draft_updated_at: datetime
    questions: List[QpDraftQuestionResponse] = []
    # Enriched
    subject_name: Optional[str] = None
    material_summaries: Optional[List[QpMaterialSummary]] = None

    model_config = {"from_attributes": True}


class QpDraftListItem(BaseModel):
    draft_id: uuid.UUID
    draft_subject_id: uuid.UUID
    draft_title: str
    draft_status: str
    question_count: int
    total_marks: Optional[float] = None
    draft_converted_assessment_id: Optional[uuid.UUID] = None
    draft_created_at: datetime
    draft_updated_at: datetime

    model_config = {"from_attributes": True}


# ── Subject Materials for Selection ────────────────────────────

class QpMaterialListResponse(BaseModel):
    """List of subject materials available for question paper generation."""
    subject_id: uuid.UUID
    subject_name: str
    materials: List[QpMaterialSummary]
