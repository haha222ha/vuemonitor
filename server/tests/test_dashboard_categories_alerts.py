import os
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.middleware.auth import get_current_user
from app.models.user import User


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
    user.plan_expires_at = None
    user.membership_tier = plan
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


def _setup_overrides(user=None):
    mock_user = user or _make_mock_user()
    mock_db = _make_mock_db(mock_user)

    async def _get_db():
        yield mock_db

    async def _get_current_user():
        return mock_user

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_current_user] = _get_current_user
    return mock_db, mock_user


def _setup_overrides_with_gate(user=None):
    mock_db, mock_user = _setup_overrides(user)
    _patcher = patch(
        "app.middleware.feature_gate.FeatureGateMiddleware.check_gate",
        new_callable=AsyncMock,
        return_value=None,
    )
    _patcher.start()
    return mock_db, mock_user


def _clear_gate_patch():
    patch.stopall()


def _clear_overrides():
    app.dependency_overrides.clear()


def _auth_header(user_id, plan="pro", role="user"):
    token = create_access_token(subject=user_id, extra={"plan": plan, "role": role})
    return {"Authorization": f"Bearer {token}"}


class TestDashboardAPI:
    @pytest.mark.asyncio
    async def test_stats_requires_auth(self):
        _clear_overrides()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/dashboard/stats")
            assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_stats_returns_data(self):
        user_id = str(uuid.uuid4())
        mock_db, mock_user = _setup_overrides()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/dashboard/stats", headers=_auth_header(user_id))
                assert resp.status_code == 200
                data = resp.json()
                assert "code" in data
        finally:
            _clear_overrides()

    @pytest.mark.asyncio
    async def test_trend_requires_auth(self):
        _clear_overrides()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/dashboard/trend")
            assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_activities_requires_auth(self):
        _clear_overrides()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/dashboard/activities")
            assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_home_requires_auth(self):
        _clear_overrides()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/dashboard/home")
            assert resp.status_code in (401, 403)


class TestCategoriesAPI:
    @pytest.mark.asyncio
    async def test_list_requires_auth(self):
        _clear_overrides()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/categories")
            assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_list_returns_data(self):
        user_id = str(uuid.uuid4())
        mock_db, mock_user = _setup_overrides_with_gate()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/categories", headers=_auth_header(user_id))
                assert resp.status_code == 200
                data = resp.json()
                assert "code" in data
        finally:
            _clear_gate_patch()
            _clear_overrides()

    @pytest.mark.asyncio
    async def test_create_requires_name(self):
        user_id = str(uuid.uuid4())
        mock_db, mock_user = _setup_overrides_with_gate()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/categories", json={}, headers=_auth_header(user_id))
                assert resp.status_code == 422
        finally:
            _clear_gate_patch()
            _clear_overrides()

    @pytest.mark.asyncio
    async def test_create_validates_name_length(self):
        user_id = str(uuid.uuid4())
        mock_db, mock_user = _setup_overrides_with_gate()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/categories",
                    json={"name": "a" * 101},
                    headers=_auth_header(user_id),
                )
                assert resp.status_code == 422
        finally:
            _clear_gate_patch()
            _clear_overrides()

    @pytest.mark.asyncio
    async def test_create_with_valid_data(self):
        user_id = str(uuid.uuid4())
        mock_db, mock_user = _setup_overrides_with_gate()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/categories",
                    json={"name": "测试分类", "color": "#FF5500", "sort_order": 1},
                    headers=_auth_header(user_id),
                )
                assert resp.status_code in (200, 201)
        finally:
            _clear_gate_patch()
            _clear_overrides()

    @pytest.mark.asyncio
    async def test_update_requires_auth(self):
        _clear_overrides()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put("/api/v1/categories/123", json={"name": "new"})
            assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_delete_requires_auth(self):
        _clear_overrides()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete("/api/v1/categories/123")
            assert resp.status_code in (401, 403)


class TestAlertRulesAPI:
    @pytest.mark.asyncio
    async def test_list_requires_auth(self):
        _clear_overrides()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/alert-rules")
            assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_list_returns_data(self):
        user_id = str(uuid.uuid4())
        mock_db, mock_user = _setup_overrides()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/alert-rules", headers=_auth_header(user_id))
                assert resp.status_code == 200
                data = resp.json()
                assert "code" in data
        finally:
            _clear_overrides()

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self):
        user_id = str(uuid.uuid4())
        mock_db, mock_user = _setup_overrides()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/alert-rules/metrics", headers=_auth_header(user_id))
                assert resp.status_code == 200
        finally:
            _clear_overrides()

    @pytest.mark.asyncio
    async def test_operators_endpoint(self):
        user_id = str(uuid.uuid4())
        mock_db, mock_user = _setup_overrides()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/alert-rules/operators", headers=_auth_header(user_id))
                assert resp.status_code == 200
        finally:
            _clear_overrides()

    @pytest.mark.asyncio
    async def test_create_requires_fields(self):
        user_id = str(uuid.uuid4())
        mock_db, mock_user = _setup_overrides()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/alert-rules", json={}, headers=_auth_header(user_id))
                assert resp.status_code == 422
        finally:
            _clear_overrides()

    @pytest.mark.asyncio
    async def test_events_requires_auth(self):
        _clear_overrides()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/alert-rules/events/all")
            assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_stats_summary_requires_auth(self):
        _clear_overrides()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/alert-rules/stats/summary")
            assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_auto_detect_requires_auth(self):
        _clear_overrides()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/alert-rules/auto-detect", json={})
            assert resp.status_code in (401, 403)
