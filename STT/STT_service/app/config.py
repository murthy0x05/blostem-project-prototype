"""
STT Service - Application Configuration

Centralized settings management using Pydantic Settings.
All configuration is loaded from environment variables with sensible defaults.
"""

import json
from pathlib import Path
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "STT-Service"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # --- Whisper Model ---
    whisper_model_size: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_download_root: str = "./models"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Celery ---
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./data/stt_service.db"

    # --- Storage ---
    storage_backend: str = "local"  # "local" or "s3"
    upload_dir: str = "./uploads"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "stt-service-audio"

    # --- Rate Limiting ---
    rate_limit_per_minute: int = 100

    # --- Logging ---
    log_level: str = "INFO"

    # --- CORS ---
    cors_origins: str = '["http://localhost:3000","http://localhost:8000"]'

    # --- Upload Limits ---
    max_upload_size_mb: int = 25
    max_audio_duration_seconds: int = 300

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from JSON string."""
        try:
            return json.loads(self.cors_origins)
        except (json.JSONDecodeError, TypeError):
            return ["*"]

    @property
    def max_upload_size_bytes(self) -> int:
        """Maximum upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def database_path(self) -> Path:
        """Extract the file path from the SQLite URL."""
        db_path = self.database_url.replace("sqlite+aiosqlite:///", "")
        return Path(db_path)


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings singleton.
    Returns the same Settings instance across all calls.
    """
    return Settings()
