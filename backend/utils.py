"""
Utility functions and data models for the STT service.
"""

import io
import tempfile
from pathlib import Path
from typing import List, Optional

from pydub import AudioSegment
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class SegmentInfo(BaseModel):
    """A contiguous speech segment with timing information."""
    start: float = Field(..., description="Segment start time in seconds.")
    end: float = Field(..., description="Segment end time in seconds.")
    text: str = Field(..., description="Transcribed text of this segment.")


class WordInfo(BaseModel):
    """A single recognised word with timing information."""
    word: str = Field(..., description="The recognised word.")
    start: float = Field(..., description="Start time in seconds.")
    end: float = Field(..., description="End time in seconds.")


class ProcessingMetadata(BaseModel):
    """Metadata about how the request was processed."""
    processing_time: float = Field(
        ..., description="Wall-clock processing time in seconds."
    )
    model_name: Optional[str] = Field(
        default=None, description="Whisper model used for this transcription."
    )
    device: Optional[str] = Field(
        default=None, description="Device used for inference."
    )
    compute_type: Optional[str] = Field(
        default=None, description="Compute precision used for inference."
    )


class TranscriptionResponse(BaseModel):
    """
    Canonical output for every STT service endpoint.
    """
    text: str = Field(..., description="Final processed text.")
    language: str = Field(
        ..., description="Detected language code ('en' or 'hi')."
    )
    segments: List[SegmentInfo] = Field(
        default_factory=list, description="Timed segments of the transcription."
    )
    words: List[WordInfo] = Field(
        default_factory=list, description="Word-level timing information."
    )
    metadata: ProcessingMetadata = Field(
        ..., description="Processing metadata."
    )


class ErrorResponse(BaseModel):
    """Standard error envelope."""
    detail: str = Field(..., description="Error message.")


# ---------------------------------------------------------------------------
# Audio Processing Utilities
# ---------------------------------------------------------------------------

def normalise_audio(raw_bytes: bytes, filename: str) -> str:
    """
    Convert arbitrary audio to a 16 kHz mono WAV temp file.
    Returns the path to the temporary file (caller must clean up).
    """
    suffix = Path(filename).suffix.lower() if filename else ".wav"
    fmt = suffix.lstrip(".")
    if fmt not in ("wav", "mp3", "ogg", "flac", "webm", "m4a"):
        fmt = "wav"

    try:
        audio = AudioSegment.from_file(io.BytesIO(raw_bytes), format=fmt)
    except Exception as exc:
        raise ValueError(f"Could not decode audio file: {exc}")

    # Normalise: mono, 16 kHz
    audio = audio.set_channels(1).set_frame_rate(16000)

    # Max 30 seconds as requested in performance considerations
    max_ms = 30 * 1000
    if len(audio) > max_ms:
        audio = audio[:max_ms]

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    audio.export(tmp.name, format="wav")
    tmp.close()
    return tmp.name
