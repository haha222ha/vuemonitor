import sys
import os
import uuid
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.security import create_access_token
from app.core.database import get_db
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


def _override_db(user=None):
    mock_db = _make_mock_db(user)
    async def _get_db():
        yield mock_db
    app.dependency_overrides[get_db] = _get_db
    return mock_db


def _clear_db_override():
    app.dependency_overrides.clear()


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_check(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/health")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "ok"
        finally:
            _clear_db_override()


class TestAuthAPIValidation:
    @pytest.mark.asyncio
    async def test_register_validation_empty_email(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/api/v1/auth/register", json={
                    "email": "not-an-email",
                    "nickname": "test",
                    "password": "ValidPass123",
                })
                assert response.status_code == 422
        finally:
            _clear_db_override()

    @pytest.mark.asyncio
    async def test_register_validation_short_password(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/api/v1/auth/register", json={
                    "email": "test@example.com",
                    "nickname": "test",
                    "password": "short",
                })
                assert response.status_code == 422
        finally:
            _clear_db_override()

    @pytest.mark.asyncio
    async def test_register_validation_weak_password(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/api/v1/auth/register", json={
                    "email": "test@example.com",
                    "nickname": "test",
                    "password": "alllowercase123",
                })
                assert response.status_code == 422
        finally:
            _clear_db_override()

    @pytest.mark.asyncio
    async def test_me_without_token(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/auth/me")
                assert response.status_code in (401, 403)
        finally:
            _clear_db_override()

    @pytest.mark.asyncio
    async def test_me_with_invalid_token(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/auth/me", headers={
                    "Authorization": "Bearer invalid.token.here"
                })
                assert response.status_code in (401, 403)
        finally:
            _clear_db_override()


class TestProductsAPIValidation:
    @pytest.mark.asyncio
    async def test_create_product_validation_bad_platform(self):
        user_id = str(uuid.uuid4())
        mock_user = _make_mock_user(user_id, plan="pro", role="user")
        _override_db(mock_user)
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                token = create_access_token(subject=user_id, extra={"plan": "pro", "role": "user"})
                response = await client.post("/api/v1/products", json={
                    "platform": "invalid_platform",
                    "platform_product_id": "123",
                    "product_name": "Test",
                }, headers={"Authorization": f"Bearer {token}"})
                assert response.status_code == 422
        finally:
            _clear_db_override()

    @pytest.mark.asyncio
    async def test_list_products_requires_auth(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/products")
                assert response.status_code in (401, 403)
        finally:
            _clear_db_override()


class TestCollectAPIValidation:
    @pytest.mark.asyncio
    async def test_create_task_validation_bad_platform(self):
        user_id = str(uuid.uuid4())
        mock_user = _make_mock_user(user_id, plan="pro", role="user")
        _override_db(mock_user)
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                token = create_access_token(subject=user_id, extra={"plan": "pro", "role": "user"})
                response = await client.post("/api/v1/collect/tasks", json={
                    "task_type": "product",
                    "platform": "bad_platform",
                    "target_type": "product_id",
                    "target_ids": ["123"],
                }, headers={"Authorization": f"Bearer {token}"})
                assert response.status_code == 422
        finally:
            _clear_db_override()

    @pytest.mark.asyncio
    async def test_create_task_validation_empty_targets(self):
        user_id = str(uuid.uuid4())
        mock_user = _make_mock_user(user_id, plan="pro", role="user")
        _override_db(mock_user)
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                token = create_access_token(subject=user_id, extra={"plan": "pro", "role": "user"})
                response = await client.post("/api/v1/collect/tasks", json={
                    "task_type": "product",
                    "platform": "xhs",
                    "target_type": "product_id",
                    "target_ids": [],
                }, headers={"Authorization": f"Bearer {token}"})
                assert response.status_code == 422
        finally:
            _clear_db_override()


class TestMonitorAPIValidation:
    @pytest.mark.asyncio
    async def test_create_rule_validation_bad_type(self):
        user_id = str(uuid.uuid4())
        mock_user = _make_mock_user(user_id, plan="pro", role="user")
        _override_db(mock_user)
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                token = create_access_token(subject=user_id, extra={"plan": "pro", "role": "user"})
                response = await client.post("/api/v1/monitor/rules", json={
                    "product_id": str(uuid.uuid4()),
                    "rule_name": "Test Rule",
                    "rule_type": "invalid_type",
                    "conditions": {},
                }, headers={"Authorization": f"Bearer {token}"})
                assert response.status_code == 422
        finally:
            _clear_db_override()


class TestAIAPIValidation:
    @pytest.mark.asyncio
    async def test_analyze_validation_bad_type(self):
        user_id = str(uuid.uuid4())
        mock_user = _make_mock_user(user_id, plan="pro", role="user")
        _override_db(mock_user)
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                token = create_access_token(subject=user_id, extra={"plan": "pro", "role": "user"})
                response = await client.post("/api/v1/ai/analyze", json={
                    "product_id": str(uuid.uuid4()),
                    "analysis_type": "invalid_type",
                }, headers={"Authorization": f"Bearer {token}"})
                assert response.status_code == 422
        finally:
            _clear_db_override()


class TestAdminAPIValidation:
    @pytest.mark.asyncio
    async def test_admin_login_rate_limit(self):
        from app.api.admin import _admin_login_attempts, _ADMIN_MAX_ATTEMPTS
        _admin_login_attempts.clear()

        mock_db = _make_mock_db(user=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_result.scalar = MagicMock(return_value=0)
        mock_db.execute = AsyncMock(return_value=mock_result)

        async def _get_db():
            yield mock_db
        app.dependency_overrides[get_db] = _get_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                for _ in range(_ADMIN_MAX_ATTEMPTS):
                    response = await client.post("/api/v1/admin/login", json={
                        "username": "fake@admin.com",
                        "password": "wrong",
                    })
                    assert response.status_code in (400, 403)

                response = await client.post("/api/v1/admin/login", json={
                    "username": "fake@admin.com",
                    "password": "wrong",
                })
                assert response.status_code == 403
        finally:
            _admin_login_attempts.clear()
            _clear_db_override()

    @pytest.mark.asyncio
    async def test_admin_endpoints_require_admin_role(self):
        user_id = str(uuid.uuid4())
        mock_user = _make_mock_user(user_id, plan="free", role="user")
        _override_db(mock_user)
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                user_token = create_access_token(subject=user_id, extra={"plan": "free", "role": "user"})
                response = await client.get("/api/v1/admin/stats", headers={
                    "Authorization": f"Bearer {user_token}"
                })
                assert response.status_code == 403
        finally:
            _clear_db_override()

    @pytest.mark.asyncio
    async def test_proxy_add_validation_bad_port(self):
        user_id = str(uuid.uuid4())
        mock_user = _make_mock_user(user_id, plan="enterprise", role="admin")
        _override_db(mock_user)
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                admin_token = create_access_token(subject=user_id, extra={"plan": "enterprise", "role": "admin"})
                response = await client.post("/api/v1/admin/proxies", json={
                    "ip": "1.2.3.4",
                    "port": 99999,
                    "protocol": "http",
                }, headers={"Authorization": f"Bearer {admin_token}"})
                assert response.status_code == 422
        finally:
            _clear_db_override()

    @pytest.mark.asyncio
    async def test_user_update_validation_bad_plan(self):
        user_id = str(uuid.uuid4())
        mock_user = _make_mock_user(user_id, plan="enterprise", role="admin")
        _override_db(mock_user)
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                admin_token = create_access_token(subject=user_id, extra={"plan": "enterprise", "role": "admin"})
                response = await client.put(f"/api/v1/admin/users/{uuid.uuid4()}", json={
                    "plan": "invalid_plan",
                }, headers={"Authorization": f"Bearer {admin_token}"})
                assert response.status_code == 422
        finally:
            _clear_db_override()


class TestCORS:
    @pytest.mark.asyncio
    async def test_cors_headers_present(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.options("/api/v1/health", headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "GET",
                })
                assert "access-control-allow-origin" in response.headers
        finally:
            _clear_db_override()

    @pytest.mark.asyncio
    async def test_cors_disallows_unknown_origin(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.options("/api/v1/health", headers={
                    "Origin": "http://evil-site.com",
                    "Access-Control-Request-Method": "GET",
                })
                assert "access-control-allow-origin" not in response.headers or \
                       response.headers.get("access-control-allow-origin") != "http://evil-site.com"
        finally:
            _clear_db_override()
