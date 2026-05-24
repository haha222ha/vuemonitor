import contextlib
import os
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.user import User


@pytest.fixture(scope="session")
def mock_lifespan():
    with patch("app.main.lifespan") as mock_ls:
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

    app.dependency_overrides[get_db] = _get_db
    yield mock_db
    app.dependency_overrides.clear()


def _make_mock_user(user_id=None, plan="pro", role="user", is_active=True):
    user = MagicMock(spec=User)
    user.id = uuid.UUID(user_id) if user_id else uuid.uuid4()
    user.plan = plan
    user.role = role
    user.is_active = is_active
    user.email = "test@example.com"
    user.nickname = "TestUser"
    user.password_hash = "$2b$12$fakehash"
    user.created_at = None
    return user


def _make_mock_db(user=None):
    db = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.flush = AsyncMock()
    db.close = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()

    mock_user = user or _make_mock_user()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
    mock_result.scalar = MagicMock(return_value=0)
    mock_scalars = MagicMock()
    mock_scalars.all = MagicMock(return_value=[])
    mock_result.scalars = MagicMock(return_value=mock_scalars)
    db.execute = AsyncMock(return_value=mock_result)
    return db


@pytest.fixture
def mock_user():
    return _make_mock_user()


@pytest.fixture
def mock_admin_user():
    return _make_mock_user(role="admin")


@pytest.fixture
def auth_token(mock_user):
    return create_access_token(
        subject=str(mock_user.id),
        extra={"plan": mock_user.plan, "role": mock_user.role},
    )


@pytest.fixture
def admin_token(mock_admin_user):
    return create_access_token(
        subject=str(mock_admin_user.id),
        extra={"plan": mock_admin_user.plan, "role": mock_admin_user.role},
    )


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def mock_db_with_user(mock_user):
    return _make_mock_db(mock_user)


@pytest.fixture
def override_db_with_user(mock_db_with_user):
    async def _get_db():
        yield mock_db_with_user

    app.dependency_overrides[get_db] = _get_db
    yield mock_db_with_user
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.ping = AsyncMock(return_value=True)
    redis.pipeline = MagicMock()
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def override_redis(mock_redis):
    with patch("app.core.redis.redis_client", mock_redis):
        with patch("app.core.redis.is_redis_available", return_value=True):
            yield mock_redis
