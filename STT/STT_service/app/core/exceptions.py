"""
STT Service - Custom Exceptions

Centralized exception hierarchy for clean error handling across the application.
Each exception maps to a specific HTTP status code.
"""

from typing import Any, Optional


class STTServiceError(Exception):
    """Base exception for all STT Service errors."""

    def __init__(
        self,
        message: str = "An internal error occurred",
        status_code: int = 500,
        detail: Optional[Any] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)


class AudioValidationError(STTServiceError):
    """Raised when audio file validation fails (wrong format, too large, etc.)."""

    def __init__(self, message: str = "Invalid audio file"):
        super().__init__(message=message, status_code=400)


class AudioProcessingError(STTServiceError):
    """Raised when audio preprocessing fails (conversion, noise handling)."""

    def __init__(self, message: str = "Failed to process audio file"):
        super().__init__(message=message, status_code=422)


class TranscriptionError(STTServiceError):
    """Raised when the Whisper model fails to transcribe."""

    def __init__(self, message: str = "Transcription failed"):
        super().__init__(message=message, status_code=500)


class JobNotFoundError(STTServiceError):
    """Raised when a transcription job ID is not found."""

    def __init__(self, job_id: str):
        super().__init__(
            message=f"Transcription job '{job_id}' not found",
            status_code=404,
        )


class RateLimitExceededError(STTServiceError):
    """Raised when a client exceeds their rate limit."""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            status_code=429,
            detail={"retry_after_seconds": retry_after},
        )


class AuthenticationError(STTServiceError):
    """Raised when API key authentication fails."""

    def __init__(self, message: str = "Invalid or missing API key"):
        super().__init__(message=message, status_code=401)


class StorageError(STTServiceError):
    """Raised when file storage operations fail."""

    def __init__(self, message: str = "Storage operation failed"):
        super().__init__(message=message, status_code=500)
