"""
STT Service - Whisper Transcription Engine

Wraps faster-whisper for CPU-based transcription with:
  - Lazy model loading (singleton)
  - Word-level timestamps
  - Language auto-detection
  - Confidence scores
"""

import time
from dataclasses import dataclass, field
from typing import List, Optional

from app.config import get_settings
from app.core.exceptions import TranscriptionError
from app.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class WordTimestamp:
    """A single word with its timing and confidence."""
    word: str
    start: float
    end: float
    confidence: float


@dataclass
class Segment:
    """A transcription segment (sentence/phrase) with word-level detail."""
    id: int
    start: float
    end: float
    text: str
    confidence: float
    words: List[WordTimestamp] = field(default_factory=list)


@dataclass
class TranscriptionResult:
    """Complete transcription output from Whisper."""
    full_text: str
    segments: List[Segment]
    language: str
    language_probability: float
    duration: float
    confidence: float  # Average confidence across all segments
    processing_time: float  # How long transcription took (seconds)


class WhisperService:
    """
    Singleton wrapper around faster-whisper.
    
    The model is loaded lazily on first use and reused across requests.
    Uses CTranslate2 backend for optimized CPU inference with int8 quantization.
    """

    _instance: Optional["WhisperService"] = None
    _model = None

    def __new__(cls) -> "WhisperService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_model(self) -> None:
        """
        Load the Whisper model into memory.
        
        Called during app startup. Uses int8 quantization for
        faster CPU inference with minimal accuracy loss.
        """
        if self._model is not None:
            logger.info("whisper_model_already_loaded")
            return

        from faster_whisper import WhisperModel

        logger.info(
            "whisper_model_loading",
            model_size=settings.whisper_model_size,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )

        start = time.time()

        self._model = WhisperModel(
            settings.whisper_model_size,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
            download_root=settings.whisper_download_root,
        )

        elapsed = time.time() - start
        logger.info("whisper_model_loaded", elapsed_seconds=round(elapsed, 2))

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Transcribe an audio file with word-level timestamps.
        
        Args:
            audio_path: Path to the audio file (WAV preferred).
            language: ISO 639-1 language code (e.g., "en", "es").
                     If None, auto-detection is used.
        
        Returns:
            TranscriptionResult with full text, segments, word timestamps,
            and confidence scores.
        
        Raises:
            TranscriptionError: If transcription fails for any reason.
        """
        if self._model is None:
            raise TranscriptionError("Whisper model not loaded. Call load_model() first.")

        logger.info(
            "transcription_started",
            audio_path=audio_path,
            language=language or "auto-detect",
        )

        start_time = time.time()

        try:
            segments_gen, info = self._model.transcribe(
                audio_path,
                language=language,
                beam_size=5,
                word_timestamps=True,
                vad_filter=True,  # Voice Activity Detection for noise handling
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=400,
                ),
            )

            # Collect all segments and words
            segments: List[Segment] = []
            full_text_parts: List[str] = []
            total_confidence = 0.0

            for idx, seg in enumerate(segments_gen):
                words = []
                if seg.words:
                    for w in seg.words:
                        words.append(WordTimestamp(
                            word=w.word.strip(),
                            start=round(w.start, 3),
                            end=round(w.end, 3),
                            confidence=round(w.probability, 4),
                        ))

                segment = Segment(
                    id=idx,
                    start=round(seg.start, 3),
                    end=round(seg.end, 3),
                    text=seg.text.strip(),
                    confidence=round(seg.avg_logprob, 4) if seg.avg_logprob else 0.0,
                    words=words,
                )
                segments.append(segment)
                full_text_parts.append(seg.text.strip())
                total_confidence += abs(seg.avg_logprob) if seg.avg_logprob else 0

            processing_time = time.time() - start_time
            full_text = " ".join(full_text_parts)

            # Convert avg log probability to a 0-1 confidence score
            # avg_logprob is negative; closer to 0 = more confident
            avg_confidence = 0.0
            if segments:
                avg_logprob = total_confidence / len(segments)
                # Map log probability to 0-1 scale (heuristic)
                import math
                avg_confidence = round(math.exp(-avg_logprob), 4)

            result = TranscriptionResult(
                full_text=full_text,
                segments=segments,
                language=info.language,
                language_probability=round(info.language_probability, 4),
                duration=round(info.duration, 3),
                confidence=min(avg_confidence, 1.0),
                processing_time=round(processing_time, 3),
            )

            logger.info(
                "transcription_completed",
                language=result.language,
                duration=result.duration,
                segments_count=len(segments),
                processing_time=result.processing_time,
                confidence=result.confidence,
            )

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                "transcription_failed",
                audio_path=audio_path,
                error=str(e),
                processing_time=round(processing_time, 3),
            )
            raise TranscriptionError(f"Transcription failed: {str(e)}")

    def detect_language(self, audio_path: str) -> dict:
        """
        Detect the language of an audio file without full transcription.
        
        Returns:
            dict with language code and probability.
        """
        if self._model is None:
            raise TranscriptionError("Whisper model not loaded.")

        try:
            _, info = self._model.transcribe(
                audio_path,
                beam_size=1,
                word_timestamps=False,
                # Only process enough audio to detect language
            )
            return {
                "language": info.language,
                "probability": round(info.language_probability, 4),
            }
        except Exception as e:
            raise TranscriptionError(f"Language detection failed: {str(e)}")

    @staticmethod
    def get_supported_languages() -> List[dict]:
        """Return list of languages supported by Whisper."""
        from faster_whisper.tokenizer import _LANGUAGE_CODES
        
        languages = []
        for code in sorted(_LANGUAGE_CODES):
            languages.append({"code": code, "name": code})
        return languages


def get_whisper_service() -> WhisperService:
    """Get the Whisper service singleton."""
    return WhisperService()
