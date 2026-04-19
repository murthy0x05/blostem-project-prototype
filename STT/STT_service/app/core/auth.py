"""
STT Service - API Key Authentication

Handles API key generation, hashing, and validation.
Keys are stored as SHA-256 hashes in the database for security.
"""

import hashlib
import secrets
from typing import Optional

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

from app.core.logging_config import get_logger
from app.db.database import get_db_session
from app.db.models import APIKey

from sqlalchemy import select

logger = get_logger(__name__)

# Header-based API key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def generate_api_key() -> str:
    """
    Generate a cryptographically secure API key.
    
    Format: stt_<48 random hex characters>
    Example: stt_a1b2c3d4e5f6...
    """
    return f"stt_{secrets.token_hex(24)}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using SHA-256.
    
    We never store raw API keys — only their hashes.
    This ensures that even if the database is compromised,
    the actual keys remain secure.
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


async def validate_api_key(
    api_key: Optional[str] = Security(api_key_header),
) -> APIKey:
    """
    FastAPI dependency that validates the API key from the X-API-Key header.
    
    Returns the APIKey database record if valid.
    Raises 401 if missing or invalid.
    """
    if not api_key:
        logger.warning("api_key_missing", detail="No API key provided in request header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide it via X-API-Key header.",
        )

    key_hash = hash_api_key(api_key)

    async with get_db_session() as session:
        result = await session.execute(
            select(APIKey).where(
                APIKey.key_hash == key_hash,
                APIKey.is_active == True,
            )
        )
        db_key = result.scalar_one_or_none()

    if not db_key:
        logger.warning("api_key_invalid", key_prefix=api_key[:8] + "...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or deactivated API key.",
        )

    logger.info("api_key_validated", key_name=db_key.name, key_id=db_key.id)
    return db_key
