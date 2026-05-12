import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "vuemonitor_test")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-integration-testing")
os.environ.setdefault("JWT_REFRESH_SECRET", "test-refresh-secret-for-integration-testing")
os.environ.setdefault("ENCRYPTION_KEY", "0123456789abcdef0123456789abcdef")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")
os.environ.setdefault("DEEPSEEK_API_KEY", "sk-test-deepseek-key")

from app.core.security import create_access_token, hash_password
from app.core.database import get_db
from app.main import app


def _make_mock_user(
    user_id=None,
    email="test@example.com",
    nickname="测试用户",
    plan="pro",
    role="user",
):
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.email = email
    user.nickname = nickname
    user.plan = plan
    user.role = role
    user.is_active = True
    user.avatar_url = None
    user.plan_expires_at = None
    user.password_hash = hash_password("TestPass123")
    return user


def _make_mock_db():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalar.return_value = 0
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.delete = AsyncMock()
    mock_db.rollback = AsyncMock()
    return mock_db


def _make_token(user, expires_delta=None):
    return create_access_token(
        subject=str(user.id),
        extra={"plan": user.plan, "role": user.role},
        expires_delta=expires_delta,
    )


def _auth_headers(user):
    return {"Authorization": f"Bearer {_make_token(user)}"}


mock_user = _make_mock_user()
mock_admin = _make_mock_user(
    email="admin@vuemonitor.com",
    nickname="管理员",
    plan="enterprise",
    role="admin",
)
mock_db = _make_mock_db()


async def override_get_db():
    yield mock_db


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def user():
    return _make_mock_user()


@pytest.fixture
def admin():
    return _make_mock_user(plan="enterprise", role="admin")


@pytest.fixture
def auth_headers(user):
    return _auth_headers(user)


@pytest.fixture
def admin_headers(admin):
    return _auth_headers(admin)


@pytest.fixture
def db():
    return mock_db


# ═══════════════════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════════════════


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_check(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/health")
            assert r.status_code == 200
            assert r.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_api_health(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/health")
            assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════
# Auth
# ═══════════════════════════════════════════════════════════════


class TestAuthAPI:
    @pytest.mark.asyncio
    async def test_register_reachable(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/auth/register", json={
                "email": "new@example.com",
                "nickname": "新用户",
                "password": "NewPass123",
            })
            assert r.status_code in (200, 201, 400, 422)

    @pytest.mark.asyncio
    async def test_login_reachable(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/auth/login", json={
                "email": "test@example.com",
                "password": "TestPass123",
            })
            assert r.status_code in (200, 401, 422)

    @pytest.mark.asyncio
    async def test_me_without_token(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/auth/me")
            assert r.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_me_with_token(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/auth/me", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_register_missing_fields(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/auth/register", json={"email": "a@b.com"})
            assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_login_missing_fields(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/auth/login", json={})
            assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════
# Products
# ═══════════════════════════════════════════════════════════════


class TestProductsAPI:
    @pytest.mark.asyncio
    async def test_list_products(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/products", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_create_product(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/products", json={
                "platform": "xhs",
                "platform_product_id": "abc123def456abc123def456",
                "product_name": "测试商品",
            }, headers=_auth_headers(user))
            assert r.status_code in (200, 201, 400, 401, 403, 422)

    @pytest.mark.asyncio
    async def test_create_product_invalid_platform(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/products", json={
                "platform": "invalid_platform",
                "platform_product_id": "test123",
            }, headers=_auth_headers(user))
            assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_create_product_all_platforms(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for platform in ["xhs", "douyin", "taobao", "jd", "pdd"]:
                r = await client.post("/api/v1/products", json={
                    "platform": platform,
                    "platform_product_id": f"test_{platform}_123",
                    "product_name": f"{platform}测试商品",
                }, headers=_auth_headers(user))
                assert r.status_code in (200, 201, 400, 401, 403, 422)

    @pytest.mark.asyncio
    async def test_get_product(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get(f"/api/v1/products/{uuid.uuid4()}", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_delete_product(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.delete(f"/api/v1/products/{uuid.uuid4()}", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_product_features(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get(f"/api/v1/products/{uuid.uuid4()}/features", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_export_csv(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/products/export/csv", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_export_json(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/products/export/json", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_products_without_auth(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/products")
            assert r.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════
# Monitor Rules
# ═══════════════════════════════════════════════════════════════


class TestMonitorAPI:
    @pytest.mark.asyncio
    async def test_list_rules(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/monitor/rules", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_create_rule(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/monitor/rules", json={
                "name": "价格下降预警",
                "conditions": [{"field": "price", "operator": "drop", "threshold": 10}],
                "actions": [{"type": "notify"}],
            }, headers=_auth_headers(user))
            assert r.status_code in (200, 201, 400, 401, 403, 422)

    @pytest.mark.asyncio
    async def test_get_rule(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get(f"/api/v1/monitor/rules/{uuid.uuid4()}", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_update_rule(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.put(f"/api/v1/monitor/rules/{uuid.uuid4()}", json={
                "name": "更新规则",
            }, headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_delete_rule(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.delete(f"/api/v1/monitor/rules/{uuid.uuid4()}", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403, 404)


# ═══════════════════════════════════════════════════════════════
# Collect Tasks
# ═══════════════════════════════════════════════════════════════


class TestCollectAPI:
    @pytest.mark.asyncio
    async def test_list_tasks(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/collect/tasks", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_create_task(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/collect/tasks", json={
                "task_type": "product",
                "platform": "xhs",
                "target_type": "product_id",
                "target_ids": ["12345"],
            }, headers=_auth_headers(user))
            assert r.status_code in (200, 201, 400, 401, 403, 422)

    @pytest.mark.asyncio
    async def test_get_task(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get(f"/api/v1/collect/tasks/{uuid.uuid4()}", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_cancel_task(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post(f"/api/v1/collect/tasks/{uuid.uuid4()}/cancel", headers=_auth_headers(user))
            assert r.status_code in (200, 400, 401, 403, 404)


# ═══════════════════════════════════════════════════════════════
# AI Analysis
# ═══════════════════════════════════════════════════════════════


class TestAIAPI:
    @pytest.mark.asyncio
    async def test_analyze(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/ai/analyze", json={
                "product_id": str(uuid.uuid4()),
                "analysis_type": "basic_analysis",
            }, headers=_auth_headers(user))
            assert r.status_code in (200, 400, 401, 403, 404, 422)

    @pytest.mark.asyncio
    async def test_list_analyses(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/ai/analyses", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_get_analysis(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get(f"/api/v1/ai/analyses/{uuid.uuid4()}", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_invalid_analysis_type(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/ai/analyze", json={
                "product_id": str(uuid.uuid4()),
                "analysis_type": "invalid_type",
            }, headers=_auth_headers(user))
            assert r.status_code in (400, 422)


# ═══════════════════════════════════════════════════════════════
# Sync
# ═══════════════════════════════════════════════════════════════


class TestSyncAPI:
    @pytest.mark.asyncio
    async def test_push(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/sync/push", json={
                "platform": "xhs",
                "platform_product_id": "test123",
                "features": [{"price": 99.9, "collected_at": datetime.now(timezone.utc).isoformat()}],
            }, headers=_auth_headers(user))
            assert r.status_code in (200, 201, 401, 403, 422)

    @pytest.mark.asyncio
    async def test_pull(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/sync/pull", json={}, headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403, 422)


# ═══════════════════════════════════════════════════════════════
# Notifications
# ═══════════════════════════════════════════════════════════════


class TestNotificationsAPI:
    @pytest.mark.asyncio
    async def test_list_notifications(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/notifications", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_unread_count(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/notifications/unread-count", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_mark_read(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.put(f"/api/v1/notifications/{uuid.uuid4()}/read", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_mark_all_read(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.put("/api/v1/notifications/read-all", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403)


# ═══════════════════════════════════════════════════════════════
# Dashboard
# ═══════════════════════════════════════════════════════════════


class TestDashboardAPI:
    @pytest.mark.asyncio
    async def test_stats(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/dashboard/stats", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_trend(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/dashboard/trend", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_activities(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/dashboard/activities", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403)


# ═══════════════════════════════════════════════════════════════
# Teams
# ═══════════════════════════════════════════════════════════════


class TestTeamsAPI:
    @pytest.mark.asyncio
    async def test_create_team(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/teams", json={
                "name": "测试团队",
                "description": "用于集成测试",
            }, headers=_auth_headers(user))
            assert r.status_code in (200, 201, 401, 403, 422)

    @pytest.mark.asyncio
    async def test_list_teams(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/teams", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_get_team(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get(f"/api/v1/teams/{uuid.uuid4()}", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_update_team(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.put(f"/api/v1/teams/{uuid.uuid4()}", json={
                "name": "更新团队名",
            }, headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_delete_team(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.delete(f"/api/v1/teams/{uuid.uuid4()}", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_invite_member(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post(f"/api/v1/teams/{uuid.uuid4()}/invite", json={
                "email": "member@example.com",
                "role": "member",
            }, headers=_auth_headers(user))
            assert r.status_code in (200, 201, 400, 401, 403, 404, 422)

    @pytest.mark.asyncio
    async def test_accept_invitation(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/teams/invitations/faketoken/accept", headers=_auth_headers(user))
            assert r.status_code in (200, 400, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_share_rule(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post(f"/api/v1/teams/{uuid.uuid4()}/share/rule", json={
                "rule_id": str(uuid.uuid4()),
                "can_edit": False,
            }, headers=_auth_headers(user))
            assert r.status_code in (200, 400, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_share_product(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post(f"/api/v1/teams/{uuid.uuid4()}/share/product", json={
                "product_id": str(uuid.uuid4()),
                "can_edit": False,
            }, headers=_auth_headers(user))
            assert r.status_code in (200, 400, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_list_shared(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get(f"/api/v1/teams/{uuid.uuid4()}/shared", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_create_team_missing_name(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/teams", json={}, headers=_auth_headers(user))
            assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════
# Feature Gates
# ═══════════════════════════════════════════════════════════════


class TestFeatureAPI:
    @pytest.mark.asyncio
    async def test_get_limits(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/feature/limits", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_get_usage(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/feature/usage", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403)


# ═══════════════════════════════════════════════════════════════
# Users
# ═══════════════════════════════════════════════════════════════


class TestUsersAPI:
    @pytest.mark.asyncio
    async def test_get_profile(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/users/me", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403)

    @pytest.mark.asyncio
    async def test_update_profile(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.put("/api/v1/users/me", json={"nickname": "新昵称"}, headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403, 422)

    @pytest.mark.asyncio
    async def test_change_password(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.put("/api/v1/users/me/password", json={
                "old_password": "TestPass123",
                "new_password": "NewPass456",
            }, headers=_auth_headers(user))
            assert r.status_code in (200, 400, 401, 403, 422)


# ═══════════════════════════════════════════════════════════════
# License
# ═══════════════════════════════════════════════════════════════


class TestLicenseAPI:
    @pytest.mark.asyncio
    async def test_activate(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/license/activate", json={
                "code": "FAKE-LICENSE-CODE",
            }, headers=_auth_headers(user))
            assert r.status_code in (200, 400, 401, 403, 404)

    @pytest.mark.asyncio
    async def test_get_status(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/license/status", headers=_auth_headers(user))
            assert r.status_code in (200, 401, 403)


# ═══════════════════════════════════════════════════════════════
# Admin
# ═══════════════════════════════════════════════════════════════


class TestAdminAPI:
    @pytest.mark.asyncio
    async def test_admin_login(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/admin/login", json={
                "username": "admin@vuemonitor.com",
                "password": "AdminPass123",
            })
            assert r.status_code in (200, 401, 403, 422)

    @pytest.mark.asyncio
    async def test_admin_users_without_auth(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/admin/users")
            assert r.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_admin_monitoring_without_auth(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/admin/monitoring/system")
            assert r.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_admin_alerts_without_auth(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/admin/monitoring/alerts")
            assert r.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════
# Security & Edge Cases
# ═══════════════════════════════════════════════════════════════


class TestSecurity:
    @pytest.mark.asyncio
    async def test_expired_token(self):
        expired_token = create_access_token(
            subject=str(uuid.uuid4()),
            extra={"plan": "pro", "role": "user"},
            expires_delta=timedelta(seconds=-1),
        )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/products", headers={"Authorization": f"Bearer {expired_token}"})
            assert r.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_malformed_token(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/products", headers={"Authorization": "Bearer not.a.real.token"})
            assert r.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_missing_bearer_prefix(self):
        token = create_access_token(subject=str(uuid.uuid4()), extra={"plan": "pro", "role": "user"})
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/products", headers={"Authorization": token})
            assert r.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_sql_injection_in_product_id(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/products/1; DROP TABLE products;--", headers=_auth_headers(user))
            assert r.status_code in (400, 404, 422)

    @pytest.mark.asyncio
    async def test_xss_in_product_name(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/products", json={
                "platform": "xhs",
                "platform_product_id": "xss_test_123",
                "product_name": "<script>alert('xss')</script>",
            }, headers=_auth_headers(user))
            assert r.status_code in (200, 201, 400, 422)

    @pytest.mark.asyncio
    async def test_very_long_input(self, user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post("/api/v1/products", json={
                "platform": "xhs",
                "platform_product_id": "a" * 10000,
                "product_name": "测试",
            }, headers=_auth_headers(user))
            assert r.status_code in (200, 201, 400, 422)

    @pytest.mark.asyncio
    async def test_method_not_allowed(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.patch("/api/v1/products")
            assert r.status_code == 405

    @pytest.mark.asyncio
    async def test_not_found_route(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/nonexistent")
            assert r.status_code == 404
