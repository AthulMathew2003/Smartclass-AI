import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import StorageException, ValidationException
from app.core.storage import S3StorageService
from app.modules.users.models import User


# ── Constants ──────────────────────────────────────────────────
ALLOWED_CONTENT_TYPES: set[str] = {"image/jpeg", "image/png", "image/webp"}

CONTENT_TYPE_EXTENSIONS: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5 MB


class ProfilePhotoService:
    """
    Domain-specific service for managing user profile photos on S3.

    Wraps the generic S3StorageService with profile-photo validation,
    key generation, and photo lifecycle management.

    This service does NOT perform authorization checks — the caller
    (router / service layer) must verify permissions before invoking.
    """

    def __init__(self, storage: S3StorageService | None = None) -> None:
        self.storage = storage or S3StorageService()

    # ── Validation ─────────────────────────────────────────────

    @staticmethod
    def validate_photo_request(content_type: str, file_size: int) -> None:
        """
        Validate the declared content type and file size for a profile photo.

        :param content_type: MIME type declared by the client.
        :param file_size: File size in bytes declared by the client.
        :raises ValidationException: If content type or size is invalid.
        """
        if not content_type or content_type.strip() not in ALLOWED_CONTENT_TYPES:
            raise ValidationException(
                f"Invalid image type '{content_type}'. "
                f"Allowed types: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}."
            )
        if file_size <= 0:
            raise ValidationException("File size must be greater than zero.")
        if file_size > MAX_FILE_SIZE:
            raise ValidationException(
                f"File size ({file_size} bytes) exceeds the maximum "
                f"allowed size of {MAX_FILE_SIZE // (1024 * 1024)} MB."
            )

    # ── Key Generation ─────────────────────────────────────────

    @staticmethod
    def generate_photo_key(user_id: uuid.UUID, content_type: str) -> str:
        """
        Generate a unique, server-controlled S3 object key for a profile photo.

        Format: users/{user_id}/profile/{unique_file_id}.{extension}

        :param user_id: Target user's UUID.
        :param content_type: Validated MIME type.
        :return: S3 object key string.
        """
        ext = CONTENT_TYPE_EXTENSIONS.get(content_type.strip(), "jpg")
        file_id = uuid.uuid4().hex[:12]
        return f"users/{user_id}/profile/{file_id}.{ext}"

    # ── Upload URL Generation ──────────────────────────────────

    def request_upload(
        self,
        user_id: uuid.UUID,
        content_type: str,
        file_size: int,
        expires_in: int = 900,
    ) -> dict[str, Any]:
        """
        Validate photo parameters, generate an S3 key, and return a presigned
        PUT URL for the client to upload the photo directly to S3.

        :param user_id: Target user's UUID.
        :param content_type: MIME type of the file.
        :param file_size: Size of the file in bytes.
        :param expires_in: Presigned URL expiration in seconds.
        :return: Dict with key, upload_url, and expires_in.
        """
        self.validate_photo_request(content_type, file_size)
        key = self.generate_photo_key(user_id, content_type)
        upload_url = self.storage.generate_upload_url(
            key=key,
            content_type=content_type.strip(),
            expires_in=expires_in,
        )
        return {
            "key": key,
            "upload_url": upload_url,
            "expires_in": expires_in,
        }

    # ── URL Resolution ─────────────────────────────────────────

    def resolve_photo_url(
        self,
        profile_image_value: Optional[str],
        expires_in: int = 900,
    ) -> Optional[str]:
        """
        Resolve a stored profile_image value to a usable URL.

        - None → None (no photo set)
        - Starts with http:// or https:// → None (legacy OAuth URL, force re-upload)
        - Otherwise → presigned GET URL from S3

        :param profile_image_value: Raw value from user_profile_image column.
        :param expires_in: Presigned URL expiration in seconds.
        :return: Presigned download URL or None.
        """
        if not profile_image_value:
            return None
        # Legacy OAuth URLs should not be served — return None to force re-upload
        if profile_image_value.startswith(("http://", "https://")):
            return None
        try:
            return self.storage.generate_download_url(
                key=profile_image_value,
                expires_in=expires_in,
            )
        except Exception:
            return None

    # ── Confirm Upload ─────────────────────────────────────────

    async def confirm_upload(
        self,
        db: AsyncSession,
        user: User,
        key: str,
    ) -> User:
        """
        Verify an uploaded photo exists in S3, save the key to the user record,
        and delete the old photo if one exists.

        :param db: Async database session.
        :param user: User ORM instance to update.
        :param key: S3 object key to confirm.
        :return: Updated User instance.
        :raises StorageException: If the object does not exist in S3.
        :raises ValidationException: If the key does not belong to the target user.
        """
        # Verify the key belongs to this user
        expected_prefix = f"users/{user.user_id}/profile/"
        if not key.startswith(expected_prefix):
            raise ValidationException(
                "Profile photo key does not belong to the target user."
            )

        # Verify the object exists in S3
        if not self.storage.object_exists(key):
            raise StorageException(
                "Profile photo was not found in storage. "
                "The upload may have failed or the URL expired."
            )

        old_key = user.user_profile_image

        # Save the new key
        user.user_profile_image = key
        db.add(user)
        await db.flush()

        # Delete the old S3 object only after DB update succeeds
        if old_key and old_key != key and not old_key.startswith(("http://", "https://")):
            try:
                self.storage.delete_object(old_key)
            except Exception:
                # Non-critical: old object cleanup failed but new photo is saved
                pass

        return user

    # ── Delete Photo ───────────────────────────────────────────

    async def delete_photo(
        self,
        db: AsyncSession,
        user: User,
    ) -> User:
        """
        Remove the profile photo from the user record and delete the S3 object.

        :param db: Async database session.
        :param user: User ORM instance.
        :return: Updated User instance.
        """
        old_key = user.user_profile_image

        user.user_profile_image = None
        db.add(user)
        await db.flush()

        if old_key and not old_key.startswith(("http://", "https://")):
            try:
                self.storage.delete_object(old_key)
            except Exception:
                # Non-critical: old object cleanup failed but DB is updated
                pass

        return user
