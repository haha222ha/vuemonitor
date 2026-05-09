import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.database import Base


@pytest.fixture(scope="session")
def mock_lifespan():
    with patch("app.main.lifespan") as mock_ls:
        import contextlib

        @contextlib.asynccontextmanager
        async def fake_lifespan(app):
            yield

        mock_ls.side_effect = fake_lifespan
        yield mock_ls


@pytest.fixture
def mock_db():
    db = AsyncMock(spec=AsyncSession)
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.flush = AsyncMock()
    db.close = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def override_get_db(mock_db):
    async def _get_db():
        yield mock_db

    from app.core.database import get_db
    from app.main import app

    app.dependency_overrides[get_db] = _get_db
    yield mock_db
    app.dependency_overrides.clear()
