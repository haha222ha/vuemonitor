import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app


def _make_mock_user(user_id=None, plan="pro", role="user", is_active=True):
    user = MagicMock()
    user.id = uuid.UUID(user_id) if user_id else uuid.uuid4()
    user.plan = plan
    user.role = role
    user.is_active = is_active
    user.email = "test@example.com"
    user.nickname = "TestUser"
    user.password_hash = "$2b$12$fakehash"
    return user


def _make_mock_db_with_user(user=None):
    mock_user = user or _make_mock_user()
    db = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.flush = AsyncMock()
    db.close = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)
    mock_result.scalar = MagicMock(return_value=1)
    mock_scalars = MagicMock()
    mock_scalars.all = MagicMock(return_value=[mock_user])
    mock_scalars.unique = MagicMock(return_value=mock_scalars)
    mock_result.scalars = MagicMock(return_value=mock_scalars)
    db.execute = AsyncMock(return_value=mock_result)
    return db


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_status(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.core.redis.check_redis_health", new_callable=AsyncMock, return_value=True), \
                 patch("app.core.database.async_session_factory") as mock_sf:
                mock_db = AsyncMock()
                mock_db.execute = AsyncMock(return_value=MagicMock())
                mock_db.__aenter__ = AsyncMock(return_value=mock_db)
                mock_db.__aexit__ = AsyncMock(return_value=False)
                mock_sf.return_value = mock_db

                resp = await client.get("/health")
                assert resp.status_code == 200
                data = resp.json()
                assert "status" in data
                assert "checks" in data
                assert "database" in data["checks"]
                assert "redis" in data["checks"]


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_login_rate_limit_on_redis(self):
        mock_pipe = MagicMock()
        mock_pipe.zremrangebyscore = MagicMock(return_value=mock_pipe)
        mock_pipe.zadd = MagicMock(return_value=mock_pipe)
        mock_pipe.zcard = MagicMock(return_value=mock_pipe)
        mock_pipe.expire = MagicMock(return_value=mock_pipe)
        mock_pipe.execute = AsyncMock(return_value=[None, None, 11, True])

        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        mock_redis.delete = AsyncMock(return_value=1)

        mock_db = _make_mock_db_with_user()

        async def _get_db():
            yield mock_db

        app.dependency_overrides[get_db] = _get_db

        try:
            with patch("app.core.cache.is_redis_available", return_value=True), \
                 patch("app.core.cache.redis_client", mock_redis):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    resp = await client.post("/api/v1/auth/login", json={
                        "account": "test@example.com",
                        "password": "TestPass123",
                    })
                    assert resp.status_code == 429
                    assert "频繁" in resp.json().get("message", "")
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_unauthenticated_access_denied(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/auth/me")
            assert resp.status_code in (401, 403)


class TestTokenSecurity:
    def test_access_token_contains_required_claims(self):
        user_id = str(uuid.uuid4())
        token = create_access_token(subject=user_id, extra={"plan": "pro", "role": "user"})
        from app.core.security import decode_access_token
        payload = decode_access_token(token)
        assert payload["sub"] == user_id
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_expired_token_rejected(self):
        from app.core.security import decode_access_token
        from jose import jwt
        from app.config import get_settings
        settings = get_settings()
        expired_payload = {
            "sub": str(uuid.uuid4()),
            "type": "access",
            "exp": 0,
        }
        expired_token = jwt.encode(expired_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        with pytest.raises(Exception):
            decode_access_token(expired_token)
