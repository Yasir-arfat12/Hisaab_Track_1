import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app import database
from app.database import Base, create_engine_and_session, get_db
from app.main import create_app
from app.utils.rate_limit import RateLimitMiddleware


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    RateLimitMiddleware.reset()
    yield
    RateLimitMiddleware.reset()


@pytest.fixture
async def db_session_factory():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_hisaab.db"
        db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
        engine, session_factory = create_engine_and_session(db_url)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield session_factory

        await engine.dispose()


@pytest.fixture
async def db_session(db_session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with db_session_factory() as session:
        yield session


@pytest.fixture
async def test_app(db_session_factory, monkeypatch):
    monkeypatch.setattr(database, "async_session_factory", db_session_factory)
    app = create_app()

    async def override_get_db() -> AsyncGenerator:
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
async def client(test_app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
