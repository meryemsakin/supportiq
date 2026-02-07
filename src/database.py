"""
Database configuration and session management.

This module provides:
- SQLAlchemy engine and session factory
- Async database support
- Dependency injection for FastAPI
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from src.config import settings

# -----------------------------------------------------------------------------
# Database URL handling
# -----------------------------------------------------------------------------

def get_async_database_url(url: str) -> str:
    """Convert standard PostgreSQL URL to async version."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def get_sync_database_url(url: str) -> str:
    """Ensure URL uses sync driver."""
    if "asyncpg" in url:
        return url.replace("postgresql+asyncpg://", "postgresql://")
    return url


# -----------------------------------------------------------------------------
# Sync Engine and Session (for Alembic and sync operations)
# -----------------------------------------------------------------------------

sync_engine = create_engine(
    get_sync_database_url(settings.database_url),
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
    echo=settings.debug,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# -----------------------------------------------------------------------------
# Async Engine and Session (for FastAPI)
# -----------------------------------------------------------------------------

async_engine = create_async_engine(
    get_async_database_url(settings.database_url),
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
    echo=settings.debug,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# -----------------------------------------------------------------------------
# Base Model
# -----------------------------------------------------------------------------

Base = declarative_base()

# -----------------------------------------------------------------------------
# Dependency Injection
# -----------------------------------------------------------------------------

def get_sync_db() -> Generator[Session, None, None]:
    """
    Get synchronous database session.
    
    Usage:
        @app.get("/")
        def endpoint(db: Session = Depends(get_sync_db)):
            ...
    
    Yields:
        Session: SQLAlchemy session
    """
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get asynchronous database session.
    
    Usage:
        @app.get("/")
        async def endpoint(db: AsyncSession = Depends(get_async_db)):
            ...
    
    Yields:
        AsyncSession: SQLAlchemy async session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database session (for use outside FastAPI).
    
    Usage:
        async with get_db_context() as db:
            result = await db.execute(query)
    
    Yields:
        AsyncSession: SQLAlchemy async session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# -----------------------------------------------------------------------------
# Database Utilities
# -----------------------------------------------------------------------------

async def init_db() -> None:
    """
    Initialize database by creating all tables.
    
    Note: In production, use Alembic migrations instead.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await async_engine.dispose()


async def check_db_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        bool: True if connection is successful
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
            return True
    except Exception:
        return False
