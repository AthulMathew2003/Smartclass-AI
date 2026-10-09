from app.core.exceptions import AppException


class AiTutorException(AppException):
    """Base exception for AI Tutor module."""
    def __init__(self, message: str = "AI Tutor encountered an error.", code: str = "AI_TUTOR_ERROR", status_code: int = 500):
        super().__init__(message=message, code=code, status_code=status_code)


class AiTutorGenerationException(AiTutorException):
    """Raised when LLM text generation fails."""
    def __init__(self, message: str = "Failed to generate tutor response from AI service."):
        super().__init__(message=message, code="AI_TUTOR_GENERATION_FAILED", status_code=500)


class ConversationNotFoundException(AppException):
    """Raised when an AI Tutor conversation is not found or not owned."""
    def __init__(self, message: str = "Conversation not found or access denied."):
        super().__init__(message=message, code="CONVERSATION_NOT_FOUND", status_code=404)
