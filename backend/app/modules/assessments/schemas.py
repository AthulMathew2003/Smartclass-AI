import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict, AliasChoices, field_validator, model_validator
from app.modules.assessments.models import AssessmentType, AssessmentStatus, QuestionType, QuestionStatus
from app.core.exceptions import ValidationException


# ── Assessment Schemas ──────────────────────────────────────────

class AssessmentCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    subject_id: uuid.UUID = Field(..., validation_alias=AliasChoices("subject_id", "assessment_subject_id"))
    title: str = Field(..., min_length=1, max_length=255, validation_alias=AliasChoices("title", "assessment_title"), description="Title of the assessment")
    description: Optional[str] = Field(None, max_length=10000, validation_alias=AliasChoices("description", "assessment_description"), description="Detailed instructions or description")
    type: AssessmentType = Field(AssessmentType.QUIZ, validation_alias=AliasChoices("type", "assessment_type"), description="Type of assessment (quiz, exam, practice)")
    status: Optional[AssessmentStatus] = Field(AssessmentStatus.DRAFT, validation_alias=AliasChoices("status", "assessment_status"), description="Initial assessment status")
    duration_minutes: Optional[int] = Field(None, gt=0, validation_alias=AliasChoices("duration_minutes", "assessment_duration_minutes"), description="Duration in minutes")
    start_at: Optional[datetime] = Field(None, validation_alias=AliasChoices("start_at", "assessment_start_at"), description="Scheduled start time (UTC)")
    end_at: Optional[datetime] = Field(None, validation_alias=AliasChoices("end_at", "assessment_end_at"), description="Scheduled end time (UTC)")
    total_marks: Optional[Decimal] = Field(None, ge=0, max_digits=7, decimal_places=2, validation_alias=AliasChoices("total_marks", "assessment_total_marks"), description="Total marks (auto-calculated if questions exist)")
    passing_marks: Optional[Decimal] = Field(None, ge=0, max_digits=7, decimal_places=2, validation_alias=AliasChoices("passing_marks", "assessment_passing_marks"), description="Passing marks threshold")
    attempt_limit: int = Field(1, ge=1, validation_alias=AliasChoices("attempt_limit", "assessment_attempt_limit"), description="Maximum attempts allowed")
    randomize_questions: bool = Field(False, validation_alias=AliasChoices("randomize_questions", "assessment_randomize_questions"), description="Whether to randomize question order for students")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValidationException("Assessment title cannot be empty or whitespace only.")
        if len(trimmed) > 255:
            raise ValidationException("Assessment title must be 255 characters or fewer.")
        return trimmed

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if len(trimmed) > 10000:
                raise ValidationException("Assessment description must be 10000 characters or fewer.")
            return trimmed if trimmed else None
        return None

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v <= 0 or v > 1440):
            raise ValidationException("Assessment duration must be between 1 and 1440 minutes (24 hours).")
        return v

    @field_validator("total_marks", "passing_marks")
    @classmethod
    def validate_marks(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            if v < 0:
                raise ValidationException("Marks cannot be negative.")
            if v > Decimal("99999.99"):
                raise ValidationException("Marks cannot exceed 99999.99.")
        return v

    @field_validator("start_at", "end_at")
    @classmethod
    def validate_datetimes(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None:
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            else:
                v = v.astimezone(timezone.utc)
        return v

    @model_validator(mode="after")
    def validate_schedule_and_passing(self) -> "AssessmentCreateRequest":
        if self.start_at is not None and self.end_at is not None:
            if self.end_at <= self.start_at:
                raise ValidationException("Assessment end time must be after the start time.")
        if self.passing_marks is not None and self.total_marks is not None:
            if self.passing_marks > self.total_marks:
                raise ValidationException("Passing marks cannot exceed total marks.")
        return self


class AssessmentUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: Optional[str] = Field(None, min_length=1, max_length=255, validation_alias=AliasChoices("title", "assessment_title"))
    description: Optional[str] = Field(None, max_length=10000, validation_alias=AliasChoices("description", "assessment_description"))
    type: Optional[AssessmentType] = Field(None, validation_alias=AliasChoices("type", "assessment_type"))
    duration_minutes: Optional[int] = Field(None, gt=0, validation_alias=AliasChoices("duration_minutes", "assessment_duration_minutes"))
    start_at: Optional[datetime] = Field(None, validation_alias=AliasChoices("start_at", "assessment_start_at"))
    end_at: Optional[datetime] = Field(None, validation_alias=AliasChoices("end_at", "assessment_end_at"))
    total_marks: Optional[Decimal] = Field(None, ge=0, max_digits=7, decimal_places=2, validation_alias=AliasChoices("total_marks", "assessment_total_marks"))
    passing_marks: Optional[Decimal] = Field(None, ge=0, max_digits=7, decimal_places=2, validation_alias=AliasChoices("passing_marks", "assessment_passing_marks"))
    attempt_limit: Optional[int] = Field(None, ge=1, validation_alias=AliasChoices("attempt_limit", "assessment_attempt_limit"))
    randomize_questions: Optional[bool] = Field(None, validation_alias=AliasChoices("randomize_questions", "assessment_randomize_questions"))

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                raise ValidationException("Assessment title cannot be empty or whitespace only.")
            if len(trimmed) > 255:
                raise ValidationException("Assessment title must be 255 characters or fewer.")
            return trimmed
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if len(trimmed) > 10000:
                raise ValidationException("Assessment description must be 10000 characters or fewer.")
            return trimmed if trimmed else None
        return None

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v <= 0 or v > 1440):
            raise ValidationException("Assessment duration must be between 1 and 1440 minutes (24 hours).")
        return v

    @field_validator("total_marks", "passing_marks")
    @classmethod
    def validate_marks(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            if v < 0:
                raise ValidationException("Marks cannot be negative.")
            if v > Decimal("99999.99"):
                raise ValidationException("Marks cannot exceed 99999.99.")
        return v

    @field_validator("start_at", "end_at")
    @classmethod
    def validate_datetimes(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None:
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            else:
                v = v.astimezone(timezone.utc)
        return v

    @model_validator(mode="after")
    def validate_schedule_and_passing(self) -> "AssessmentUpdateRequest":
        if self.start_at is not None and self.end_at is not None:
            if self.end_at <= self.start_at:
                raise ValidationException("Assessment end time must be after the start time.")
        if self.passing_marks is not None and self.total_marks is not None:
            if self.passing_marks > self.total_marks:
                raise ValidationException("Passing marks cannot exceed total marks.")
        return self


class AssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    assessment_id: uuid.UUID = Field(..., validation_alias=AliasChoices("assessment_id", "id"))
    assessment_subject_id: uuid.UUID = Field(..., validation_alias=AliasChoices("assessment_subject_id", "subject_id"))
    assessment_title: str = Field(..., validation_alias=AliasChoices("assessment_title", "title"))
    assessment_description: Optional[str] = Field(None, validation_alias=AliasChoices("assessment_description", "description"))
    assessment_type: AssessmentType = Field(..., validation_alias=AliasChoices("assessment_type", "type"))
    assessment_status: AssessmentStatus = Field(..., validation_alias=AliasChoices("assessment_status", "status"))
    assessment_duration_minutes: Optional[int] = Field(None, validation_alias=AliasChoices("assessment_duration_minutes", "duration_minutes"))
    assessment_start_at: Optional[datetime] = Field(None, validation_alias=AliasChoices("assessment_start_at", "start_at"))
    assessment_end_at: Optional[datetime] = Field(None, validation_alias=AliasChoices("assessment_end_at", "end_at"))
    assessment_total_marks: Decimal = Field(..., validation_alias=AliasChoices("assessment_total_marks", "total_marks"))
    assessment_passing_marks: Optional[Decimal] = Field(None, validation_alias=AliasChoices("assessment_passing_marks", "passing_marks"))
    assessment_attempt_limit: int = Field(1, validation_alias=AliasChoices("assessment_attempt_limit", "attempt_limit"))
    assessment_randomize_questions: bool = Field(False, validation_alias=AliasChoices("assessment_randomize_questions", "randomize_questions"))
    assessment_created_by: Optional[uuid.UUID] = Field(None, validation_alias=AliasChoices("assessment_created_by", "created_by"))
    assessment_created_at: datetime = Field(..., validation_alias=AliasChoices("assessment_created_at", "created_at"))
    assessment_updated_at: datetime = Field(..., validation_alias=AliasChoices("assessment_updated_at", "updated_at"))

    # Enriched fields
    total_questions: Optional[int] = None
    subject_name: Optional[str] = None
    workspace_id: Optional[uuid.UUID] = None
    workspace_name: Optional[str] = None


# ── Option Schemas ──────────────────────────────────────────────

class QuestionOptionCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    option_id: Optional[uuid.UUID] = Field(None, validation_alias=AliasChoices("option_id", "id"))
    option_text: str = Field(..., min_length=1, validation_alias=AliasChoices("option_text", "text"), description="Option text")
    option_order: int = Field(..., ge=1, validation_alias=AliasChoices("option_order", "order"), description="1-based display order")
    option_is_correct: bool = Field(False, validation_alias=AliasChoices("option_is_correct", "is_correct"), description="Whether this option is correct")

    @field_validator("option_text")
    @classmethod
    def validate_option_text(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValidationException("Option text cannot be empty or whitespace only.")
        return trimmed


class QuestionOptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    option_id: Optional[uuid.UUID] = Field(None, validation_alias=AliasChoices("option_id", "id"))
    option_question_id: Optional[uuid.UUID] = Field(None, validation_alias=AliasChoices("option_question_id", "question_id"))
    option_text: str = Field(..., validation_alias=AliasChoices("option_text", "text"))
    option_order: int = Field(..., validation_alias=AliasChoices("option_order", "order"))
    option_is_correct: bool = Field(..., validation_alias=AliasChoices("option_is_correct", "is_correct"))


class StudentQuestionOptionResponse(BaseModel):
    """Sanitized student view: strictly omits option_is_correct."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    option_id: Optional[uuid.UUID] = Field(None, validation_alias=AliasChoices("option_id", "id"))
    option_text: str = Field(..., validation_alias=AliasChoices("option_text", "text"))
    option_order: int = Field(..., validation_alias=AliasChoices("option_order", "order"))


# ── Question Validation Helpers ─────────────────────────────────

def validate_question_options_rules(q_type: QuestionType, options: List[QuestionOptionCreate]) -> None:
    orders = [o.option_order for o in options]
    if len(orders) != len(set(orders)):
        raise ValidationException("Option order numbers must be unique within the question.")

    if q_type == QuestionType.MCQ_SINGLE:
        if len(options) < 2:
            raise ValidationException("MCQ Single Choice questions must have at least 2 options.")
        correct_count = sum(1 for o in options if o.option_is_correct)
        if correct_count != 1:
            raise ValidationException(f"MCQ Single Choice questions must have exactly 1 correct option (found {correct_count}).")

    elif q_type == QuestionType.MCQ_MULTIPLE:
        if len(options) < 2:
            raise ValidationException("MCQ Multiple Choice questions must have at least 2 options.")
        correct_count = sum(1 for o in options if o.option_is_correct)
        if correct_count < 1:
            raise ValidationException("MCQ Multiple Choice questions must have at least 1 correct option.")

    elif q_type == QuestionType.TRUE_FALSE:
        if len(options) != 2:
            raise ValidationException("True/False questions must have exactly 2 options (True and False).")
        texts = {o.option_text.strip().lower() for o in options}
        if texts != {"true", "false"}:
            raise ValidationException("True/False question options must be 'True' and 'False'.")
        correct_count = sum(1 for o in options if o.option_is_correct)
        if correct_count != 1:
            raise ValidationException("True/False questions must have exactly 1 correct option.")

    elif q_type == QuestionType.SHORT_ANSWER:
        if len(options) > 0:
            raise ValidationException("Short Answer questions must not contain options.")


# ── Subject Question Bank Schemas ───────────────────────────────

class QuestionBankItemCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question_type: QuestionType = Field(..., validation_alias=AliasChoices("question_type", "type"), description="Question type")
    question_text: str = Field(..., min_length=1, validation_alias=AliasChoices("question_text", "text"), description="Question prompt / text")
    default_marks: Decimal = Field(Decimal("1.00"), gt=0, max_digits=7, decimal_places=2, validation_alias=AliasChoices("default_marks", "marks", "question_default_marks", "question_marks"), description="Default marks")
    question_explanation: Optional[str] = Field(None, validation_alias=AliasChoices("question_explanation", "explanation"), description="Teacher-only explanation")
    options: List[QuestionOptionCreate] = Field(default_factory=list, description="Question options")

    @field_validator("question_text")
    @classmethod
    def validate_question_text(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValidationException("Question text cannot be empty or whitespace only.")
        return trimmed

    @field_validator("default_marks")
    @classmethod
    def validate_marks(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValidationException("Question marks must be greater than 0.")
        if v > Decimal("99999.99"):
            raise ValidationException("Question marks cannot exceed 99999.99.")
        return v

    @model_validator(mode="after")
    def validate_type_and_options(self) -> "QuestionBankItemCreate":
        validate_question_options_rules(self.question_type, self.options)
        return self


class QuestionBankItemUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question_type: Optional[QuestionType] = Field(None, validation_alias=AliasChoices("question_type", "type"))
    question_text: Optional[str] = Field(None, min_length=1, validation_alias=AliasChoices("question_text", "text"))
    default_marks: Optional[Decimal] = Field(None, gt=0, max_digits=7, decimal_places=2, validation_alias=AliasChoices("default_marks", "marks", "question_default_marks", "question_marks"))
    question_explanation: Optional[str] = Field(None, validation_alias=AliasChoices("question_explanation", "explanation"))
    options: Optional[List[QuestionOptionCreate]] = Field(None, description="Updated question options")

    @field_validator("question_text")
    @classmethod
    def validate_question_text(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                raise ValidationException("Question text cannot be empty or whitespace only.")
            return trimmed
        return v

    @field_validator("default_marks")
    @classmethod
    def validate_marks(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            if v <= 0:
                raise ValidationException("Question marks must be greater than 0.")
            if v > Decimal("99999.99"):
                raise ValidationException("Question marks cannot exceed 99999.99.")
        return v


class QuestionBankItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    question_id: uuid.UUID = Field(..., validation_alias=AliasChoices("question_id", "id"))
    question_subject_id: uuid.UUID = Field(..., validation_alias=AliasChoices("question_subject_id", "subject_id"))
    question_type: QuestionType = Field(..., validation_alias=AliasChoices("question_type", "type"))
    question_text: str = Field(..., validation_alias=AliasChoices("question_text", "text"))
    question_default_marks: Decimal = Field(..., validation_alias=AliasChoices("question_default_marks", "default_marks", "marks"))
    question_explanation: Optional[str] = Field(None, validation_alias=AliasChoices("question_explanation", "explanation"))
    question_status: QuestionStatus = Field(..., validation_alias=AliasChoices("question_status", "status"))
    question_created_by: Optional[uuid.UUID] = Field(None, validation_alias=AliasChoices("question_created_by", "created_by"))
    question_created_at: datetime = Field(..., validation_alias=AliasChoices("question_created_at", "created_at"))
    question_updated_at: datetime = Field(..., validation_alias=AliasChoices("question_updated_at", "updated_at"))
    options: List[QuestionOptionResponse] = Field(default_factory=list)


# ── Assessment Question & Snapshot Schemas ──────────────────────

class AssessmentAddQuestionRequest(BaseModel):
    """Add an existing Question Bank question to an Assessment."""
    model_config = ConfigDict(populate_by_name=True)

    question_id: uuid.UUID = Field(..., description="ID of the question in Subject Question Bank")
    marks: Optional[Decimal] = Field(None, gt=0, max_digits=7, decimal_places=2, description="Custom marks for this assessment (defaults to question's default_marks)")
    order: Optional[int] = Field(None, ge=1, description="Specific display order (appends to end if omitted)")

    @field_validator("marks")
    @classmethod
    def validate_marks(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValidationException("Question marks must be greater than 0.")
        return v


class AssessmentCreateAndAddQuestionRequest(BaseModel):
    """Create a new question in the Subject Question Bank and directly attach it to the Assessment."""
    model_config = ConfigDict(populate_by_name=True)

    question_type: QuestionType = Field(..., validation_alias=AliasChoices("question_type", "type"))
    question_text: str = Field(..., min_length=1, validation_alias=AliasChoices("question_text", "text"))
    marks: Decimal = Field(Decimal("1.00"), gt=0, max_digits=7, decimal_places=2, validation_alias=AliasChoices("marks", "question_marks", "default_marks"))
    question_explanation: Optional[str] = Field(None, validation_alias=AliasChoices("question_explanation", "explanation"))
    options: List[QuestionOptionCreate] = Field(default_factory=list)
    order: Optional[int] = Field(None, ge=1)

    @field_validator("question_text")
    @classmethod
    def validate_question_text(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValidationException("Question text cannot be empty or whitespace only.")
        return trimmed

    @field_validator("marks")
    @classmethod
    def validate_marks(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValidationException("Question marks must be greater than 0.")
        return v

    @model_validator(mode="after")
    def validate_type_and_options(self) -> "AssessmentCreateAndAddQuestionRequest":
        validate_question_options_rules(self.question_type, self.options)
        return self


class AssessmentQuestionUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    marks: Optional[Decimal] = Field(None, gt=0, max_digits=7, decimal_places=2, validation_alias=AliasChoices("marks", "assessment_question_marks"))
    order: Optional[int] = Field(None, ge=1, validation_alias=AliasChoices("order", "assessment_question_order"))

    @field_validator("marks")
    @classmethod
    def validate_marks(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValidationException("Question marks must be greater than 0.")
        return v


class QuestionReorderRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question_ids: List[uuid.UUID] = Field(..., min_length=1, description="List of all assessment question UUIDs in desired order")

    @field_validator("question_ids")
    @classmethod
    def validate_unique_ids(cls, v: List[uuid.UUID]) -> List[uuid.UUID]:
        if len(v) != len(set(v)):
            raise ValidationException("Question IDs in reorder request must be unique.")
        return v


class AssessmentQuestionResponse(BaseModel):
    """Full Teacher/Admin view of an Assessment Question derived from its snapshot."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    assessment_question_id: uuid.UUID = Field(..., validation_alias=AliasChoices("assessment_question_id", "id"))
    assessment_question_assessment_id: uuid.UUID = Field(..., validation_alias=AliasChoices("assessment_question_assessment_id", "assessment_id"))
    assessment_question_question_id: Optional[uuid.UUID] = Field(None, validation_alias=AliasChoices("assessment_question_question_id", "question_id"))
    assessment_question_order: int = Field(..., validation_alias=AliasChoices("assessment_question_order", "order"))
    assessment_question_marks: Decimal = Field(..., validation_alias=AliasChoices("assessment_question_marks", "marks"))
    assessment_question_created_at: datetime = Field(..., validation_alias=AliasChoices("assessment_question_created_at", "created_at"))

    # Unpacked from snapshot
    question_type: QuestionType = Field(..., validation_alias=AliasChoices("question_type", "type"))
    question_text: str = Field(..., validation_alias=AliasChoices("question_text", "text"))
    question_explanation: Optional[str] = Field(None, validation_alias=AliasChoices("question_explanation", "explanation"))
    options: List[QuestionOptionResponse] = Field(default_factory=list)


class StudentAssessmentQuestionResponse(BaseModel):
    """Sanitized student view of an Assessment Question derived from its snapshot."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    assessment_question_id: uuid.UUID = Field(..., validation_alias=AliasChoices("assessment_question_id", "id"))
    assessment_question_order: int = Field(..., validation_alias=AliasChoices("assessment_question_order", "order"))
    assessment_question_marks: Decimal = Field(..., validation_alias=AliasChoices("assessment_question_marks", "marks"))
    question_type: QuestionType = Field(..., validation_alias=AliasChoices("question_type", "type"))
    question_text: str = Field(..., validation_alias=AliasChoices("question_text", "text"))
    options: List[StudentQuestionOptionResponse] = Field(default_factory=list)


# Aliases for backward compatibility
QuestionCreateRequest = AssessmentCreateAndAddQuestionRequest
QuestionUpdateRequest = AssessmentQuestionUpdateRequest
QuestionResponse = AssessmentQuestionResponse
StudentQuestionResponse = StudentAssessmentQuestionResponse
