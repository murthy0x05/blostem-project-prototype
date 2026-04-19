"""
Text-input service — uses langdetect to detect language and maps to standard schema.
"""

import logging
import time

from langdetect import detect, LangDetectException

from backend.utils import (
    ProcessingMetadata,
    SegmentInfo,
    TranscriptionResponse,
)

logger = logging.getLogger(__name__)


def process_text_sync(text: str) -> TranscriptionResponse:
    """
    Wrap plain-text string in the standard TranscriptionResponse format.
    """
    t0 = time.perf_counter()

    if not text or not text.strip():
        raise ValueError("Text input must not be empty.")

    text = text.strip()

    # --- Language detection ---
    try:
        language = detect(text)
        # normalize to basic language codes ('en', 'hi') if possible
        if language not in ('en', 'hi'):
            # Just keep the detected code or fallback to unknown
            pass
    except LangDetectException:
        language = "unknown"

    # --- Synthetic segment ---
    segments = [
        SegmentInfo(start=0.0, end=0.0, text=text),
    ]

    processing_time = time.perf_counter() - t0

    return TranscriptionResponse(
        text=text,
        language=language,
        segments=segments,
        words=[],
        metadata=ProcessingMetadata(
            processing_time=round(processing_time, 6),
            model_name="langdetect",
            device="cpu",
            compute_type="float32",
        ),
    )
