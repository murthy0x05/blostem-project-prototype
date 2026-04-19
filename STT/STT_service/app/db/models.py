"""
STT Service - Database Models (SQLAlchemy ORM)

Defines the three core tables:
  1. api_keys     - API key authentication records
  2. transcription_jobs    - Job tracking (status, metadata)
  3. transcription_results - Transcription output (text, timestamps, confidence)
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, relationship


def generate_uuid() -> str:
    """Generate a UUID4 string for primary keys."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class APIKey(Base):
    """
    API Key records.
    
    Stores hashed API keys with metadata.
    Raw keys are NEVER stored — only SHA-256 hashes.
    """
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=generate_uuid)
    key_hash = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    is_active = Column(Boolean, default=True)
    rate_limit = Column(Integer, default=100)

    # Relationships
    jobs = relationship("TranscriptionJob", back_populates="api_key")

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, name={self.name}, active={self.is_active})>"


class TranscriptionJob(Base):
    """
    Transcription job tracking.
    
    Each uploaded audio file creates a job that progresses through:
    pending → processing → completed | failed
    """
    __tablename__ = "transcription_jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    api_key_id = Column(String, ForeignKey("api_keys.id"), nullable=False)
    status = Column(String, default="pending", index=True)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    language = Column(String, nullable=True)  # Requested language (None = auto-detect)
    detected_language = Column(String, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    api_key = relationship("APIKey", back_populates="jobs")
    result = relationship(
        "TranscriptionResult",
        back_populates="job",
        uselist=False,  # One-to-one
    )

    def __repr__(self) -> str:
        return f"<TranscriptionJob(id={self.id}, status={self.status})>"


class TranscriptionResult(Base):
    """
    Transcription output.
    
    Stores the full transcribed text, overall confidence score,
    and word-level timestamps as a JSON array.
    
    Segments format:
    [
        {
            "id": 0,
            "start": 0.0,
            "end": 2.5,
            "text": "Hello world",
            "confidence": 0.95,
            "words": [
                {"word": "Hello", "start": 0.0, "end": 1.0, "confidence": 0.96},
                {"word": "world", "start": 1.2, "end": 2.5, "confidence": 0.94}
            ]
        }
    ]
    """
    __tablename__ = "transcription_results"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(
        String,
        ForeignKey("transcription_jobs.id"),
        nullable=False,
        unique=True,
    )
    full_text = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)
    language = Column(String, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    segments = Column(JSON, nullable=True)  # Word-level timestamps
    word_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    job = relationship("TranscriptionJob", back_populates="result")

    def __repr__(self) -> str:
        return f"<TranscriptionResult(id={self.id}, job_id={self.job_id})>"
