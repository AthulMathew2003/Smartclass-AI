import os
import re
import uuid
from typing import Dict, Set

from app.core.config import settings
from app.core.exceptions import ValidationException


# ── Allowed MIME Types & Default Extensions ─────────────────────────────
# Maps allowed MIME types to standard file extensions
ALLOWED_MATERIAL_MIME_TYPES: Dict[str, str] = {
    # Documents (max 50 MB)
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.ms-powerpoint": "ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "text/csv": "csv",
    "text/plain": "txt",
    # Images (max 10 MB)
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    # Video (max 500 MB)
    "video/mp4": "mp4",
    "video/webm": "webm",
    # Archives (max 100 MB)
    "application/zip": "zip",
    "application/x-zip-compressed": "zip",
    "application/x-zip": "zip",
}

# Mapping of file extensions to their allowed MIME types (for dual verification)
EXTENSION_TO_MIME_MAP: Dict[str, Set[str]] = {
    "pdf": {"application/pdf"},
    "doc": {"application/msword"},
    "docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    "ppt": {"application/vnd.ms-powerpoint"},
    "pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
    "xls": {"application/vnd.ms-excel"},
    "xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    "csv": {"text/csv", "text/plain", "application/vnd.ms-excel"},
    "txt": {"text/plain"},
    "jpg": {"image/jpeg"},
    "jpeg": {"image/jpeg"},
    "png": {"image/png"},
    "webp": {"image/webp"},
    "mp4": {"video/mp4"},
    "webm": {"video/webm"},
    "zip": {"application/zip", "application/x-zip-compressed", "application/x-zip"},
}

# Explicitly Disallowed / Dangerous MIME & Extension Patterns
DISALLOWED_PATTERNS = [
    r"^image/svg.*",
    r"^text/html.*",
    r"^text/javascript.*",
    r"^application/javascript.*",
    r"^application/x-javascript.*",
    r"^application/x-executable.*",
    r"^application/x-msdownload.*",
    r"^application/x-sh.*",
    r"^application/x-bat.*",
]

DISALLOWED_EXTENSIONS = {
    "svg", "html", "htm", "js", "mjs", "jsx", "ts", "tsx", "exe", "dll", "bat", "cmd",
    "sh", "bash", "vbs", "ps1", "jar", "apk", "scr", "pif"
}


def sanitize_filename(filename: str) -> str:
    """
    Sanitize the client-provided filename:
    - Strip directory traversal and path separators
    - Strip control characters and non-printable chars
    - Enforce length limits (max 255 chars)
    - Fallback to 'material_file' if sanitized name is empty
    """
    if not filename or not isinstance(filename, str):
        return "material_file"

    clean = os.path.basename(filename.strip().replace("\\", "/"))
    # Remove control characters and non-printable chars
    clean = re.sub(r"[\x00-\x1f\x7f]", "", clean)
    if not clean or clean in (".", ".."):
        clean = "material_file"
    return clean[:255]


def get_material_max_size_bytes(ext: str) -> int:
    """Return max allowed size in bytes based on file category limit in settings."""
    ext_lower = ext.lower()
    if ext_lower in ("jpg", "jpeg", "png", "webp"):
        return settings.MATERIAL_MAX_IMAGE_SIZE_MB * 1024 * 1024
    if ext_lower in ("mp4", "webm"):
        return settings.MATERIAL_MAX_VIDEO_SIZE_MB * 1024 * 1024
    if ext_lower == "zip":
        return settings.MATERIAL_MAX_ZIP_SIZE_MB * 1024 * 1024
    # Default document types
    return settings.MATERIAL_MAX_DOC_SIZE_MB * 1024 * 1024


def get_material_max_size_mb(ext: str) -> int:
    """Return max allowed size in MB for friendly error messaging."""
    ext_lower = ext.lower()
    if ext_lower in ("jpg", "jpeg", "png", "webp"):
        return settings.MATERIAL_MAX_IMAGE_SIZE_MB
    if ext_lower in ("mp4", "webm"):
        return settings.MATERIAL_MAX_VIDEO_SIZE_MB
    if ext_lower == "zip":
        return settings.MATERIAL_MAX_ZIP_SIZE_MB
    return settings.MATERIAL_MAX_DOC_SIZE_MB


def validate_material_upload_request(content_type: str, file_size: int, filename: str) -> str:
    """
    Perform rigorous server-side dual validation using both MIME/content type and file extension.
    Rejects unsupported formats, SVGs, scripts, and oversized files.
    
    Returns the resolved clean file extension.
    """
    if not filename or not isinstance(filename, str) or not filename.strip():
        raise ValidationException("Filename is required.")

    if not content_type or not isinstance(content_type, str) or not content_type.strip():
        raise ValidationException("Content type is required.")

    clean_content_type = content_type.strip().lower()
    clean_filename = sanitize_filename(filename)

    # 1. Check disallowed MIME patterns (e.g. svg, html, script, executable)
    for pattern in DISALLOWED_PATTERNS:
        if re.match(pattern, clean_content_type):
            raise ValidationException(f"File type '{content_type}' is not allowed for course materials.")

    # 2. Extract and check extension
    parts = clean_filename.rsplit(".", 1)
    if len(parts) < 2 or not parts[1].strip():
        raise ValidationException("Filename must include a valid file extension.")
    
    ext = parts[1].strip().lower()

    if ext in DISALLOWED_EXTENSIONS:
        raise ValidationException(f"Files with extension '.{ext}' are not permitted.")

    if ext not in EXTENSION_TO_MIME_MAP:
        allowed_exts = ", ".join(sorted(EXTENSION_TO_MIME_MAP.keys()))
        raise ValidationException(
            f"Unsupported file extension '.{ext}'. Supported extensions: {allowed_exts}."
        )

    # 3. Check allowed MIME types list
    if clean_content_type not in ALLOWED_MATERIAL_MIME_TYPES:
        allowed_mimes = ", ".join(sorted(ALLOWED_MATERIAL_MIME_TYPES.keys()))
        raise ValidationException(
            f"Unsupported content type '{content_type}'. Allowed types: {allowed_mimes}."
        )

    # 4. Cross-validate MIME type and extension compatibility
    valid_mimes_for_ext = EXTENSION_TO_MIME_MAP.get(ext, set())
    if clean_content_type not in valid_mimes_for_ext:
        raise ValidationException(
            f"Content type '{clean_content_type}' does not match file extension '.{ext}'."
        )

    # 5. Check file size
    if file_size <= 0:
        raise ValidationException("File size must be greater than zero bytes.")

    max_bytes = get_material_max_size_bytes(ext)
    max_mb = get_material_max_size_mb(ext)
    if file_size > max_bytes:
        raise ValidationException(
            f"File size ({file_size} bytes) exceeds maximum allowed limit of {max_mb} MB for .{ext} files."
        )

    return ext


def generate_material_s3_key(
    subject_id: uuid.UUID,
    material_id: uuid.UUID,
    extension: str
) -> str:
    """
    Generate a deterministic, server-controlled S3 object key for a course material.

    Format: subjects/{subject_id}/materials/{material_id}/file.{extension}
    """
    clean_ext = extension.strip().lower().lstrip(".")
    if not clean_ext:
        clean_ext = "bin"
    return f"subjects/{subject_id}/materials/{material_id}/file.{clean_ext}"
