"""Database session management."""
from typing import AsyncGenerator, Annotated, Generator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from fastapi import Depends

from src.app.core.config import settings

# Create PostgreSQL engines
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
    future=True
)

# Create sync engine for Alembic and other sync operations
sync_engine = create_engine(
    settings.DATABASE_URL.replace('postgresql+asyncpg', 'postgresql'),
    pool_pre_ping=True,
    echo=False,
    future=True
)

# Create session factories
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

SessionLocal = sessionmaker(
    sync_engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_db() -> Generator[Session, None, None]:
    """Get synchronous database session for Alembic and other sync operations."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


SessionDep = Annotated[AsyncSession, Depends(get_db)]
SyncSessionDep = Annotated[Session, Depends(get_sync_db)] 