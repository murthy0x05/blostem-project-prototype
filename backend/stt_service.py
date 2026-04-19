"""
Speech-to-Text service using faster-whisper or Hugging Face Whisper.
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
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_MODEL_CANDIDATES = (
    PROJECT_ROOT / "stt_model",
    PROJECT_ROOT / "models" / "stt_model",
)
DEFAULT_ADAPTER_BASE_MODEL = os.getenv(
    "WHISPER_BASE_MODEL",
    "openai/whisper-large-v3-turbo",
).strip()

SUPPORTED_MODEL_NAMES = ()

CUSTOM_MODEL_ALIAS = "telugu-whisper"
CUSTOM_MODEL_PATH_ENV = "WHISPER_MODEL_PATH"
_models: dict[str, object] = {}


def _detect_runtime() -> tuple[str, str]:
    has_cuda = shutil.which("nvidia-smi") is not None
    device = "cuda" if has_cuda else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    return device, compute_type


def get_default_model_name() -> str:
    return _get_default_model_name()


def get_configured_model_path() -> Optional[str]:
    configured_path = os.getenv(CUSTOM_MODEL_PATH_ENV, "").strip()
    if not configured_path:
        return None
    return str(Path(configured_path).expanduser().resolve())


def get_project_model_path() -> Optional[str]:
    for candidate in LOCAL_MODEL_CANDIDATES:
        if not candidate.exists() or not candidate.is_dir():
            continue
        resolved_candidate = _find_local_model_root(candidate)
        if resolved_candidate is not None:
            return str(resolved_candidate)
    return None


def _get_default_model_name() -> str:
    project_model_path = get_project_model_path()
    if project_model_path:
        return project_model_path

    configured_custom_path = get_configured_model_path()
    if configured_custom_path:
        return CUSTOM_MODEL_ALIAS

    return "stt_model"


def get_supported_models() -> list[str]:
    project_model_path = get_project_model_path()
    if project_model_path:
        return [CUSTOM_MODEL_ALIAS]
    return []


def _ensure_local_model_path(model_path: str) -> Path:
    path = Path(model_path).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"Local model path does not exist: {path}")
    if not path.is_dir():
        raise ValueError(f"Local model path must be a directory: {path}")
    return path


def _find_local_model_root(model_path: Path) -> Optional[Path]:
    path = _ensure_local_model_path(str(model_path))

    if (path / "model.bin").exists():
        return path

    if (path / "config.json").exists():
        return path

    if (path / "adapter_config.json").exists() and (path / "adapter_model.safetensors").exists():
        return path

    for nested_path in sorted(path.rglob("*")):
        if not nested_path.is_dir():
            continue
        if (nested_path / "model.bin").exists():
            return nested_path.resolve()
        if (nested_path / "config.json").exists():
            return nested_path.resolve()
        if (nested_path / "adapter_config.json").exists() and (
            nested_path / "adapter_model.safetensors"
        ).exists():
            return nested_path.resolve()

    return None


def _resolve_custom_model_path() -> str:
    configured_custom_path = get_configured_model_path()
    if not configured_custom_path:
        raise ValueError(
            f"'{CUSTOM_MODEL_ALIAS}' requested but {CUSTOM_MODEL_PATH_ENV} is not set."
        )
    return str(_ensure_local_model_path(configured_custom_path))


def resolve_model_name(model_name: Optional[str]) -> str:
    requested_model = (model_name or _get_default_model_name()).strip()
    if requested_model in SUPPORTED_MODEL_NAMES:
        return requested_model

    if requested_model == CUSTOM_MODEL_ALIAS:
        return _resolve_custom_model_path()

    if requested_model == "stt_model":
        project_model_path = get_project_model_path()
        if project_model_path:
            return project_model_path
        raise ValueError(
            "Requested local model 'stt_model', but no project model folder was found. "
            "Place your model at '/Users/tharuntej/Desktop/STT_service/stt_model' "
            "or '/Users/tharuntej/Desktop/STT_service/models/stt_model', "
            "or set WHISPER_MODEL_PATH."
        )

    candidate_path = Path(requested_model).expanduser()
    if candidate_path.exists():
        resolved_candidate = _find_local_model_root(candidate_path)
        if resolved_candidate is not None:
            return str(resolved_candidate)
        return str(_ensure_local_model_path(str(candidate_path)))

    supported = ", ".join(get_supported_models())
    raise ValueError(
        f"Unsupported model '{requested_model}'. Supported models: {supported}, "
        f"or provide a valid local model directory path."
    )


def _get_model_cache_key(model_ref: str) -> str:
    if model_ref in SUPPORTED_MODEL_NAMES:
        return model_ref
    return f"path:{model_ref}"


def _get_model_display_name(model_ref: str) -> str:
    configured_custom_path = get_configured_model_path()
    if configured_custom_path and model_ref == configured_custom_path:
        return f"{CUSTOM_MODEL_ALIAS} ({configured_custom_path})"
    return model_ref


def _detect_model_format(model_ref: str) -> str:
    if model_ref in SUPPORTED_MODEL_NAMES:
        return "faster-whisper"

    model_path = _ensure_local_model_path(model_ref)

    if (model_path / "model.bin").exists():
        return "faster-whisper"

    if (model_path / "config.json").exists():
        return "hf-whisper"

    if (model_path / "adapter_config.json").exists() and (
        model_path / "adapter_model.safetensors"
    ).exists():
        return "hf-whisper-adapter"

    raise ValueError(
        f"Could not identify model format in {model_path}. Expected a faster-whisper "
        "directory with model.bin, a Hugging Face Whisper directory with config.json, "
        "or a PEFT adapter directory with adapter_config.json."
    )


def validate_startup_configuration() -> None:
    configured_custom_path = get_configured_model_path()
    default_model_name = _get_default_model_name()

    if configured_custom_path:
        _ensure_local_model_path(configured_custom_path)
        _detect_model_format(configured_custom_path)

    if default_model_name == CUSTOM_MODEL_ALIAS and not configured_custom_path:
        supported = ", ".join(SUPPORTED_MODEL_NAMES)
        raise ValueError(
            f"Default model is '{CUSTOM_MODEL_ALIAS}' but {CUSTOM_MODEL_PATH_ENV} is not set. "
            f"Use one of: {supported}, or set {CUSTOM_MODEL_PATH_ENV} to your local model directory."
        )

    if default_model_name == "stt_model" and not get_project_model_path():
        raise ValueError(
            "Default model is 'stt_model', but no local project model folder was found. "
            "Place your model at '/Users/tharuntej/Desktop/STT_service/stt_model' "
            "or '/Users/tharuntej/Desktop/STT_service/models/stt_model', "
            "or set WHISPER_MODEL_PATH to your model folder."
        )

    if (
        default_model_name not in SUPPORTED_MODEL_NAMES
        and default_model_name != CUSTOM_MODEL_ALIAS
        and default_model_name != "stt_model"
        and not Path(default_model_name).expanduser().exists()
    ):
        supported = ", ".join(SUPPORTED_MODEL_NAMES)
        raise ValueError(
            f"Unsupported default model '{default_model_name}'. Supported models: {supported}, "
            f"or use '{CUSTOM_MODEL_ALIAS}' with {CUSTOM_MODEL_PATH_ENV}."
        )


def _load_faster_whisper_model(model_ref: str):
    from faster_whisper import WhisperModel

    device, compute_type = _detect_runtime()
    logger.info(
        "Loading faster-whisper model '%s' on %s (%s)",
        _get_model_display_name(model_ref),
        device,
        compute_type,
    )
    return WhisperModel(model_ref, device=device, compute_type=compute_type)


def _load_hf_whisper_model(model_ref: str):
    import torch
    from transformers import pipeline

    device, _ = _detect_runtime()
    torch_dtype = torch.float16 if device == "cuda" else torch.float32
    device_index = 0 if device == "cuda" else -1

    logger.info(
        "Loading Hugging Face Whisper model '%s' on %s",
        _get_model_display_name(model_ref),
        device,
    )
    return pipeline(
        task="automatic-speech-recognition",
        model=model_ref,
        tokenizer=model_ref,
        feature_extractor=model_ref,
        dtype=torch_dtype,
        device=device_index,
    )


def _infer_adapter_base_model(model_ref: str) -> str:
    readme_path = Path(model_ref) / "README.md"
    if readme_path.exists():
        for line in readme_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("base_model:"):
                value = line.split(":", 1)[1].strip()
                if value:
                    return value
    return DEFAULT_ADAPTER_BASE_MODEL


def _load_hf_whisper_adapter_model(model_ref: str):
    import torch
    from peft import PeftModel
    from transformers import (
        AutoModelForSpeechSeq2Seq,
        AutoProcessor,
        pipeline,
    )

    device, _ = _detect_runtime()
    torch_dtype = torch.float16 if device == "cuda" else torch.float32
    device_index = 0 if device == "cuda" else -1
    base_model_name = _infer_adapter_base_model(model_ref)

    logger.info(
        "Loading Whisper adapter '%s' with base model '%s' on %s",
        _get_model_display_name(model_ref),
        base_model_name,
        device,
    )

    base_model = AutoModelForSpeechSeq2Seq.from_pretrained(
        base_model_name,
        dtype=torch_dtype,
        low_cpu_mem_usage=True,
        use_safetensors=True,
    )
    adapted_model = PeftModel.from_pretrained(base_model, model_ref)
    processor = AutoProcessor.from_pretrained(base_model_name)

    return pipeline(
        task="automatic-speech-recognition",
        model=adapted_model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        dtype=torch_dtype,
        device=device_index,
    )


def _get_model(model_name: Optional[str] = None):
    """
    Lazily load a speech model once, then reuse it.
    """
    requested_model = resolve_model_name(model_name)
    cache_key = _get_model_cache_key(requested_model)
    model_format = _detect_model_format(requested_model)

    if cache_key not in _models:
        if model_format == "hf-whisper":
            _models[cache_key] = _load_hf_whisper_model(requested_model)
        elif model_format == "hf-whisper-adapter":
            _models[cache_key] = _load_hf_whisper_adapter_model(requested_model)
        else:
            _models[cache_key] = _load_faster_whisper_model(requested_model)
        logger.info(
            "Model '%s' loaded successfully.",
            _get_model_display_name(requested_model),
        )

    return _models[cache_key]


def _transcribe_with_faster_whisper(
    model,
    wav_path: str,
    language_hint: Optional[str],
) -> tuple[str, str, list[SegmentInfo], list[WordInfo]]:
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

    return " ".join(full_text_parts), info.language, all_segments, all_words


def _transcribe_with_hf_whisper(
    model,
    wav_path: str,
    language_hint: Optional[str],
) -> tuple[str, str, list[SegmentInfo], list[WordInfo]]:
    generate_kwargs = {"task": "transcribe"}
    if language_hint:
        generate_kwargs["language"] = language_hint

    result = model(
        wav_path,
        return_timestamps=True,
        generate_kwargs=generate_kwargs,
    )

    raw_text = str(result.get("text", "")).strip()
    raw_chunks = result.get("chunks") or []

    segments: list[SegmentInfo] = []
    words: list[WordInfo] = []

    for chunk in raw_chunks:
        text = str(chunk.get("text", "")).strip()
        timestamp = chunk.get("timestamp") or ()
        if not isinstance(timestamp, (tuple, list)) or len(timestamp) != 2:
            continue
        start, end = timestamp
        if start is None or end is None:
            continue
        segments.append(SegmentInfo(start=float(start), end=float(end), text=text))

    detected_language = language_hint or "unknown"
    return raw_text, detected_language, segments, words


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
    selected_model = resolve_model_name(model_name)
    model_format = _detect_model_format(selected_model)
    wav_path = normalise_audio(audio_bytes, filename)

    try:
        model = _get_model(selected_model)
        if model_format == "hf-whisper":
            full_text, detected_language, all_segments, all_words = (
                _transcribe_with_hf_whisper(
                    model,
                    wav_path,
                    language_hint,
                )
            )
        else:
            full_text, detected_language, all_segments, all_words = (
                _transcribe_with_faster_whisper(
                    model,
                    wav_path,
                    language_hint,
                )
            )
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
            model_name=_get_model_display_name(selected_model),
            device=device,
            compute_type=compute_type,
        ),
    )
