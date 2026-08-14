import uuid
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
from botocore.exceptions import ClientError

from app.core.exceptions import StorageException, ValidationException
from app.modules.users.profile_photo import (
    ProfilePhotoService,
    ALLOWED_CONTENT_TYPES,
    MAX_FILE_SIZE,
    CONTENT_TYPE_EXTENSIONS,
)


# ── Fixtures ───────────────────────────────────────────────────

@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.generate_upload_url.return_value = "https://s3.amazonaws.com/presigned-put-url"
    storage.generate_download_url.return_value = "https://s3.amazonaws.com/presigned-get-url"
    storage.object_exists.return_value = True
    storage.delete_object.return_value = None
    return storage


@pytest.fixture
def photo_service(mock_storage):
    return ProfilePhotoService(storage=mock_storage)


# ── Validation Tests ───────────────────────────────────────────

class TestPhotoValidation:
    """Tests for content type and file size validation."""

    def test_valid_content_types_accepted(self, photo_service):
        for ct in ALLOWED_CONTENT_TYPES:
            ProfilePhotoService.validate_photo_request(ct, 1024)

    def test_svg_rejected(self, photo_service):
        with pytest.raises(ValidationException, match="Invalid image type"):
            ProfilePhotoService.validate_photo_request("image/svg+xml", 1024)

    def test_invalid_mime_rejected(self, photo_service):
        invalid_types = ["text/plain", "application/pdf", "image/gif", "video/mp4", ""]
        for ct in invalid_types:
            with pytest.raises(ValidationException):
                ProfilePhotoService.validate_photo_request(ct, 1024)

    def test_oversized_file_rejected(self, photo_service):
        with pytest.raises(ValidationException, match="exceeds the maximum"):
            ProfilePhotoService.validate_photo_request("image/jpeg", MAX_FILE_SIZE + 1)

    def test_zero_size_rejected(self, photo_service):
        with pytest.raises(ValidationException, match="greater than zero"):
            ProfilePhotoService.validate_photo_request("image/jpeg", 0)

    def test_negative_size_rejected(self, photo_service):
        with pytest.raises(ValidationException, match="greater than zero"):
            ProfilePhotoService.validate_photo_request("image/jpeg", -1)

    def test_max_size_accepted(self, photo_service):
        ProfilePhotoService.validate_photo_request("image/jpeg", MAX_FILE_SIZE)

    def test_none_content_type_rejected(self, photo_service):
        with pytest.raises(ValidationException):
            ProfilePhotoService.validate_photo_request(None, 1024)


# ── Key Generation Tests ───────────────────────────────────────

class TestPhotoKeyGeneration:
    """Tests for S3 key format generation."""

    def test_generate_photo_key_format(self):
        user_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        key = ProfilePhotoService.generate_photo_key(user_id, "image/jpeg")
        assert key.startswith(f"users/{user_id}/profile/")
        assert key.endswith(".jpg")

    def test_generate_photo_key_png(self):
        user_id = uuid.uuid4()
        key = ProfilePhotoService.generate_photo_key(user_id, "image/png")
        assert key.endswith(".png")

    def test_generate_photo_key_webp(self):
        user_id = uuid.uuid4()
        key = ProfilePhotoService.generate_photo_key(user_id, "image/webp")
        assert key.endswith(".webp")

    def test_generate_photo_key_unique(self):
        user_id = uuid.uuid4()
        key1 = ProfilePhotoService.generate_photo_key(user_id, "image/jpeg")
        key2 = ProfilePhotoService.generate_photo_key(user_id, "image/jpeg")
        assert key1 != key2


# ── Upload URL Generation Tests ────────────────────────────────

class TestRequestUpload:
    """Tests for presigned upload URL generation."""

    def test_request_upload_returns_presigned_url(self, photo_service, mock_storage):
        user_id = uuid.uuid4()
        result = photo_service.request_upload(user_id, "image/jpeg", 1024)

        assert "key" in result
        assert result["key"].startswith(f"users/{user_id}/profile/")
        assert result["upload_url"] == "https://s3.amazonaws.com/presigned-put-url"
        assert result["expires_in"] == 900
        mock_storage.generate_upload_url.assert_called_once()

    def test_request_upload_validates_content_type(self, photo_service):
        with pytest.raises(ValidationException, match="Invalid image type"):
            photo_service.request_upload(uuid.uuid4(), "image/svg+xml", 1024)

    def test_request_upload_validates_file_size(self, photo_service):
        with pytest.raises(ValidationException, match="exceeds the maximum"):
            photo_service.request_upload(uuid.uuid4(), "image/jpeg", MAX_FILE_SIZE + 1)


# ── URL Resolution Tests ──────────────────────────────────────

class TestResolvePhotoUrl:
    """Tests for resolving stored profile_image to usable URLs."""

    def test_resolve_photo_url_none_for_null(self, photo_service):
        assert photo_service.resolve_photo_url(None) is None

    def test_resolve_photo_url_none_for_empty(self, photo_service):
        assert photo_service.resolve_photo_url("") is None

    def test_resolve_photo_url_presigned_for_s3_key(self, photo_service, mock_storage):
        key = "users/some-uuid/profile/abc123.jpg"
        result = photo_service.resolve_photo_url(key)
        assert result == "https://s3.amazonaws.com/presigned-get-url"
        mock_storage.generate_download_url.assert_called_once_with(key=key, expires_in=900)

    def test_resolve_photo_url_none_for_http_url(self, photo_service, mock_storage):
        """Legacy OAuth URLs should return None to force re-upload."""
        result = photo_service.resolve_photo_url("https://lh3.googleusercontent.com/a/photo")
        assert result is None
        mock_storage.generate_download_url.assert_not_called()

    def test_resolve_photo_url_none_for_http_url_github(self, photo_service, mock_storage):
        result = photo_service.resolve_photo_url("https://avatars.githubusercontent.com/u/12345")
        assert result is None
        mock_storage.generate_download_url.assert_not_called()

    def test_resolve_photo_url_handles_s3_error_gracefully(self, photo_service, mock_storage):
        mock_storage.generate_download_url.side_effect = Exception("S3 error")
        result = photo_service.resolve_photo_url("users/id/profile/abc.jpg")
        assert result is None


# ── Confirm Upload Tests ──────────────────────────────────────

class TestConfirmUpload:
    """Tests for confirming a photo upload and saving the key."""

    @pytest.fixture
    def mock_user(self):
        user = MagicMock()
        user.user_id = uuid.uuid4()
        user.user_profile_image = None
        return user

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_confirm_upload_saves_key(self, photo_service, mock_user, mock_db, mock_storage):
        key = f"users/{mock_user.user_id}/profile/abc123.jpg"
        updated = await photo_service.confirm_upload(mock_db, mock_user, key)

        assert updated.user_profile_image == key
        mock_db.add.assert_called_once_with(mock_user)
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_confirm_upload_deletes_old_s3_object(self, photo_service, mock_user, mock_db, mock_storage):
        old_key = f"users/{mock_user.user_id}/profile/old_photo.jpg"
        mock_user.user_profile_image = old_key
        new_key = f"users/{mock_user.user_id}/profile/new_photo.jpg"

        await photo_service.confirm_upload(mock_db, mock_user, new_key)

        mock_storage.delete_object.assert_called_once_with(old_key)
        assert mock_user.user_profile_image == new_key

    @pytest.mark.asyncio
    async def test_confirm_upload_skips_delete_for_legacy_http(self, photo_service, mock_user, mock_db, mock_storage):
        mock_user.user_profile_image = "https://lh3.googleusercontent.com/old"
        new_key = f"users/{mock_user.user_id}/profile/new_photo.jpg"

        await photo_service.confirm_upload(mock_db, mock_user, new_key)

        mock_storage.delete_object.assert_not_called()
        assert mock_user.user_profile_image == new_key

    @pytest.mark.asyncio
    async def test_confirm_upload_same_key_does_not_delete(self, photo_service, mock_user, mock_db, mock_storage):
        same_key = f"users/{mock_user.user_id}/profile/photo.jpg"
        mock_user.user_profile_image = same_key

        await photo_service.confirm_upload(mock_db, mock_user, same_key)

        mock_storage.delete_object.assert_not_called()
        assert mock_user.user_profile_image == same_key

    @pytest.mark.asyncio
    async def test_confirm_upload_wrong_user_key_rejected(self, photo_service, mock_user, mock_db):
        wrong_key = f"users/{uuid.uuid4()}/profile/abc.jpg"
        with pytest.raises(ValidationException, match="does not belong"):
            await photo_service.confirm_upload(mock_db, mock_user, wrong_key)

    @pytest.mark.asyncio
    async def test_confirm_upload_nonexistent_object_fails(self, photo_service, mock_user, mock_db, mock_storage):
        key = f"users/{mock_user.user_id}/profile/missing.jpg"
        mock_storage.object_exists.return_value = False

        with pytest.raises(StorageException, match="not found in storage"):
            await photo_service.confirm_upload(mock_db, mock_user, key)


# ── Delete Photo Tests ────────────────────────────────────────

class TestDeletePhoto:
    """Tests for deleting a user's profile photo."""

    @pytest.fixture
    def mock_user(self):
        user = MagicMock()
        user.user_id = uuid.uuid4()
        user.user_profile_image = f"users/{uuid.uuid4()}/profile/photo.jpg"
        return user

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_delete_photo_clears_field(self, photo_service, mock_user, mock_db):
        await photo_service.delete_photo(mock_db, mock_user)
        assert mock_user.user_profile_image is None

    @pytest.mark.asyncio
    async def test_delete_photo_deletes_s3_object(self, photo_service, mock_user, mock_db, mock_storage):
        old_key = mock_user.user_profile_image
        await photo_service.delete_photo(mock_db, mock_user)
        mock_storage.delete_object.assert_called_once_with(old_key)

    @pytest.mark.asyncio
    async def test_delete_photo_handles_no_photo(self, photo_service, mock_db, mock_storage):
        user = MagicMock()
        user.user_profile_image = None
        await photo_service.delete_photo(mock_db, user)
        mock_storage.delete_object.assert_not_called()
        assert user.user_profile_image is None


# ── OAuth Registration Tests ──────────────────────────────────

class TestOAuthNoAvatar:
    """Verify OAuth registration does not store provider avatar URLs."""

    def test_google_avatar_url_resolves_to_none(self, photo_service):
        """Google avatar URL in user_profile_image should not be served."""
        url = "https://lh3.googleusercontent.com/a/ACg8ocJ..."
        assert photo_service.resolve_photo_url(url) is None

    def test_github_avatar_url_resolves_to_none(self, photo_service):
        """GitHub avatar URL in user_profile_image should not be served."""
        url = "https://avatars.githubusercontent.com/u/12345?v=4"
        assert photo_service.resolve_photo_url(url) is None
