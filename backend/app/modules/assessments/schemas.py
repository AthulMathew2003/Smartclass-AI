import uuid
from enum import Enum
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict, AliasChoices, field_validator, model_validator
from app.modules.assessments.models import (
    AssessmentType,
    AssessmentStatus,
    QuestionType,
    QuestionStatus,
    AttemptStatus,
    ResultStatus,
    GradingStatus,
    CorrectnessStatus
)
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
    leaderboard_enabled: bool = Field(False, validation_alias=AliasChoices("leaderboard_enabled", "assessment_leaderboard_enabled"), description="Whether leaderboard ranking is enabled")

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
    leaderboard_enabled: Optional[bool] = Field(None, validation_alias=AliasChoices("leaderboard_enabled", "assessment_leaderboard_enabled"))

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
    assessment_leaderboard_enabled: bool = Field(False, validation_alias=AliasChoices("assessment_leaderboard_enabled", "leaderboard_enabled"))
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


# ── Assessment Attempt & Taking Schemas ────────────────────────

class StudentAttemptAnswerInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    selected_option_id: Optional[uuid.UUID] = Field(None, validation_alias=AliasChoices("selected_option_id", "selectedOptionId", "option_id"))
    selected_option_ids: Optional[List[uuid.UUID]] = Field(None, validation_alias=AliasChoices("selected_option_ids", "selectedOptionIds", "option_ids"))
    text_answer: Optional[str] = Field(None, validation_alias=AliasChoices("text_answer", "textAnswer", "answer_text"))

    @field_validator("text_answer")
    @classmethod
    def sanitize_text(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            return trimmed if trimmed else None
        return None


class StudentAttemptQuestionResponse(BaseModel):
    """Sanitized question delivered to student during attempt with their current answer."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    assessment_question_id: uuid.UUID = Field(..., validation_alias=AliasChoices("assessment_question_id", "id", "question_id"))
    assessment_question_order: int = Field(..., validation_alias=AliasChoices("assessment_question_order", "order", "order_index"))
    assessment_question_marks: Decimal = Field(..., validation_alias=AliasChoices("assessment_question_marks", "marks"))
    question_type: QuestionType = Field(..., validation_alias=AliasChoices("question_type", "type"))
    question_text: str = Field(..., validation_alias=AliasChoices("question_text", "text"))
    options: List[StudentQuestionOptionResponse] = Field(default_factory=list)
    current_answer: Optional[Dict[str, Any]] = None


class AssessmentAttemptResponse(BaseModel):
    """Full attempt response for student exam taking."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    attempt_id: uuid.UUID = Field(..., validation_alias=AliasChoices("attempt_id", "id"))
    attempt_assessment_id: uuid.UUID = Field(..., validation_alias=AliasChoices("attempt_assessment_id", "assessment_id"))
    attempt_student_id: uuid.UUID = Field(..., validation_alias=AliasChoices("attempt_student_id", "student_id"))
    attempt_number: int = Field(..., validation_alias=AliasChoices("attempt_number", "number"))
    attempt_status: AttemptStatus = Field(..., validation_alias=AliasChoices("attempt_status", "status"))
    attempt_started_at: datetime = Field(..., validation_alias=AliasChoices("attempt_started_at", "started_at"))
    attempt_expires_at: Optional[datetime] = Field(None, validation_alias=AliasChoices("attempt_expires_at", "expires_at"))
    attempt_submitted_at: Optional[datetime] = Field(None, validation_alias=AliasChoices("attempt_submitted_at", "submitted_at"))
    attempt_question_order: Optional[List[str]] = Field(default_factory=list)

    # Question payload and answers map
    total_questions: int = 0
    questions: List[StudentAttemptQuestionResponse] = Field(default_factory=list)
    answers: Dict[str, Any] = Field(default_factory=dict)


class AssessmentAttemptSummaryResponse(BaseModel):
    """Summary of student's past or current attempt."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    attempt_id: uuid.UUID = Field(..., validation_alias=AliasChoices("attempt_id", "id"))
    attempt_assessment_id: uuid.UUID = Field(..., validation_alias=AliasChoices("attempt_assessment_id", "assessment_id"))
    attempt_student_id: uuid.UUID = Field(..., validation_alias=AliasChoices("attempt_student_id", "student_id"))
    attempt_number: int = Field(..., validation_alias=AliasChoices("attempt_number", "number"))
    attempt_status: AttemptStatus = Field(..., validation_alias=AliasChoices("attempt_status", "status"))
    attempt_started_at: datetime = Field(..., validation_alias=AliasChoices("attempt_started_at", "started_at"))
    attempt_expires_at: Optional[datetime] = Field(None, validation_alias=AliasChoices("attempt_expires_at", "expires_at"))
    attempt_submitted_at: Optional[datetime] = Field(None, validation_alias=AliasChoices("attempt_submitted_at", "submitted_at"))


# Aliases for backward compatibility
QuestionCreateRequest = AssessmentCreateAndAddQuestionRequest
QuestionUpdateRequest = AssessmentQuestionUpdateRequest
QuestionResponse = AssessmentQuestionResponse
StudentQuestionResponse = StudentAssessmentQuestionResponse


# ── Assessment Evaluation & Result Schemas ──────────────────────

class ManualGradeInput(BaseModel):
    """Payload submitted by a teacher to grade a short answer question."""
    model_config = ConfigDict(populate_by_name=True)

    marks_awarded: Decimal = Field(..., ge=0, max_digits=7, decimal_places=2, validation_alias=AliasChoices("marks_awarded", "marks", "score"))
    feedback: Optional[str] = Field(None, max_length=5000, validation_alias=AliasChoices("feedback", "comments", "teacher_feedback"))

    @field_validator("marks_awarded")
    @classmethod
    def validate_marks(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValidationException("Marks awarded cannot be negative.")
        return v

    @field_validator("feedback")
    @classmethod
    def sanitize_feedback(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            return trimmed if trimmed else None
        return None


class AssessmentResultQuestionResponse(BaseModel):
    """Detailed review of a single question evaluation."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    result_question_id: uuid.UUID = Field(..., validation_alias=AliasChoices("result_question_id", "id"))
    assessment_question_id: uuid.UUID = Field(..., validation_alias=AliasChoices("result_question_assessment_question_id", "assessment_question_id"))
    order: int
    question_type: QuestionType
    question_text: str
    question_explanation: Optional[str] = None
    options: List[QuestionOptionResponse] = Field(default_factory=list)
    answer_value: Optional[Dict[str, Any]] = None
    marks_available: Decimal = Field(..., validation_alias=AliasChoices("result_question_marks_available", "marks_available"))
    marks_awarded: Decimal = Field(..., validation_alias=AliasChoices("result_question_marks_awarded", "marks_awarded"))
    correctness: CorrectnessStatus = Field(..., validation_alias=AliasChoices("result_question_correctness", "correctness"))
    grading_status: GradingStatus = Field(..., validation_alias=AliasChoices("result_question_grading_status", "grading_status"))
    feedback: Optional[str] = Field(None, validation_alias=AliasChoices("result_question_feedback", "feedback"))
    graded_by: Optional[uuid.UUID] = Field(None, validation_alias=AliasChoices("result_question_graded_by", "graded_by"))
    graded_at: Optional[datetime] = Field(None, validation_alias=AliasChoices("result_question_graded_at", "graded_at"))


class AssessmentResultResponse(BaseModel):
    """Complete assessment attempt evaluation result."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    result_id: uuid.UUID = Field(..., validation_alias=AliasChoices("result_id", "id"))
    attempt_id: uuid.UUID = Field(..., validation_alias=AliasChoices("result_attempt_id", "attempt_id"))
    assessment_id: uuid.UUID = Field(..., validation_alias=AliasChoices("result_assessment_id", "assessment_id"))
    student_id: uuid.UUID = Field(..., validation_alias=AliasChoices("result_student_id", "student_id"))
    assessment_title: Optional[str] = None
    attempt_number: int = 1
    attempt_status: AttemptStatus = AttemptStatus.SUBMITTED
    attempt_started_at: datetime
    attempt_submitted_at: Optional[datetime] = None
    total_marks: Decimal = Field(..., validation_alias=AliasChoices("result_total_marks", "total_marks"))
    obtained_marks: Decimal = Field(..., validation_alias=AliasChoices("result_obtained_marks", "obtained_marks"))
    percentage: Decimal = Field(..., validation_alias=AliasChoices("result_percentage", "percentage"))
    passed: Optional[bool] = Field(None, validation_alias=AliasChoices("result_passed", "passed"))
    status: ResultStatus = Field(..., validation_alias=AliasChoices("result_status", "status"))
    correct_count: int = Field(0, validation_alias=AliasChoices("result_correct_count", "correct_count"))
    incorrect_count: int = Field(0, validation_alias=AliasChoices("result_incorrect_count", "incorrect_count"))
    unanswered_count: int = Field(0, validation_alias=AliasChoices("result_unanswered_count", "unanswered_count"))
    pending_count: int = Field(0, validation_alias=AliasChoices("result_pending_count", "pending_count"))
    graded_at: Optional[datetime] = Field(None, validation_alias=AliasChoices("result_graded_at", "graded_at"))
    questions: List[AssessmentResultQuestionResponse] = Field(default_factory=list)


class TeacherAssessmentResultSummaryResponse(BaseModel):
    """Summary of a student's attempt result for teacher tables."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    result_id: Optional[uuid.UUID] = None
    attempt_id: uuid.UUID
    student_id: uuid.UUID
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    attempt_number: int
    attempt_status: AttemptStatus
    total_marks: Decimal
    obtained_marks: Decimal
    percentage: Decimal
    passed: Optional[bool] = None
    status: ResultStatus
    pending_count: int = 0
    started_at: datetime
    submitted_at: Optional[datetime] = None


# ── Assessment Analytics Schemas (Step 10.11) ─────────────────

class AssessmentAnalyticsOverview(BaseModel):
    """High-level assessment metrics and rates."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    total_enrolled_students: int = 0
    total_students_attempted: int = 0
    total_attempts: int = 0
    total_submitted_attempts: int = 0
    total_expired_attempts: int = 0
    total_in_progress_attempts: int = 0
    total_completed_evaluations: int = 0
    total_pending_manual_grading: int = 0
    total_passed: int = 0
    total_failed: int = 0
    pass_percentage: Optional[float] = None
    participation_rate: Optional[float] = None


class AssessmentScoreStatistics(BaseModel):
    """Score distributions and extremes across completed evaluations."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    average_percentage: Optional[float] = None
    median_percentage: Optional[float] = None
    highest_percentage: Optional[float] = None
    lowest_percentage: Optional[float] = None
    average_obtained_marks: Optional[float] = None
    total_marks: float = 0.0
    passing_marks: Optional[float] = None


class AssessmentAttemptStatistics(BaseModel):
    """Attempt counts and distribution metrics."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    total_attempts: int = 0
    average_attempts_per_student: Optional[float] = None
    single_attempt_student_count: int = 0
    multiple_attempts_student_count: int = 0


class AssessmentQuestionAnalyticsItem(BaseModel):
    """Statistical performance metrics for an individual assessment question."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    assessment_question_id: uuid.UUID
    question_order: int
    question_type: QuestionType
    question_text: str
    marks_available: float
    evaluated_count: int = 0
    correct_count: int = 0
    incorrect_count: int = 0
    unanswered_count: int = 0
    pending_count: int = 0
    average_marks_awarded: Optional[float] = None
    accuracy_percentage: Optional[float] = None


class AssessmentStudentAttemptItem(BaseModel):
    """Summary of a specific attempt by a student."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    attempt_id: uuid.UUID
    attempt_number: int
    attempt_status: AttemptStatus
    started_at: datetime
    submitted_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    obtained_marks: Optional[float] = None
    percentage: Optional[float] = None
    passed: Optional[bool] = None
    status: Optional[ResultStatus] = None
    pending_count: int = 0


class AssessmentStudentPerformanceItem(BaseModel):
    """Aggregated assessment performance for an individual student."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    student_id: uuid.UUID
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    total_attempts: int = 0
    latest_attempt_number: int = 1
    latest_attempt_status: AttemptStatus
    latest_percentage: Optional[float] = None
    latest_obtained_marks: Optional[float] = None
    latest_passed: Optional[bool] = None
    latest_result_status: Optional[ResultStatus] = None
    best_percentage: Optional[float] = None
    best_obtained_marks: Optional[float] = None
    has_pending_grading: bool = False
    attempts: List[AssessmentStudentAttemptItem] = Field(default_factory=list)


class AssessmentAnalyticsResponse(BaseModel):
    """Complete class-wide assessment analytics payload for Teachers and Admins."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    assessment_id: uuid.UUID
    assessment_title: str
    assessment_type: AssessmentType
    assessment_status: AssessmentStatus
    overview: AssessmentAnalyticsOverview
    score_statistics: AssessmentScoreStatistics
    attempt_statistics: AssessmentAttemptStatistics
    question_statistics: List[AssessmentQuestionAnalyticsItem] = Field(default_factory=list)
    student_statistics: List[AssessmentStudentPerformanceItem] = Field(default_factory=list)


class StudentSelfAnalyticsResponse(BaseModel):
    """Student self-performance and attempt progression analytics."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    assessment_id: uuid.UUID
    assessment_title: str
    assessment_total_marks: float
    attempt_limit: int
    total_attempts_used: int
    attempts_remaining: int
    latest_percentage: Optional[float] = None
    latest_obtained_marks: Optional[float] = None
    best_percentage: Optional[float] = None
    best_obtained_marks: Optional[float] = None
    passed: Optional[bool] = None
    has_pending_grading: bool = False
    attempts: List[AssessmentStudentAttemptItem] = Field(default_factory=list)


# ── Learning Analytics & Question Difficulty Schemas (Step 10.12) ───

class ObservedDifficultyBand(str, Enum):
    EASIER_OBSERVED = "easier_observed"
    MODERATE_OBSERVED = "moderate_observed"
    HARDER_OBSERVED = "harder_observed"
    INSUFFICIENT_SAMPLE = "insufficient_sample"


class StudentLearningOverview(BaseModel):
    """High-level longitudinal learning overview for a student."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    total_assessments_attempted: int = 0
    total_assessments_completed: int = 0
    total_assessments_pending_grading: int = 0
    total_attempts_count: int = 0
    average_percentage: Optional[float] = None
    best_percentage: Optional[float] = None
    latest_percentage: Optional[float] = None
    total_passed_count: int = 0
    total_failed_count: int = 0


class StudentPerformanceTrendPoint(BaseModel):
    """A chronological assessment result data point."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    assessment_id: uuid.UUID
    assessment_title: str
    subject_id: uuid.UUID
    subject_name: str
    attempt_id: uuid.UUID
    attempt_number: int
    date: datetime
    percentage: Optional[float] = None
    obtained_marks: Optional[float] = None
    total_marks: float = 0.0
    passed: Optional[bool] = None
    status: ResultStatus


class StudentLearningTrend(BaseModel):
    """Longitudinal trend metrics comparing recent performance to history."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    recent_average_percentage: Optional[float] = None
    historical_average_percentage: Optional[float] = None
    improvement_from_previous: Optional[float] = None
    recent_window_size: int = 5


class StudentSubjectPerformanceItem(BaseModel):
    """Student performance aggregated by Subject."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    subject_id: uuid.UUID
    subject_name: str
    assessments_attempted: int = 0
    assessments_completed: int = 0
    average_percentage: Optional[float] = None
    best_percentage: Optional[float] = None
    latest_percentage: Optional[float] = None
    objective_accuracy_percentage: Optional[float] = None
    passed_count: int = 0
    failed_count: int = 0


class StudentQuestionTypePerformanceItem(BaseModel):
    """Performance breakdown by Question Type."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    question_type: QuestionType
    evaluated_count: int = 0
    correct_count: int = 0
    incorrect_count: int = 0
    unanswered_count: int = 0
    pending_count: int = 0
    accuracy_percentage: Optional[float] = None


class StudentLearningAnalyticsResponse(BaseModel):
    """Complete longitudinal learning analytics payload for a student."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    student_id: uuid.UUID
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    overview: StudentLearningOverview
    trend: StudentLearningTrend
    performance_progression: List[StudentPerformanceTrendPoint] = Field(default_factory=list)
    subject_performance: List[StudentSubjectPerformanceItem] = Field(default_factory=list)
    question_type_performance: List[StudentQuestionTypePerformanceItem] = Field(default_factory=list)
    recent_assessments: List[StudentPerformanceTrendPoint] = Field(default_factory=list)


class QuestionDifficultyAnalyticsItem(BaseModel):
    """Observed descriptive difficulty metrics for an individual question."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    question_id: uuid.UUID
    source_question_id: Optional[uuid.UUID] = None
    question_text: str
    question_type: QuestionType
    marks_available: float
    evaluated_count: int = 0
    correct_count: int = 0
    incorrect_count: int = 0
    unanswered_count: int = 0
    pending_count: int = 0
    average_marks_awarded: Optional[float] = None
    accuracy_percentage: Optional[float] = None
    difficulty_band: ObservedDifficultyBand
    difficulty_label: str
    is_insufficient_sample: bool = False
    assessment_count: int = 1


class SubjectQuestionDifficultyResponse(BaseModel):
    """Descriptive question difficulty analysis for a subject."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    subject_id: uuid.UUID
    subject_name: str
    total_questions_analyzed: int = 0
    easier_count: int = 0
    moderate_count: int = 0
    harder_count: int = 0
    insufficient_sample_count: int = 0
    questions: List[QuestionDifficultyAnalyticsItem] = Field(default_factory=list)


class SubjectLearningAnalyticsResponse(BaseModel):
    """Subject-level learning progression and assessment performance."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    subject_id: uuid.UUID
    subject_name: str
    total_assessments: int = 0
    total_students_enrolled: int = 0
    total_students_attempted: int = 0
    average_subject_percentage: Optional[float] = None
    pass_rate_percentage: Optional[float] = None
    total_evaluations_completed: int = 0
    total_pending_manual_grading: int = 0
    assessment_trends: List[Dict[str, Any]] = Field(default_factory=list)
    question_difficulty_summary: Dict[str, int] = Field(default_factory=dict)


# ── Step 10.13: Leaderboard & Class Performance Dashboard ────────────

class AssessmentLeaderboardSettingsUpdateRequest(BaseModel):
    """Payload to enable or disable leaderboard ranking for an assessment."""
    enabled: bool = Field(..., description="Whether leaderboard ranking is enabled")


class LeaderboardStudentBrief(BaseModel):
    """Sanitized student profile information for leaderboard display."""
    id: uuid.UUID
    display_name: str
    profile_image_url: Optional[str] = None


class AssessmentLeaderboardEntryResponse(BaseModel):
    """Individual ranked student entry on the leaderboard."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    rank: int
    student: LeaderboardStudentBrief
    percentage: float
    obtained_marks: float
    total_marks: float
    attempts_used: int
    completed_at: datetime
    is_current_user: bool = False


class AssessmentLeaderboardResponse(BaseModel):
    """Authoritative leaderboard response for an assessment."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    assessment_id: uuid.UUID
    assessment_title: str
    leaderboard_enabled: bool
    total_ranked_students: int
    my_rank: Optional[int] = None
    my_entry: Optional[AssessmentLeaderboardEntryResponse] = None
    entries: List[AssessmentLeaderboardEntryResponse] = Field(default_factory=list)
    page: int = 1
    page_size: int = 20
    total_pages: int = 1


class ClassStudentPerformanceItem(BaseModel):
    """Aggregated per-student performance row on the class dashboard."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    student_id: uuid.UUID
    student_name: str
    student_email: Optional[str] = None
    assessments_completed: int = 0
    average_percentage: Optional[float] = None
    latest_percentage: Optional[float] = None
    best_percentage: Optional[float] = None
    passed_count: int = 0
    pending_grading_count: int = 0
    status_label: str = "Completed"


class ClassPerformanceDashboardResponse(BaseModel):
    """Consolidated class performance dashboard response for teachers and admins."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    subject_id: uuid.UUID
    subject_name: str
    workspace_id: uuid.UUID
    workspace_name: str
    total_students: int = 0
    participating_students: int = 0
    participation_rate_percentage: float = 0.0
    total_assessments: int = 0
    completed_evaluations: int = 0
    class_average_percentage: Optional[float] = None
    class_median_percentage: Optional[float] = None
    class_pass_rate_percentage: Optional[float] = None
    total_pending_manual_grading: int = 0
    performance_trend: List[Dict[str, Any]] = Field(default_factory=list)
    assessment_summaries: List[Dict[str, Any]] = Field(default_factory=list)
    student_roster: List[ClassStudentPerformanceItem] = Field(default_factory=list)
    question_difficulty_summary: Dict[str, int] = Field(default_factory=dict)





