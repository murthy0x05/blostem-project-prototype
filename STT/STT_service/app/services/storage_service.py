"""
STT Service - File Storage Service

Handles saving and retrieving audio files.
Supports two backends:
  - Local filesystem (development)
  - AWS S3 (production)

Configurable via STORAGE_BACKEND env var.
"""

import os
import uuid
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.core.exceptions import StorageError
from app.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


class LocalStorage:
    """Local filesystem storage backend."""

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or settings.upload_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, file_data: bytes, filename: str) -> str:
        """
        Save a file to local storage.
        
        Files are stored with a UUID prefix to prevent name collisions.
        
        Returns:
            The full path to the saved file.
        """
        try:
            # Generate unique filename
            unique_name = f"{uuid.uuid4().hex}_{filename}"
            file_path = self.base_dir / unique_name

            with open(file_path, "wb") as f:
                f.write(file_data)

            logger.info(
                "file_saved_locally",
                path=str(file_path),
                size_bytes=len(file_data),
            )
            return str(file_path)

        except Exception as e:
            logger.error("local_save_failed", error=str(e))
            raise StorageError(f"Failed to save file locally: {str(e)}")

    async def get(self, file_path: str) -> bytes:
        """Read a file from local storage."""
        try:
            with open(file_path, "rb") as f:
                return f.read()
        except FileNotFoundError:
            raise StorageError(f"File not found: {file_path}")

    async def delete(self, file_path: str) -> bool:
        """Delete a file from local storage."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info("file_deleted", path=file_path)
                return True
            return False
        except Exception as e:
            logger.error("local_delete_failed", error=str(e))
            return False


class S3Storage:
    """AWS S3 storage backend for production."""

    def __init__(self):
        import boto3
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
        )
        self.bucket = settings.s3_bucket_name

    async def save(self, file_data: bytes, filename: str) -> str:
        """
        Upload a file to S3.
        
        Returns:
            The S3 key (path) of the uploaded file.
        """
        try:
            key = f"uploads/{uuid.uuid4().hex}_{filename}"
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=file_data,
            )
            logger.info(
                "file_saved_s3",
                bucket=self.bucket,
                key=key,
                size_bytes=len(file_data),
            )
            return key
        except Exception as e:
            logger.error("s3_save_failed", error=str(e))
            raise StorageError(f"Failed to upload to S3: {str(e)}")

    async def get(self, key: str) -> bytes:
        """Download a file from S3."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except Exception as e:
            raise StorageError(f"Failed to download from S3: {str(e)}")

    async def delete(self, key: str) -> bool:
        """Delete a file from S3."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=key)
            logger.info("file_deleted_s3", key=key)
            return True
        except Exception as e:
            logger.error("s3_delete_failed", error=str(e))
            return False


def get_storage():
    """
    Factory function to get the appropriate storage backend.
    
    Returns LocalStorage for development, S3Storage for production.
    Controlled by the STORAGE_BACKEND env var.
    """
    if settings.storage_backend == "s3":
        return S3Storage()
    return LocalStorage()
