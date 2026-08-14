import re
from typing import Any
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.exceptions import StorageException, ValidationException


def validate_storage_key(key: str) -> str:
    """
    Validate S3 object key to prevent unsafe paths:
    - Empty or whitespace-only keys
    - Absolute paths (starting with '/' or '\\' or Windows drive letters)
    - Path traversal ('..' components)

    Returns trimmed key if valid, raises ValidationException if invalid.
    """
    if not isinstance(key, str):
        raise ValidationException("Storage key must be a string.")

    clean_key = key.strip()
    if not clean_key:
        raise ValidationException("Storage key cannot be empty.")

    # Check absolute paths (leading slashes/backslashes)
    if clean_key.startswith("/") or clean_key.startswith("\\"):
        raise ValidationException("Storage key cannot be an absolute path.")

    # Windows drive specifiers (e.g. C:, D:)
    if re.match(r"^[a-zA-Z]:", clean_key):
        raise ValidationException("Storage key cannot be an absolute path.")

    # Path traversal check
    normalized = clean_key.replace("\\", "/")
    parts = normalized.split("/")
    if ".." in parts:
        raise ValidationException("Storage key cannot contain path traversal ('..').")

    return clean_key


class S3StorageService:
    """
    Generic service for interacting with AWS S3 storage using boto3 and presigned URLs.
    Does not expose AWS credentials and does not contain domain-specific business logic.
    """

    def __init__(self, s3_client: Any = None, bucket_name: str | None = None) -> None:
        """
        Initialize the S3 storage service.
        If s3_client is not provided, it initializes boto3 S3 client using app Settings.
        """
        self.bucket_name = settings.AWS_S3_BUCKET if bucket_name is None else bucket_name

        if s3_client is not None:
            self.s3_client = s3_client
        else:
            config = Config(
                signature_version="s3v4",
                region_name=settings.AWS_REGION,
                s3={"addressing_style": "virtual"}
            )
            client_kwargs: dict[str, Any] = {"config": config}
            if settings.AWS_REGION:
                client_kwargs["region_name"] = settings.AWS_REGION
                client_kwargs["endpoint_url"] = f"https://s3.{settings.AWS_REGION}.amazonaws.com"
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                client_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
                client_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY

            self.s3_client = boto3.client("s3", **client_kwargs)

    def generate_upload_url(self, key: str, content_type: str, expires_in: int = 900) -> str:
        """
        Generate a presigned URL for uploading (PUT) an object to S3.

        :param key: Destination S3 key/path.
        :param content_type: MIME type of the file to be uploaded.
        :param expires_in: Expiration time in seconds (default 900s / 15 minutes).
        :return: Presigned upload URL string.
        """
        validated_key = validate_storage_key(key)
        if not content_type or not content_type.strip():
            raise ValidationException("Content type must be provided for upload URL generation.")

        if not self.bucket_name:
            raise StorageException("S3 bucket name is not configured.")

        try:
            url: str = self.s3_client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": validated_key,
                    "ContentType": content_type.strip(),
                },
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            raise StorageException(
                f"Failed to generate presigned upload URL: {e.response.get('Error', {}).get('Message', str(e))}"
            )
        except Exception as e:
            if isinstance(e, (ValidationException, StorageException)):
                raise
            raise StorageException(f"Unexpected error generating presigned upload URL: {str(e)}")

    def generate_download_url(self, key: str, expires_in: int = 900) -> str:
        """
        Generate a presigned URL for downloading (GET) an object from S3.

        :param key: S3 key/path.
        :param expires_in: Expiration time in seconds (default 900s / 15 minutes).
        :return: Presigned download URL string.
        """
        validated_key = validate_storage_key(key)

        if not self.bucket_name:
            raise StorageException("S3 bucket name is not configured.")

        try:
            url: str = self.s3_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": validated_key,
                },
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            raise StorageException(
                f"Failed to generate presigned download URL: {e.response.get('Error', {}).get('Message', str(e))}"
            )
        except Exception as e:
            if isinstance(e, (ValidationException, StorageException)):
                raise
            raise StorageException(f"Unexpected error generating presigned download URL: {str(e)}")

    def delete_object(self, key: str) -> None:
        """
        Delete an object from S3.

        :param key: S3 key/path to delete.
        """
        validated_key = validate_storage_key(key)

        if not self.bucket_name:
            raise StorageException("S3 bucket name is not configured.")

        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=validated_key,
            )
        except ClientError as e:
            raise StorageException(
                f"Failed to delete object from S3: {e.response.get('Error', {}).get('Message', str(e))}"
            )
        except Exception as e:
            if isinstance(e, (ValidationException, StorageException)):
                raise
            raise StorageException(f"Unexpected error deleting object: {str(e)}")

    def object_exists(self, key: str) -> bool:
        """
        Check if an object exists in S3.

        :param key: S3 key/path to check.
        :return: True if object exists, False otherwise.
        """
        validated_key = validate_storage_key(key)

        if not self.bucket_name:
            raise StorageException("S3 bucket name is not configured.")

        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=validated_key,
            )
            return True
        except ClientError as e:
            error_code = str(e.response.get("Error", {}).get("Code", ""))
            status_code = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if error_code in ("404", "NoSuchKey", "NotFound") or status_code == 404:
                return False
            raise StorageException(
                f"Failed to check object existence in S3: {e.response.get('Error', {}).get('Message', str(e))}"
            )
        except Exception as e:
            if isinstance(e, (ValidationException, StorageException)):
                raise
            raise StorageException(f"Unexpected error checking object existence: {str(e)}")
