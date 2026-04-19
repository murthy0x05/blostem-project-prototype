"""
STT Service - Database Setup

Async SQLite database using SQLAlchemy with aiosqlite.
Provides session management and table creation utilities.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Create the async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    connect_args={"check_same_thread": False},  # Required for SQLite
)

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions.
    
    Usage:
        async with get_db_session() as session:
            result = await session.execute(query)
    
    Automatically commits on success, rolls back on error.
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_database() -> None:
    """
    Initialize the database: create the directory and all tables.
    
    Called once during application startup.
    """
    from app.db.models import Base  # Import here to avoid circular imports

    # Ensure the data directory exists
    db_path = settings.database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("database_init", path=str(db_path))

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("database_ready", tables=list(Base.metadata.tables.keys()))


async def close_database() -> None:
    """Dispose the engine connection pool on shutdown."""
    await engine.dispose()
    logger.info("database_closed")
