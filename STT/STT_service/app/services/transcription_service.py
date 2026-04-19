"""
STT Service - Transcription Orchestrator

Coordinates the full transcription pipeline:
  1. Save audio to storage
  2. Create job record in database
  3. Dispatch Celery task
  4. Query job status / results
"""

import dataclasses
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from app.core.logging_config import get_logger
from app.db.database import get_db_session
from app.db.models import TranscriptionJob, TranscriptionResult

logger = get_logger(__name__)


async def create_job(
    api_key_id: str,
    file_name: str,
    file_path: str,
    file_size: int,
    language: Optional[str] = None,
) -> TranscriptionJob:
    """
    Create a new transcription job in the database.
    
    Returns the created job record with a unique ID
    that the client can use to poll for status.
    """
    async with get_db_session() as session:
        job = TranscriptionJob(
            api_key_id=api_key_id,
            file_name=file_name,
            file_path=file_path,
            file_size_bytes=file_size,
            language=language,
            status="pending",
        )
        session.add(job)
        await session.flush()
        await session.refresh(job)

        logger.info(
            "job_created",
            job_id=job.id,
            file_name=file_name,
            language=language or "auto",
        )
        return job


async def get_job(job_id: str, api_key_id: str) -> Optional[TranscriptionJob]:
    """
    Get a transcription job by ID, scoped to the API key owner.
    
    Returns None if the job doesn't exist or belongs to another key.
    """
    async with get_db_session() as session:
        result = await session.execute(
            select(TranscriptionJob).where(
                TranscriptionJob.id == job_id,
                TranscriptionJob.api_key_id == api_key_id,
            )
        )
        return result.scalar_one_or_none()


async def get_job_with_result(
    job_id: str,
    api_key_id: str,
) -> Optional[dict]:
    """
    Get a job with its transcription result.
    
    Returns a dict combining job metadata and transcription output.
    """
    async with get_db_session() as session:
        # Get job
        job_result = await session.execute(
            select(TranscriptionJob).where(
                TranscriptionJob.id == job_id,
                TranscriptionJob.api_key_id == api_key_id,
            )
        )
        job = job_result.scalar_one_or_none()
        if not job:
            return None

        # Get result if completed
        result = None
        if job.status == "completed":
            result_query = await session.execute(
                select(TranscriptionResult).where(
                    TranscriptionResult.job_id == job_id,
                )
            )
            result = result_query.scalar_one_or_none()

        return {
            "job": job,
            "result": result,
        }


async def update_job_status(
    job_id: str,
    status: str,
    error_message: Optional[str] = None,
    detected_language: Optional[str] = None,
    duration_seconds: Optional[float] = None,
) -> None:
    """
    Update the status of a transcription job.
    
    Called by Celery workers as the job progresses.
    """
    async with get_db_session() as session:
        result = await session.execute(
            select(TranscriptionJob).where(TranscriptionJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            logger.error("job_not_found_for_update", job_id=job_id)
            return

        job.status = status
        if error_message:
            job.error_message = error_message
        if detected_language:
            job.detected_language = detected_language
        if duration_seconds:
            job.duration_seconds = duration_seconds

        if status == "processing":
            job.started_at = datetime.now(timezone.utc)
        elif status in ("completed", "failed"):
            job.completed_at = datetime.now(timezone.utc)

        logger.info("job_status_updated", job_id=job_id, status=status)


async def save_transcription_result(
    job_id: str,
    transcription_result,
) -> TranscriptionResult:
    """
    Save a transcription result to the database.
    
    Converts the WhisperService's TranscriptionResult dataclass
    into a database record with JSON segments.
    """
    async with get_db_session() as session:
        # Convert segments to JSON-serializable format
        segments_json = []
        for seg in transcription_result.segments:
            seg_dict = {
                "id": seg.id,
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
                "confidence": seg.confidence,
                "words": [
                    {
                        "word": w.word,
                        "start": w.start,
                        "end": w.end,
                        "confidence": w.confidence,
                    }
                    for w in seg.words
                ],
            }
            segments_json.append(seg_dict)

        db_result = TranscriptionResult(
            job_id=job_id,
            full_text=transcription_result.full_text,
            confidence=transcription_result.confidence,
            language=transcription_result.language,
            duration_seconds=transcription_result.duration,
            segments=segments_json,
            word_count=len(transcription_result.full_text.split()),
        )
        session.add(db_result)

        logger.info(
            "result_saved",
            job_id=job_id,
            word_count=db_result.word_count,
            segments=len(segments_json),
        )
        return db_result
