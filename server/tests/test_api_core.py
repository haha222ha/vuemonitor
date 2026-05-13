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


def _auth_header(user_id, plan="pro", role="user"):
    token = create_access_token(subject=user_id, extra={"plan": plan, "role": role})
    return {"Authorization": f"Bearer {token}"}


class TestProductURLParsing:
    def test_parse_xhs_url(self):
        from app.api.products import parse_product_url
        platform, pid = parse_product_url("https://www.xiaohongshu.com/explore/6501a2b3c4d5e6f7890abcde")
        assert platform == "xhs"
        assert pid == "6501a2b3c4d5e6f7890abcde"

    def test_parse_xhs_discovery_url(self):
        from app.api.products import parse_product_url
        platform, pid = parse_product_url("https://www.xiaohongshu.com/discovery/item/6501a2b3c4d5e6f7890abcde")
        assert platform == "xhs"
        assert pid == "6501a2b3c4d5e6f7890abcde"

    def test_parse_douyin_url(self):
        from app.api.products import parse_product_url
        platform, pid = parse_product_url("https://www.douyin.com/video/7123456789012345678")
        assert platform == "douyin"
        assert pid == "7123456789012345678"

    def test_parse_taobao_url(self):
        from app.api.products import parse_product_url
        platform, pid = parse_product_url("https://item.taobao.com/item.htm?id=12345678901")
        assert platform == "taobao"
        assert pid == "12345678901"

    def test_parse_jd_url(self):
        from app.api.products import parse_product_url
        platform, pid = parse_product_url("https://item.jd.com/100012345678")
        assert platform == "jd"
        assert pid == "100012345678"

    def test_parse_pdd_url(self):
        from app.api.products import parse_product_url
        platform, pid = parse_product_url("https://yangkeduo.com/goods.html?goods_id=123456")
        assert platform == "pdd"
        assert pid == "123456"

    def test_parse_unknown_url(self):
        from app.api.products import parse_product_url
        platform, pid = parse_product_url("https://www.example.com/something")
        assert platform is None
        assert pid is None

    def test_parse_xhslink_url(self):
        from app.api.products import parse_product_url
        platform, pid = parse_product_url("https://xhslink.com/abc123")
        assert platform == "xhs"

    def test_parse_tmall_url(self):
        from app.api.products import parse_product_url
        platform, pid = parse_product_url("https://detail.tmall.com/item.htm?id=98765432100")
        assert platform == "taobao"
        assert pid == "98765432100"


class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_health(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/health")
                assert resp.status_code == 200
                assert resp.json()["status"] == "ok"
        finally:
            _clear_db_override()

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/metrics")
                assert resp.status_code == 200
        finally:
            _clear_db_override()


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_register_validation(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/auth/register", json={
                    "email": "bad-email",
                    "nickname": "test",
                    "password": "Short1",
                })
                assert resp.status_code == 422
        finally:
            _clear_db_override()

    @pytest.mark.asyncio
    async def test_login_validation(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/auth/login", json={
                    "email": "",
                    "password": "",
                })
                assert resp.status_code == 422
        finally:
            _clear_db_override()

    @pytest.mark.asyncio
    async def test_me_unauthorized(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/auth/me")
                assert resp.status_code in (401, 403)
        finally:
            _clear_db_override()


class TestProductEndpoints:
    @pytest.mark.asyncio
    async def test_create_product_requires_auth(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/products", json={
                    "platform": "xhs",
                    "platform_product_id": "123",
                    "product_name": "Test",
                })
                assert resp.status_code in (401, 403)
        finally:
            _clear_db_override()

    @pytest.mark.asyncio
    async def test_list_products_requires_auth(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/products")
                assert resp.status_code in (401, 403)
        finally:
            _clear_db_override()


class TestCollectEndpoints:
    @pytest.mark.asyncio
    async def test_create_task_requires_auth(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/collect/tasks", json={
                    "task_type": "product",
                    "platform": "xhs",
                    "target_type": "product_id",
                    "target_ids": ["123"],
                })
                assert resp.status_code in (401, 403)
        finally:
            _clear_db_override()

    @pytest.mark.asyncio
    async def test_list_tasks_requires_auth(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/collect/tasks")
                assert resp.status_code in (401, 403)
        finally:
            _clear_db_override()


class TestMonitorEndpoints:
    @pytest.mark.asyncio
    async def test_create_rule_requires_auth(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/monitor/rules", json={
                    "product_id": str(uuid.uuid4()),
                    "rule_name": "Test",
                    "rule_type": "price_drop",
                    "conditions": {"threshold": 10},
                })
                assert resp.status_code in (401, 403)
        finally:
            _clear_db_override()

    @pytest.mark.asyncio
    async def test_list_rules_requires_auth(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/monitor/rules")
                assert resp.status_code in (401, 403)
        finally:
            _clear_db_override()


class TestDashboardEndpoints:
    @pytest.mark.asyncio
    async def test_dashboard_requires_auth(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/dashboard/stats")
                assert resp.status_code in (401, 403)
        finally:
            _clear_db_override()


class TestLicenseEndpoints:
    @pytest.mark.asyncio
    async def test_verify_requires_fields(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/license/verify", json={})
                assert resp.status_code == 422
        finally:
            _clear_db_override()

    @pytest.mark.asyncio
    async def test_activate_requires_auth(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/license/activate", json={
                    "license_key": "VM-TEST-KEY",
                })
                assert resp.status_code in (401, 403)
        finally:
            _clear_db_override()


class TestAdminEndpoints:
    @pytest.mark.asyncio
    async def test_admin_stats_requires_admin(self):
        user_id = str(uuid.uuid4())
        mock_user = _make_mock_user(user_id, plan="free", role="user")
        _override_db(mock_user)
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/admin/stats", headers=_auth_header(user_id, role="user"))
                assert resp.status_code == 403
        finally:
            _clear_db_override()

    @pytest.mark.asyncio
    async def test_admin_login_validation(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/admin/login", json={})
                assert resp.status_code == 422
        finally:
            _clear_db_override()


class TestAIEndpoints:
    @pytest.mark.asyncio
    async def test_analyze_requires_auth(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/ai/analyze", json={
                    "product_id": str(uuid.uuid4()),
                    "analysis_type": "sentiment",
                })
                assert resp.status_code in (401, 403)
        finally:
            _clear_db_override()

    @pytest.mark.asyncio
    async def test_ai_status_public(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/ai/status")
                assert resp.status_code == 200
                data = resp.json()
                assert "code" in data
                assert "data" in data
        finally:
            _clear_db_override()


class TestNotificationEndpoints:
    @pytest.mark.asyncio
    async def test_notifications_requires_auth(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/notifications")
                assert resp.status_code in (401, 403)
        finally:
            _clear_db_override()


class TestGDPREndpoints:
    @pytest.mark.asyncio
    async def test_gdpr_requires_auth(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/gdpr/data")
                assert resp.status_code in (401, 403, 404)
        finally:
            _clear_db_override()


class TestCORSHeaders:
    @pytest.mark.asyncio
    async def test_cors_headers_present(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.options("/api/v1/health", headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "GET",
                })
                assert "access-control-allow-origin" in resp.headers
        finally:
            _clear_db_override()

    @pytest.mark.asyncio
    async def test_cors_disallows_unknown_origin(self):
        _override_db()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.options("/api/v1/health", headers={
                    "Origin": "http://evil-site.com",
                    "Access-Control-Request-Method": "GET",
                })
                assert "access-control-allow-origin" not in resp.headers or \
                       resp.headers.get("access-control-allow-origin") != "http://evil-site.com"
        finally:
            _clear_db_override()
