import os
import re
import uuid
from typing import Dict

from app.core.config import settings
from app.core.exceptions import ValidationException


# ── Allowed MIME Types & Extensions ─────────────────────────────
ALLOWED_ATTACHMENT_MIME_TYPES: Dict[str, str] = {
    # PDF & Text
    "application/pdf": "pdf",
    "text/plain": "txt",
    # Images
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    # Documents
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    # Spreadsheets
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    # Presentations
    "application/vnd.ms-powerpoint": "ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
}

# Explicitly Disallowed / Dangerous MIME Types
DISALLOWED_MIME_PATTERNS = [
    r"image/svg.*",
    r"text/html.*",
    r"text/javascript.*",
    r"application/javascript.*",
    r"application/x-javascript.*",
    r"application/x-executable.*",
    r"application/x-msdownload.*",
    r"application/x-sh.*",
]


def sanitize_filename(filename: str) -> str:
    """
    Sanitize the client-provided filename:
    - Strip directory paths and dangerous characters
    - Fallback to 'attachment' if empty
    - Limit length to 255 characters
    """
    if not filename or not isinstance(filename, str):
        return "attachment"

    # Strip paths
    clean = os.path.basename(filename.strip().replace("\\", "/"))
    # Remove control characters and non-printable chars
    clean = re.sub(r"[\x00-\x1f\x7f]", "", clean)
    if not clean:
        clean = "attachment"
    return clean[:255]


def validate_attachment_request(content_type: str, file_size: int, filename: str) -> str:
    """
    Validate declared content type, file size, and filename.
    Returns the file extension.
    """
    if not content_type or not isinstance(content_type, str):
        raise ValidationException("Content type is required.")

    clean_content_type = content_type.strip().lower()

    # Check against disallowed patterns
    for pattern in DISALLOWED_MIME_PATTERNS:
        if re.match(pattern, clean_content_type):
            raise ValidationException(f"File type '{content_type}' is not allowed for attachments.")

    if clean_content_type not in ALLOWED_ATTACHMENT_MIME_TYPES:
        allowed_list = ", ".join(sorted(ALLOWED_ATTACHMENT_MIME_TYPES.keys()))
        raise ValidationException(
            f"Unsupported file type '{content_type}'. Allowed types: {allowed_list}."
        )

    if file_size <= 0:
        raise ValidationException("File size must be greater than zero.")

    max_size_bytes = settings.ASSIGNMENT_ATTACHMENT_MAX_SIZE_MB * 1024 * 1024
    if file_size > max_size_bytes:
        raise ValidationException(
            f"File size ({file_size} bytes) exceeds maximum limit of "
            f"{settings.ASSIGNMENT_ATTACHMENT_MAX_SIZE_MB} MB."
        )

    if not filename or not filename.strip():
        raise ValidationException("Filename is required.")

    return ALLOWED_ATTACHMENT_MIME_TYPES[clean_content_type]


def generate_attachment_s3_key(
    assignment_id: uuid.UUID,
    attachment_id: uuid.UUID,
    content_type: str
) -> str:
    """
    Generate a server-controlled S3 object key for an assignment attachment.

    Format: assignments/{assignment_id}/attachments/{attachment_id}.{extension}
    """
    clean_content_type = content_type.strip().lower()
    ext = ALLOWED_ATTACHMENT_MIME_TYPES.get(clean_content_type, "bin")
    return f"assignments/{assignment_id}/attachments/{attachment_id}.{ext}"


def generate_submission_attachment_s3_key(
    assignment_id: uuid.UUID,
    student_id: uuid.UUID,
    attachment_id: uuid.UUID,
    content_type: str
) -> str:
    """
    Generate a server-controlled S3 object key for a student submission attachment.

    Format: submissions/{assignment_id}/{student_id}/{attachment_id}.{extension}
    """
    clean_content_type = content_type.strip().lower()
    ext = ALLOWED_ATTACHMENT_MIME_TYPES.get(clean_content_type, "bin")
    return f"submissions/{assignment_id}/{student_id}/{attachment_id}.{ext}"
