"""
Speech-to-Text service using faster-whisper.
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from pathlib import Path
from typing import Optional

from backend.utils import (
    ProcessingMetadata,
    SegmentInfo,
    TranscriptionResponse,
    WordInfo,
    normalise_audio,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = os.getenv("WHISPER_MODEL", "large-v3-turbo").strip()
_models: dict[str, object] = {}


def _detect_runtime() -> tuple[str, str]:
    has_cuda = shutil.which("nvidia-smi") is not None
    device = "cuda" if has_cuda else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    return device, compute_type


def get_default_model_name() -> str:
    return DEFAULT_MODEL_NAME


def get_supported_models() -> list[str]:
    return [DEFAULT_MODEL_NAME]


def _get_model(model_name: Optional[str] = None):
    """
    Lazily load a faster-whisper model once, then reuse it.
    """
    requested_model = (model_name or DEFAULT_MODEL_NAME).strip()

    if requested_model not in _models:
        from faster_whisper import WhisperModel

        device, compute_type = _detect_runtime()
        logger.info(
            "Loading faster-whisper model '%s' on %s (%s)",
            requested_model,
            device,
            compute_type,
        )
        _models[requested_model] = WhisperModel(
            requested_model, device=device, compute_type=compute_type
        )
        logger.info("Model '%s' loaded successfully.", requested_model)

    return _models[requested_model]


def process_audio_sync(
    audio_bytes: bytes,
    filename: str,
    language_hint: Optional[str] = None,
    model_name: Optional[str] = None,
) -> TranscriptionResponse:
    """
    Synchronous transcription logic. Must be called in a threadpool.
    """
    t0 = time.perf_counter()
    requested_model = (model_name or DEFAULT_MODEL_NAME).strip()
    wav_path = normalise_audio(audio_bytes, filename)

    try:
        model = _get_model(requested_model)
        segments_iter, info = model.transcribe(
            wav_path,
            beam_size=1,
            language=language_hint,
            vad_filter=True,
            word_timestamps=True,
        )

        all_segments: list[SegmentInfo] = []
        all_words: list[WordInfo] = []
        full_text_parts: list[str] = []

        for seg in segments_iter:
            cleaned_text = seg.text.strip()
            all_segments.append(
                SegmentInfo(start=seg.start, end=seg.end, text=cleaned_text)
            )
            if cleaned_text:
                full_text_parts.append(cleaned_text)

            for word in getattr(seg, "words", []) or []:
                if word.start is None or word.end is None:
                    continue
                all_words.append(
                    WordInfo(
                        word=word.word.strip(),
                        start=word.start,
                        end=word.end,
                    )
                )

        full_text = " ".join(full_text_parts)
        detected_language = info.language
    finally:
        Path(wav_path).unlink(missing_ok=True)

    processing_time = time.perf_counter() - t0
    device, compute_type = _detect_runtime()

    return TranscriptionResponse(
        text=full_text,
        language=detected_language,
        segments=all_segments,
        words=all_words,
        metadata=ProcessingMetadata(
            processing_time=round(processing_time, 4),
            model_name=requested_model,
            device=device,
            compute_type=compute_type,
        ),
    )
