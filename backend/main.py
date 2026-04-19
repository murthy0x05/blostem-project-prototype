"""
FastAPI application for STT testing.
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.utils import ErrorResponse, TranscriptionResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("stt_backend")

ALLOWED_AUDIO_TYPES = {
    "audio/wav", "audio/x-wav", "audio/wave", "audio/mpeg",
    "audio/mp3", "audio/ogg", "audio/flac", "audio/webm",
    "audio/mp4", "audio/x-m4a", "audio/webm;codecs=opus"
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-load model on startup to avoid latency on first request."""
    logger.info("Starting STT backend...")
    try:
        from backend.stt_service import (
            _get_model,
            get_default_model_name,
            validate_startup_configuration,
        )

        validate_startup_configuration()
        _get_model(get_default_model_name())
    except Exception as exc:
        logger.warning(f"Could not pre-load model: {exc}")
    yield
    logger.info("Shutting down STT backend.")


app = FastAPI(title="STT Backend", lifespan=lifespan)

# Allow requests from any origin (e.g., local HTML file)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(detail=str(exc)).model_dump(),
    )


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}


@app.get("/stt/models", tags=["STT"])
async def list_models():
    from backend.stt_service import get_default_model_name, get_supported_models

    return {
        "default_model": get_default_model_name(),
        "supported_models": get_supported_models(),
    }


@app.post(
    "/stt/transcribe",
    response_model=TranscriptionResponse,
    responses={400: {"model": ErrorResponse}},
    tags=["STT"]
)
async def transcribe_audio_endpoint(
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
    model_name: str | None = Form(default=None),
):
    """
    Accept audio, process asynchronously in thread pool to prevent blocking.
    """
    if file.content_type and file.content_type not in ALLOWED_AUDIO_TYPES:
        # Relax strict checking slightly for 'application/octet-stream' 
        # to allow generic blobs from basic frontend testing.
        if file.content_type != "application/octet-stream":
            raise HTTPException(status_code=400, detail=f"Unsupported type: {file.content_type}")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file.")

    from backend.stt_service import process_audio_sync

    # Run blocking STT model asynchronously
    result = await asyncio.to_thread(
        process_audio_sync,
        audio_bytes,
        file.filename or "upload.wav",
        language,
        model_name,
    )
    return result


class TextInput(BaseModel):
    text: str


@app.post(
    "/stt/text",
    response_model=TranscriptionResponse,
    responses={400: {"model": ErrorResponse}},
    tags=["STT"]
)
async def process_text_endpoint(body: TextInput):
    """
    Process plain text, run asynchronously in thread pool.
    """
    if not body.text or not body.text.strip():
        raise HTTPException(status_code=400, detail="Text must not be empty.")

    from backend.text_service import process_text_sync

    result = await asyncio.to_thread(process_text_sync, body.text)
    return result
