class AppException(Exception):
    """Base application exception for SmartClass AI."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundException(AppException):
    """Raised when a requested resource is not found."""
    def __init__(self, message: str = "Resource not found."):
        super().__init__(message=message, code="NOT_FOUND", status_code=404)


class ConflictException(AppException):
    """Raised when there is a resource conflict (e.g. unique constraint)."""
    def __init__(self, message: str = "Resource conflict occurred."):
        super().__init__(message=message, code="CONFLICT", status_code=409)


class UnauthorizedException(AppException):
    """Raised when authentication is required or failed."""
    def __init__(self, message: str = "Authentication required."):
        super().__init__(message=message, code="UNAUTHORIZED", status_code=401)


class ForbiddenException(AppException):
    """Raised when access is prohibited for the authenticated user."""
    def __init__(self, message: str = "Permission denied."):
        super().__init__(message=message, code="FORBIDDEN", status_code=403)


class ValidationException(AppException):
    """Raised when request data validation fails."""
    def __init__(self, message: str = "Validation failed."):
        super().__init__(message=message, code="VALIDATION_ERROR", status_code=422)
