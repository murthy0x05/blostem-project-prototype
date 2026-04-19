"""
STT Service - Audio Processor

Handles audio validation, format conversion, and metadata extraction.
Converts all input formats (WAV, MP3, M4A) to 16kHz mono WAV for Whisper.
"""

import os
import tempfile
from pathlib import Path
from typing import Tuple

from pydub import AudioSegment

from app.config import get_settings
from app.core.exceptions import AudioValidationError, AudioProcessingError
from app.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Supported audio formats and their MIME types
SUPPORTED_FORMATS = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
}

# Content type to extension mapping
CONTENT_TYPE_MAP = {
    "audio/wav": ".wav",
    "audio/wave": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/aac": ".m4a",
}


def validate_audio_file(
    file_name: str,
    file_size: int,
    content_type: str = None,
) -> str:
    """
    Validate an uploaded audio file before processing.
    
    Checks:
      1. File extension is supported (wav, mp3, m4a)
      2. File size is within limits
    
    Args:
        file_name: Original filename.
        file_size: File size in bytes.
        content_type: MIME type from upload.
    
    Returns:
        The validated file extension.
    
    Raises:
        AudioValidationError: If validation fails.
    """
    # Check extension
    ext = Path(file_name).suffix.lower()
    if ext not in SUPPORTED_FORMATS:
        raise AudioValidationError(
            f"Unsupported audio format '{ext}'. "
            f"Supported formats: {', '.join(SUPPORTED_FORMATS.keys())}"
        )

    # Check file size
    max_size = settings.max_upload_size_bytes
    if file_size > max_size:
        raise AudioValidationError(
            f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds "
            f"maximum allowed size ({settings.max_upload_size_mb}MB)."
        )

    logger.info(
        "audio_validated",
        file_name=file_name,
        format=ext,
        size_mb=round(file_size / 1024 / 1024, 2),
    )

    return ext


def convert_to_wav(input_path: str) -> Tuple[str, float]:
    """
    Convert any supported audio format to 16kHz mono WAV.
    
    Whisper performs best with 16kHz mono WAV input.
    
    Args:
        input_path: Path to the input audio file.
    
    Returns:
        Tuple of (output_wav_path, duration_seconds).
    
    Raises:
        AudioProcessingError: If conversion fails.
    """
    try:
        ext = Path(input_path).suffix.lower()
        logger.info("audio_conversion_started", input_path=input_path, format=ext)

        # Load audio based on format
        if ext == ".wav":
            audio = AudioSegment.from_wav(input_path)
        elif ext == ".mp3":
            audio = AudioSegment.from_mp3(input_path)
        elif ext == ".m4a":
            audio = AudioSegment.from_file(input_path, format="m4a")
        else:
            audio = AudioSegment.from_file(input_path)

        # Convert to 16kHz mono (optimal for Whisper)
        audio = audio.set_frame_rate(16000).set_channels(1)

        # Get duration
        duration_seconds = len(audio) / 1000.0

        # Check duration limit
        if duration_seconds > settings.max_audio_duration_seconds:
            raise AudioValidationError(
                f"Audio duration ({duration_seconds:.1f}s) exceeds "
                f"maximum allowed ({settings.max_audio_duration_seconds}s)."
            )

        # Export to temporary WAV file
        output_path = input_path.rsplit(".", 1)[0] + "_converted.wav"
        audio.export(output_path, format="wav")

        logger.info(
            "audio_conversion_completed",
            output_path=output_path,
            duration_seconds=round(duration_seconds, 2),
            sample_rate=16000,
            channels=1,
        )

        return output_path, duration_seconds

    except AudioValidationError:
        raise
    except Exception as e:
        logger.error("audio_conversion_failed", error=str(e), input_path=input_path)
        raise AudioProcessingError(f"Failed to process audio: {str(e)}")


def get_audio_duration(file_path: str) -> float:
    """
    Get the duration of an audio file in seconds.
    
    Args:
        file_path: Path to the audio file.
    
    Returns:
        Duration in seconds.
    """
    try:
        ext = Path(file_path).suffix.lower()
        if ext == ".wav":
            audio = AudioSegment.from_wav(file_path)
        elif ext == ".mp3":
            audio = AudioSegment.from_mp3(file_path)
        else:
            audio = AudioSegment.from_file(file_path)
        return len(audio) / 1000.0
    except Exception as e:
        logger.error("duration_extraction_failed", error=str(e))
        return 0.0
