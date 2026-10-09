from enum import Enum
from typing import Set

class MaterialIndexStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


# Supported MIME types for RAG extraction in V1
RAG_SUPPORTED_MIME_TYPES: Set[str] = {
    # PDF
    "application/pdf",
    # Microsoft Word
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    # Microsoft PowerPoint
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-powerpoint",
    # Plain text & CSV
    "text/plain",
    "text/csv",
    # Microsoft Excel
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
}

# Unsupported formats (videos, images, archives) that should be marked unsupported for RAG
RAG_UNSUPPORTED_MIME_TYPES: Set[str] = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "video/mp4",
    "video/webm",
    "application/zip",
    "application/x-zip-compressed",
    "application/x-zip",
}
