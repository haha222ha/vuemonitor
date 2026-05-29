import asyncio
import hashlib
import logging
from collections import OrderedDict
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import invalidate_user_cache
from app.core.database import get_db
from app.core.exceptions import BadRequestException, ForbiddenException
from app.core.redis import get_redis
from app.middleware.auth import CurrentUser
from app.models.feature_gate import FeatureGateUsage
from app.models.product import Product
from app.services.discovery_db import discovery_db
from app.services.operation_audit import record_operation
from app.services.discovery_quota import (
    DISCOVERY_QUOTA_HINT,
    STORE_ADD_MAX_PER_REQUEST,
    assert_ref_owner,
    bind_ref_to_user,
    consume_discovery_quota,
    get_client_ip,
    get_discovery_quota,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discovery", tags=["discovery"])


class DiscoverySearchRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=100)
    page: int = Field(1, ge=1, le=100)
    page_size: int = Field(20, ge=5, le=50)
    min_price: float | None = None
    max_price: float | None = None
    min_sold: int | None = None
    sort_by: str = Field("relevance", pattern="^(relevance|price_asc|price_desc|sales_desc|sales_asc)$")
    category: str | None = None


class StoreSearchRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=100)
    page: int = Field(1, ge=1, le=50)
    page_size: int = Field(20, ge=5, le=50)


class AddToMonitorRequest(BaseModel):
    ref_id: str = Field(..., min_length=1, max_length=128)
    product_name: str | None = None
    mode: str = Field("goods", pattern="^(goods|store)$")


TITLE_MAX_LEN: dict[str, int] = {
    "free": 15,
    "pro": 40,
    "premium": -1,
    "enterprise": -1,
}

STORE_NAME_MAX_LEN: dict[str, int] = {
    "free": 8,
    "pro": 20,
    "premium": -1,
    "enterprise": -1,
}

_REF_CACHE_MAX_SIZE = 10000
_REF_CACHE_TTL_SECONDS = 7 * 24 * 3600


class _LRURefCache:
    def __init__(self, maxsize: int = _REF_CACHE_MAX_SIZE):
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._maxsize = maxsize

    def get(self, key: str) -> str | None:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def set(self, key: str, value: str) -> None:
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self._maxsize:
                self._cache.popitem(last=False)
            self._cache[key] = value


_ref_cache = _LRURefCache()

_PLATFORM_PRODUCT_ID_MAX = 255
_PRODUCT_NAME_MAX = 500


def _normalize_goods_id(raw: object) -> str:
    goods_id = str(raw or "").strip().replace("\x00", "")
    if not goods_id:
        raise ForbiddenException(code=42022, message="无效的商品引用")
    if len(goods_id) > _PLATFORM_PRODUCT_ID_MAX:
        goods_id = goods_id[:_PLATFORM_PRODUCT_ID_MAX]
    return goods_id


def _normalize_product_name(product_name: str | None, goods_id: str) -> str:
    name = (product_name or "").strip().replace("\x00", "") or f"XHS商品 {goods_id[:8]}"
    return name[:_PRODUCT_NAME_MAX]


def _encode_ref(raw_id: str) -> str:
    raw_id = str(raw_id)
    short = hashlib.sha256(raw_id.encode()).hexdigest()[:16]
    _ref_cache.set(short, raw_id)
    return short


async def _decode_ref(ref_id: str) -> str | None:
    cached = _ref_cache.get(ref_id)
    if cached:
        return cached
    try:
        redis = await get_redis()
        raw = await redis.get(f"discovery:ref:{ref_id}")
        if raw:
            _ref_cache.set(ref_id, raw)
            return raw
    except Exception as e:
        logger.warning(f"Redis lookup for ref failed: {e}")
    return None


async def _persist_ref(short: str, raw_id: str) -> None:
    try:
        redis = await get_redis()
        await redis.set(f"discovery:ref:{short}", raw_id, ex=_REF_CACHE_TTL_SECONDS)
    except Exception as e:
        logger.warning(f"Redis persist for ref failed: {e}")


async def _mask_goods_item(item: dict, plan: str, user_id: str) -> dict:
    title_raw = item.get("title", "")
    store_name_raw = item.get("store_name", "")

    title_max = TITLE_MAX_LEN.get(plan, 15)
    store_max = STORE_NAME_MAX_LEN.get(plan, 8)

    ref = _encode_ref(item["goods_id"])
    await _persist_ref(ref, item["goods_id"])
    await bind_ref_to_user(ref, user_id)

    masked: dict[str, Any] = {
        "ref": ref,
        "title": title_raw[:title_max] + ("..." if title_max > 0 and len(title_raw) > title_max else "") if title_max > 0 else "***",
        "store_name": store_name_raw[:store_max] + ("..." if store_max > 0 and len(store_name_raw) > store_max else "") if store_max > 0 else "***",
        "keyword": item.get("keyword", ""),
    }

    if plan == "free":
        masked["deal_price_masked"] = True
        masked["deal_price"] = None
        masked["sold_num_masked"] = True
        masked["sold_num"] = None
    elif plan == "pro":
        masked["deal_price"] = item.get("deal_price")
        masked["sold_num_masked"] = True
        masked["sold_num"] = None
        if item.get("sold_num") is not None and item["sold_num"] > 0:
            magnitude = 10 ** (len(str(item["sold_num"])) - 1)
            masked["sold_num_approx"] = f"{magnitude}+"
    else:
        masked["deal_price"] = item.get("deal_price")
        masked["sold_num"] = item.get("sold_num")

    return masked


async def _mask_store_item(item: dict, plan: str, user_id: str) -> dict:
    store_name_raw = item.get("store_name", "")
    store_max = STORE_NAME_MAX_LEN.get(plan, 8)

    raw_store_id = f"store:{item['store_id']}"
    ref = _encode_ref(raw_store_id)
    await _persist_ref(ref, raw_store_id)
    await bind_ref_to_user(ref, user_id)

    masked: dict[str, Any] = {
        "ref": ref,
        "store_name": store_name_raw[:store_max] + ("..." if store_max > 0 and len(store_name_raw) > store_max else "") if store_max > 0 else "***",
        "product_count": item.get("product_count", 0),
    }

    if plan in ("pro", "premium", "enterprise"):
        masked["total_sold"] = item.get("total_sold")
        masked["avg_price"] = item.get("avg_price")
    else:
        masked["total_sold_masked"] = True
        masked["avg_price_masked"] = True

    return masked


async def _check_and_record_search(user: CurrentUser, db: AsyncSession, gate_key: str) -> int:
    """爆品/榜单等独立 gate，不走 discovery 云端搜索+添加合计额度。"""
    from shared.constants.feature_gates import PLAN_LIMITS

    plan = user.plan or "free"
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
    daily_limit = limits.get("discoveryBurstPerDay", 0)

    if daily_limit > 0:
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        count_result = await db.execute(
            select(func.count()).where(
                FeatureGateUsage.user_id == user.id,
                FeatureGateUsage.gate_key == gate_key,
                FeatureGateUsage.used_at >= today_start,
            )
        )
        used = count_result.scalar() or 0
        if used >= daily_limit:
            raise ForbiddenException(
                code=42021,
                message=f"今日搜索次数已达上限（{used}/{daily_limit}），请升级套餐或明日再试",
            )

    usage = FeatureGateUsage(
        user_id=user.id,
        gate_key=gate_key,
        detail={"action": gate_key},
    )
    db.add(usage)
    await db.flush()

    return daily_limit


@router.get("/quota")
async def get_quota(
    request: Request,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    ip = get_client_ip(request)
    quota = await get_discovery_quota(str(user.id), ip, user.plan)
    stats = await discovery_db.get_stats()
    return {"code": 0, "data": {**quota, "db_stats": stats, "policy_hint": DISCOVERY_QUOTA_HINT}}


@router.post("/search")
async def search_goods(
    req: DiscoverySearchRequest,
    request: Request,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    ip = get_client_ip(request)
    quota = await consume_discovery_quota(str(user.id), ip, user.plan, amount=1, action="search")

    plan = user.plan or "free"

    result = await discovery_db.search_goods(
        keyword=req.keyword,
        page=req.page,
        page_size=req.page_size,
        min_price=req.min_price,
        max_price=req.max_price,
        min_sold=req.min_sold,
        sort_by=req.sort_by,
        category=req.category,
    )

    db_ready = discovery_db.is_ready()
    stats = await discovery_db.get_stats() if db_ready else {"total_goods": 0, "total_stores": 0, "total_keywords": 0}

    items = await asyncio.gather(
        *[_mask_goods_item(item, plan, str(user.id)) for item in result["items"]]
    )

    return {
        "code": 0,
        "data": {
            "items": items,
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
            "db_ready": db_ready,
            "db_stats": stats,
            "quota": quota,
            "quota_hint": DISCOVERY_QUOTA_HINT,
            "hint": None
            if db_ready and stats.get("total_goods", 0) > 0
            else "商品发现库未就绪：请在云主机配置 DISCOVERY_DB_PATH 并部署精简版 xhs_discovery_slim.db",
        },
    }


@router.post("/stores")
async def search_stores(
    req: StoreSearchRequest,
    request: Request,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    ip = get_client_ip(request)
    await consume_discovery_quota(str(user.id), ip, user.plan, amount=1, action="search_stores")

    plan = user.plan or "free"

    result = await discovery_db.search_stores(
        keyword=req.keyword,
        page=req.page,
        page_size=req.page_size,
    )

    items = await asyncio.gather(
        *[_mask_store_item(item, plan, str(user.id)) for item in result["items"]]
    )

    return {
        "code": 0,
        "data": {
            "items": items,
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
        },
    }


@router.get("/stores/{ref}/goods")
async def get_store_goods(
    ref: str,
    request: Request,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=50),
):
    ip = get_client_ip(request)
    await consume_discovery_quota(str(user.id), ip, user.plan, amount=1, action="store_goods")

    plan = user.plan or "free"

    store_key = await _decode_ref(ref)
    if not store_key or not store_key.startswith("store:"):
        raise ForbiddenException(code=42022, message="无效的店铺引用")
    store_id = store_key[6:]

    result = await discovery_db.get_store_goods(
        store_id=store_id,
        page=page,
        page_size=page_size,
    )

    items = await asyncio.gather(
        *[_mask_goods_item(item, plan, str(user.id)) for item in result["items"]]
    )

    return {"code": 0, "data": {"items": items, "total": result["total"]}}


@router.get("/keywords")
async def get_hot_keywords(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=100),
):
    result = await discovery_db.get_hot_keywords(page=page, page_size=page_size)
    return {"code": 0, "data": result}


@router.get("/hot-goods")
async def get_hot_goods(
    request: Request,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=50),
    category: str | None = Query(None, max_length=50),
):
    plan = user.plan or "free"

    if plan == "free":
        raise ForbiddenException(
            code=42023,
            message="热门商品榜为Pro及以上会员专属功能，升级即可查看",
        )

    ip = get_client_ip(request)
    await consume_discovery_quota(str(user.id), ip, user.plan, amount=1, action="hot_goods")

    result = await discovery_db.get_hot_goods(
        page=page,
        page_size=page_size,
        category=category,
    )

    items = await asyncio.gather(
        *[_mask_goods_item(item, plan, str(user.id)) for item in result["items"]]
    )

    return {"code": 0, "data": {"items": items, "total": result["total"], "page": result["page"], "page_size": result["page_size"]}}


@router.get("/top-sold")
async def get_top_sold(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=50),
    min_sold: int = Query(1000, ge=0),
):
    plan = user.plan or "free"

    if plan not in ("premium", "enterprise"):
        raise ForbiddenException(
            code=42024,
            message="爆品洞察仅Premium及以上可用，升级即可解锁高销量商品排行",
        )

    await _check_and_record_search(user, db, "gate:discovery:burst")

    result = await discovery_db.get_top_sold(
        page=page,
        page_size=page_size,
        min_sold=min_sold,
    )

    items = await asyncio.gather(
        *[_mask_goods_item(item, plan, str(user.id)) for item in result["items"]]
    )

    return {"code": 0, "data": {"items": items, "total": result["total"], "page": result["page"], "page_size": result["page_size"]}}


@router.get("/stats")
async def get_stats(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    stats = await discovery_db.get_stats()
    return {"code": 0, "data": stats}


@router.post("/add-to-monitor")
async def add_to_monitor(
    req: AddToMonitorRequest,
    request: Request,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from app.middleware.feature_gate import FeatureGateMiddleware

    gate = FeatureGateMiddleware(db)
    await gate.check_gate(user, "gate:monitor:add")

    ip = get_client_ip(request)
    await assert_ref_owner(req.ref_id, str(user.id))

    if req.mode == "store":
        store_key = await _decode_ref(req.ref_id)
        if not store_key or not store_key.startswith("store:"):
            raise ForbiddenException(code=42022, message="无效的店铺引用")
        store_id = store_key[6:]

        store_result = await discovery_db.get_store_goods(
            store_id=store_id, page=1, page_size=STORE_ADD_MAX_PER_REQUEST
        )
        pending: list[dict] = []
        for item in store_result["items"]:
            existing = await db.execute(
                select(Product).where(
                    Product.user_id == user.id,
                    Product.platform == "xhs",
                    Product.platform_product_id == item["goods_id"],
                )
            )
            if existing.scalar_one_or_none():
                continue
            pending.append(item)
            if len(pending) >= STORE_ADD_MAX_PER_REQUEST:
                break

        if pending:
            await consume_discovery_quota(
                str(user.id),
                ip,
                user.plan,
                amount=len(pending),
                action="add_to_monitor_store",
            )

        added = []
        for item in pending:
            goods_id = _normalize_goods_id(item["goods_id"])
            product = Product(
                user_id=user.id,
                platform="xhs",
                platform_product_id=goods_id,
                product_name=_normalize_product_name(item.get("title"), goods_id),
            )
            db.add(product)
            added.append(goods_id)
        try:
            await db.flush()
        except IntegrityError as e:
            logger.warning("add_to_monitor store flush failed: %s", e)
            raise BadRequestException(message="添加失败，部分商品可能已存在或商品ID无效") from e
        await gate.record_usage(user.id, "gate:monitor:add")
        await invalidate_user_cache(str(user.id))
        quota = await get_discovery_quota(str(user.id), ip, user.plan)
        return {
            "code": 0,
            "data": {
                "added_count": len(added),
                "mode": "store",
                "quota": quota,
                "quota_hint": DISCOVERY_QUOTA_HINT,
            },
        }

    raw_goods_id = await _decode_ref(req.ref_id)
    if not raw_goods_id:
        raise ForbiddenException(code=42022, message="无效的商品引用，请重新搜索后再添加")
    goods_id = _normalize_goods_id(raw_goods_id)

    existing = await db.execute(
        select(Product).where(
            Product.user_id == user.id,
            Product.platform == "xhs",
            Product.platform_product_id == goods_id,
        )
    )
    if existing.scalar_one_or_none():
        return {"code": 1, "message": "该商品已在监控列表中"}

    await consume_discovery_quota(
        str(user.id), ip, user.plan, amount=1, action="add_to_monitor"
    )

    product_name = _normalize_product_name(req.product_name, goods_id)
    product = Product(
        user_id=user.id,
        platform="xhs",
        platform_product_id=goods_id,
        product_name=product_name,
    )
    db.add(product)
    try:
        await db.flush()
    except IntegrityError as e:
        logger.warning("add_to_monitor goods flush failed: %s", e)
        raise BadRequestException(message="添加失败，商品可能已存在或商品ID过长/无效") from e

    await gate.record_usage(user.id, "gate:monitor:add")
    await record_operation(
        user_id=str(user.id),
        action="create",
        resource_type="product",
        resource_id=str(product.id),
        detail=f"discovery_ref={req.ref_id}, platform_product_id={goods_id[:32]}",
    )
    await invalidate_user_cache(str(user.id))

    quota = await get_discovery_quota(str(user.id), ip, user.plan)
    return {
        "code": 0,
        "data": {
            "product_id": str(product.id),
            "mode": "goods",
            "quota": quota,
            "quota_hint": DISCOVERY_QUOTA_HINT,
        },
    }


@router.get("/rising-goods")
async def get_rising_goods(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=50),
    category: str | None = Query(None, max_length=50),
):
    plan = user.plan or "free"

    if plan == "free":
        raise ForbiddenException(
            code=42023,
            message="飙升榜为Pro及以上会员专属功能，升级即可查看",
        )

    await _check_and_record_search(user, db, "gate:discovery:burst")

    result = await discovery_db.get_rising_goods(
        page=page,
        page_size=page_size,
        category=category,
    )

    items = await asyncio.gather(
        *[_mask_goods_item(item, plan, str(user.id)) for item in result["items"]]
    )

    return {"code": 0, "data": {"items": items, "total": result["total"], "page": result["page"], "page_size": result["page_size"]}}


@router.get("/new-goods")
async def get_new_goods(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=50),
    category: str | None = Query(None, max_length=50),
):
    plan = user.plan or "free"

    if plan == "free":
        raise ForbiddenException(
            code=42023,
            message="新品榜为Pro及以上会员专属功能，升级即可查看",
        )

    await _check_and_record_search(user, db, "gate:discovery:burst")

    result = await discovery_db.get_new_goods(
        page=page,
        page_size=page_size,
        category=category,
    )

    items = await asyncio.gather(
        *[_mask_goods_item(item, plan, str(user.id)) for item in result["items"]]
    )

    return {"code": 0, "data": {"items": items, "total": result["total"], "page": result["page"], "page_size": result["page_size"]}}
