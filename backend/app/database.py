from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


def create_engine_and_session(
    database_url: str | None = None,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    url = database_url or settings.DATABASE_URL
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    async_engine = create_async_engine(
        url,
        echo=False,
        connect_args=connect_args,
    )
    session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return async_engine, session_factory


engine, async_session_factory = create_engine_and_session()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for FastAPI dependencies."""
    async with async_session_factory() as session:
        yield session


async def init_db() -> None:
    """Create tables directly in dev/test if migrations are not used."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
