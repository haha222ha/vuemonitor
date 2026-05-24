import os
import sys
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app
from app.middleware.auth import get_current_user
from app.models.user import User

SAMPLE_GOODS = [
    {
        "goods_id": "goods_001",
        "title": "测试商品A标题很长需要截断",
        "store_name": "测试店铺名称很长",
        "keyword": "美妆",
        "deal_price": 99.9,
        "sold_num": 1500,
    },
    {
        "goods_id": "goods_002",
        "title": "测试商品B",
        "store_name": "店铺B",
        "keyword": "护肤",
        "deal_price": 199.0,
        "sold_num": 500,
    },
]

SAMPLE_STORES = [
    {
        "store_id": "store_001",
        "store_name": "热门美妆店铺",
        "product_count": 120,
        "total_sold": 50000,
        "avg_price": 89.5,
    },
]

SAMPLE_KEYWORDS = [
    {"keyword": "美妆", "item_count": 1500},
    {"keyword": "护肤", "item_count": 800},
]


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
    return user


def _make_mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.flush = AsyncMock()
    db.close = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_result.scalar = MagicMock(return_value=0)
    mock_scalars = MagicMock()
    mock_scalars.all = MagicMock(return_value=[])
    mock_result.scalars = MagicMock(return_value=mock_scalars)
    db.execute = AsyncMock(return_value=mock_result)
    return db


def _setup_auth(user):
    mock_db = _make_mock_db()

    async def _get_db():
        yield mock_db

    async def _get_current_user_override():
        return user

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_current_user] = _get_current_user_override
    return mock_db


def _teardown():
    app.dependency_overrides.clear()


@asynccontextmanager
async def _test_client(user=None):
    mock_db = _setup_auth(user or _make_mock_user())
    with patch("app.middleware.security_audit.SecurityAuditMiddleware._persist_audit", new_callable=AsyncMock):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, mock_db
    _teardown()


class TestDiscoveryQuota:
    @pytest.mark.asyncio
    async def test_get_quota_pro_user(self):
        user = _make_mock_user(plan="pro")
        with patch("app.api.discovery.discovery_db") as mock_discovery:
            mock_discovery.get_stats = AsyncMock(return_value={
                "total_goods": 100000,
                "total_stores": 5000,
                "total_keywords": 200,
            })
            async with _test_client(user) as (client, _):
                response = await client.get("/api/v1/discovery/quota")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "daily_limit" in data["data"]
        assert data["data"]["db_stats"]["total_goods"] == 100000


class TestDiscoverySearch:
    @pytest.mark.asyncio
    async def test_search_goods_pro_user(self):
        user = _make_mock_user(plan="pro")
        with patch("app.api.discovery.discovery_db") as mock_discovery, \
             patch("app.api.discovery.get_redis", new_callable=AsyncMock) as mock_redis_fn:
            mock_discovery.search_goods = AsyncMock(return_value={
                "items": SAMPLE_GOODS,
                "total": 2,
                "page": 1,
                "page_size": 20,
            })
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=None)
            mock_redis.set = AsyncMock(return_value=None)
            mock_redis_fn.return_value = mock_redis

            async with _test_client(user) as (client, _):
                response = await client.post(
                    "/api/v1/discovery/search",
                    json={"keyword": "美妆", "page": 1, "page_size": 20},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) == 2
        item = data["data"]["items"][0]
        assert item["deal_price"] == 99.9
        assert item["sold_num"] is None
        assert item.get("sold_num_approx") is not None

    @pytest.mark.asyncio
    async def test_search_goods_free_user_masked(self):
        user = _make_mock_user(plan="free")
        with patch("app.api.discovery.discovery_db") as mock_discovery, \
             patch("app.api.discovery.get_redis", new_callable=AsyncMock) as mock_redis_fn:
            mock_discovery.search_goods = AsyncMock(return_value={
                "items": SAMPLE_GOODS,
                "total": 2,
                "page": 1,
                "page_size": 20,
            })
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=None)
            mock_redis.set = AsyncMock(return_value=None)
            mock_redis_fn.return_value = mock_redis

            async with _test_client(user) as (client, _):
                response = await client.post(
                    "/api/v1/discovery/search",
                    json={"keyword": "美妆", "page": 1, "page_size": 20},
                )

        assert response.status_code == 200
        item = response.json()["data"]["items"][0]
        assert item["deal_price"] is None
        assert item.get("deal_price_masked") is True
        assert item["sold_num"] is None
        assert item.get("sold_num_masked") is True

    @pytest.mark.asyncio
    async def test_search_goods_premium_user_full_data(self):
        user = _make_mock_user(plan="premium")
        with patch("app.api.discovery.discovery_db") as mock_discovery, \
             patch("app.api.discovery.get_redis", new_callable=AsyncMock) as mock_redis_fn:
            mock_discovery.search_goods = AsyncMock(return_value={
                "items": SAMPLE_GOODS,
                "total": 2,
                "page": 1,
                "page_size": 20,
            })
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=None)
            mock_redis.set = AsyncMock(return_value=None)
            mock_redis_fn.return_value = mock_redis

            async with _test_client(user) as (client, _):
                response = await client.post(
                    "/api/v1/discovery/search",
                    json={"keyword": "美妆", "page": 1, "page_size": 20},
                )

        assert response.status_code == 200
        item = response.json()["data"]["items"][0]
        assert item["deal_price"] == 99.9
        assert item["sold_num"] == 1500
        assert item.get("deal_price_masked") is None
        assert item.get("sold_num_masked") is None

    @pytest.mark.asyncio
    async def test_search_goods_validation_empty_keyword(self):
        user = _make_mock_user(plan="pro")
        async with _test_client(user) as (client, _):
            response = await client.post(
                "/api/v1/discovery/search",
                json={"keyword": "", "page": 1, "page_size": 20},
            )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_goods_invalid_sort_by(self):
        user = _make_mock_user(plan="pro")
        async with _test_client(user) as (client, _):
            response = await client.post(
                "/api/v1/discovery/search",
                json={"keyword": "test", "page": 1, "page_size": 20, "sort_by": "invalid"},
            )
        assert response.status_code == 422


class TestDiscoveryStores:
    @pytest.mark.asyncio
    async def test_search_stores_pro_user(self):
        user = _make_mock_user(plan="pro")
        with patch("app.api.discovery.discovery_db") as mock_discovery, \
             patch("app.api.discovery.get_redis", new_callable=AsyncMock) as mock_redis_fn:
            mock_discovery.search_stores = AsyncMock(return_value={
                "items": SAMPLE_STORES,
                "total": 1,
                "page": 1,
                "page_size": 20,
            })
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=None)
            mock_redis.set = AsyncMock(return_value=None)
            mock_redis_fn.return_value = mock_redis

            async with _test_client(user) as (client, _):
                response = await client.post(
                    "/api/v1/discovery/stores",
                    json={"keyword": "美妆", "page": 1, "page_size": 20},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        item = data["data"]["items"][0]
        assert item["total_sold"] == 50000
        assert item["avg_price"] == 89.5

    @pytest.mark.asyncio
    async def test_search_stores_free_user_masked(self):
        user = _make_mock_user(plan="free")
        with patch("app.api.discovery.discovery_db") as mock_discovery, \
             patch("app.api.discovery.get_redis", new_callable=AsyncMock) as mock_redis_fn:
            mock_discovery.search_stores = AsyncMock(return_value={
                "items": SAMPLE_STORES,
                "total": 1,
                "page": 1,
                "page_size": 20,
            })
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=None)
            mock_redis.set = AsyncMock(return_value=None)
            mock_redis_fn.return_value = mock_redis

            async with _test_client(user) as (client, _):
                response = await client.post(
                    "/api/v1/discovery/stores",
                    json={"keyword": "美妆", "page": 1, "page_size": 20},
                )

        assert response.status_code == 200
        item = response.json()["data"]["items"][0]
        assert item.get("total_sold_masked") is True
        assert item.get("avg_price_masked") is True


class TestDiscoveryKeywords:
    @pytest.mark.asyncio
    async def test_get_keywords(self):
        user = _make_mock_user(plan="pro")
        with patch("app.api.discovery.discovery_db") as mock_discovery:
            mock_discovery.get_hot_keywords = AsyncMock(return_value={
                "items": SAMPLE_KEYWORDS,
                "total": 2,
            })
            async with _test_client(user) as (client, _):
                response = await client.get(
                    "/api/v1/discovery/keywords",
                    params={"page": 1, "page_size": 50},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) == 2


class TestDiscoveryUnauthorized:
    @pytest.mark.asyncio
    async def test_search_without_token(self):
        _teardown()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/discovery/search",
                json={"keyword": "test", "page": 1, "page_size": 20},
            )
        assert response.status_code in (401, 403)


class TestDiscoveryHotGoods:
    @pytest.mark.asyncio
    async def test_hot_goods_free_user_forbidden(self):
        user = _make_mock_user(plan="free")
        async with _test_client(user) as (client, _):
            response = await client.get(
                "/api/v1/discovery/hot-goods",
                params={"page": 1, "page_size": 20},
            )
        assert response.status_code == 403
        data = response.json()
        assert data.get("code") == 42023

    @pytest.mark.asyncio
    async def test_hot_goods_pro_user_allowed(self):
        user = _make_mock_user(plan="pro")
        with patch("app.api.discovery.discovery_db") as mock_discovery, \
             patch("app.api.discovery.get_redis", new_callable=AsyncMock) as mock_redis_fn:
            mock_discovery.get_hot_goods = AsyncMock(return_value={
                "items": SAMPLE_GOODS,
                "total": 2,
                "page": 1,
                "page_size": 20,
            })
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=None)
            mock_redis.set = AsyncMock(return_value=None)
            mock_redis_fn.return_value = mock_redis

            async with _test_client(user) as (client, _):
                response = await client.get(
                    "/api/v1/discovery/hot-goods",
                    params={"page": 1, "page_size": 20},
                )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0


class TestDiscoveryTopSold:
    @pytest.mark.asyncio
    async def test_top_sold_pro_user_forbidden(self):
        user = _make_mock_user(plan="pro")
        async with _test_client(user) as (client, _):
            response = await client.get(
                "/api/v1/discovery/top-sold",
                params={"page": 1, "page_size": 20},
            )
        assert response.status_code == 403
        data = response.json()
        assert data.get("code") == 42024

    @pytest.mark.asyncio
    async def test_top_sold_premium_user_allowed(self):
        user = _make_mock_user(plan="premium")
        with patch("app.api.discovery.discovery_db") as mock_discovery, \
             patch("app.api.discovery.get_redis", new_callable=AsyncMock) as mock_redis_fn:
            mock_discovery.get_top_sold = AsyncMock(return_value={
                "items": SAMPLE_GOODS,
                "total": 2,
                "page": 1,
                "page_size": 20,
            })
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=None)
            mock_redis.set = AsyncMock(return_value=None)
            mock_redis_fn.return_value = mock_redis

            async with _test_client(user) as (client, _):
                response = await client.get(
                    "/api/v1/discovery/top-sold",
                    params={"page": 1, "page_size": 20},
                )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0


class TestDiscoveryQuotaExhaustion:
    @pytest.mark.asyncio
    async def test_search_quota_exhausted_free_user(self):
        user = _make_mock_user(plan="free")
        with patch("app.api.discovery.discovery_db") as mock_discovery, \
             patch("app.api.discovery.get_redis", new_callable=AsyncMock) as mock_redis_fn:
            mock_discovery.search_goods = AsyncMock(return_value={
                "items": SAMPLE_GOODS,
                "total": 2,
                "page": 1,
                "page_size": 20,
            })
            mock_redis = AsyncMock()
            mock_redis.get = AsyncMock(return_value=None)
            mock_redis.set = AsyncMock(return_value=None)
            mock_redis_fn.return_value = mock_redis

            async with _test_client(user) as (client, mock_db):
                mock_result = MagicMock()
                mock_result.scalar = MagicMock(return_value=5)
                mock_db.execute = AsyncMock(return_value=mock_result)

                response = await client.post(
                    "/api/v1/discovery/search",
                    json={"keyword": "美妆", "page": 1, "page_size": 20},
                )

        assert response.status_code == 403
        data = response.json()
        assert data.get("code") == 42021
