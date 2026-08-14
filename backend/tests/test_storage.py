from unittest.mock import MagicMock, patch
import pytest
from botocore.exceptions import ClientError

from app.core.exceptions import StorageException, ValidationException
from app.core.storage import S3StorageService, validate_storage_key


class TestKeyValidation:
    """Unit tests for storage key validation."""

    def test_valid_keys(self):
        valid_keys = [
            "avatar.png",
            "uploads/user_123/avatar.jpg",
            "documents/2026/report.pdf",
            "a/b/c/d/file.txt",
        ]
        for key in valid_keys:
            assert validate_storage_key(key) == key

    def test_empty_keys_raise_validation_error(self):
        invalid_keys = ["", "   ", "\t\n"]
        for key in invalid_keys:
            with pytest.raises(ValidationException, match="cannot be empty"):
                validate_storage_key(key)

    def test_non_string_key_raises_validation_error(self):
        with pytest.raises(ValidationException, match="must be a string"):
            validate_storage_key(123)  # type: ignore

    def test_absolute_paths_raise_validation_error(self):
        absolute_keys = [
            "/root/file.txt",
            "\\windows\\system32\\cmd.exe",
            "C:/Users/file.png",
            "D:\\data\\file.csv",
        ]
        for key in absolute_keys:
            with pytest.raises(ValidationException, match="cannot be an absolute path"):
                validate_storage_key(key)

    def test_path_traversal_raises_validation_error(self):
        traversal_keys = [
            "../etc/passwd",
            "uploads/../secret.png",
            "files/dir/..",
            "files\\..\\secret.txt",
        ]
        for key in traversal_keys:
            with pytest.raises(ValidationException, match="path traversal"):
                validate_storage_key(key)


class TestS3StorageService:
    """Unit tests for S3StorageService operations using a mocked boto3 client."""

    @pytest.fixture
    def mock_s3_client(self):
        return MagicMock()

    @pytest.fixture
    def storage_service(self, mock_s3_client):
        return S3StorageService(s3_client=mock_s3_client, bucket_name="test-bucket")

    def test_generate_upload_url_success(self, storage_service, mock_s3_client):
        expected_url = "https://test-bucket.s3.amazonaws.com/uploads/photo.jpg?sig=123"
        mock_s3_client.generate_presigned_url.return_value = expected_url

        url = storage_service.generate_upload_url(
            key="uploads/photo.jpg",
            content_type="image/jpeg",
            expires_in=600,
        )

        assert url == expected_url
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            ClientMethod="put_object",
            Params={
                "Bucket": "test-bucket",
                "Key": "uploads/photo.jpg",
                "ContentType": "image/jpeg",
            },
            ExpiresIn=600,
        )

    def test_generate_upload_url_empty_content_type(self, storage_service):
        with pytest.raises(ValidationException, match="Content type must be provided"):
            storage_service.generate_upload_url("uploads/photo.jpg", content_type="")

    def test_generate_download_url_success(self, storage_service, mock_s3_client):
        expected_url = "https://test-bucket.s3.amazonaws.com/uploads/photo.jpg?sig=456"
        mock_s3_client.generate_presigned_url.return_value = expected_url

        url = storage_service.generate_download_url(
            key="uploads/photo.jpg",
            expires_in=300,
        )

        assert url == expected_url
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            ClientMethod="get_object",
            Params={
                "Bucket": "test-bucket",
                "Key": "uploads/photo.jpg",
            },
            ExpiresIn=300,
        )

    def test_delete_object_success(self, storage_service, mock_s3_client):
        storage_service.delete_object(key="uploads/photo.jpg")

        mock_s3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="uploads/photo.jpg",
        )

    def test_object_exists_returns_true(self, storage_service, mock_s3_client):
        mock_s3_client.head_object.return_value = {"ContentLength": 1024}

        assert storage_service.object_exists("uploads/photo.jpg") is True
        mock_s3_client.head_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="uploads/photo.jpg",
        )

    def test_object_exists_returns_false_on_404(self, storage_service, mock_s3_client):
        error_response = {
            "Error": {"Code": "404", "Message": "Not Found"},
            "ResponseMetadata": {"HTTPStatusCode": 404},
        }
        mock_s3_client.head_object.side_effect = ClientError(error_response, "HeadObject")

        assert storage_service.object_exists("uploads/nonexistent.jpg") is False

    def test_object_exists_returns_false_on_nosuchkey(self, storage_service, mock_s3_client):
        error_response = {
            "Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."},
            "ResponseMetadata": {"HTTPStatusCode": 404},
        }
        mock_s3_client.head_object.side_effect = ClientError(error_response, "HeadObject")

        assert storage_service.object_exists("uploads/nonexistent.jpg") is False

    def test_client_error_handling_in_generate_upload_url(self, storage_service, mock_s3_client):
        error_response = {
            "Error": {"Code": "AccessDenied", "Message": "Access Denied"},
            "ResponseMetadata": {"HTTPStatusCode": 403},
        }
        mock_s3_client.generate_presigned_url.side_effect = ClientError(error_response, "PutObject")

        with pytest.raises(StorageException, match="Failed to generate presigned upload URL"):
            storage_service.generate_upload_url("uploads/photo.jpg", content_type="image/jpeg")

    def test_client_error_handling_in_generate_download_url(self, storage_service, mock_s3_client):
        error_response = {
            "Error": {"Code": "AccessDenied", "Message": "Access Denied"},
            "ResponseMetadata": {"HTTPStatusCode": 403},
        }
        mock_s3_client.generate_presigned_url.side_effect = ClientError(error_response, "GetObject")

        with pytest.raises(StorageException, match="Failed to generate presigned download URL"):
            storage_service.generate_download_url("uploads/photo.jpg")

    def test_client_error_handling_in_delete_object(self, storage_service, mock_s3_client):
        error_response = {
            "Error": {"Code": "InternalError", "Message": "Internal Error"},
            "ResponseMetadata": {"HTTPStatusCode": 500},
        }
        mock_s3_client.delete_object.side_effect = ClientError(error_response, "DeleteObject")

        with pytest.raises(StorageException, match="Failed to delete object from S3"):
            storage_service.delete_object("uploads/photo.jpg")

    def test_client_error_handling_in_object_exists_raises_storage_exception(
        self, storage_service, mock_s3_client
    ):
        error_response = {
            "Error": {"Code": "500", "Message": "Internal Error"},
            "ResponseMetadata": {"HTTPStatusCode": 500},
        }
        mock_s3_client.head_object.side_effect = ClientError(error_response, "HeadObject")

        with pytest.raises(StorageException, match="Failed to check object existence"):
            storage_service.object_exists("uploads/photo.jpg")

    def test_unconfigured_bucket_raises_storage_exception(self, mock_s3_client):
        service = S3StorageService(s3_client=mock_s3_client, bucket_name="")
        with pytest.raises(StorageException, match="bucket name is not configured"):
            service.generate_upload_url("test.txt", "text/plain")

    @patch("boto3.client")
    def test_boto3_client_initialization_from_settings(self, mock_boto_client):
        service = S3StorageService()
        assert service.bucket_name is not None
        mock_boto_client.assert_called_once()
