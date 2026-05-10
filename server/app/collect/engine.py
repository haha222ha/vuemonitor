import asyncio
import json
import logging
import random
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import aiohttp
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.collect.parsers import get_parser
from app.collect.rate_controller import AdaptiveRateController
from app.collect.session_manager import SessionManager
from app.models.admin import ProxyPool, RiskEvent
from app.models.collect import CollectTask, CollectTaskItem
from app.models.product import Product, ProductFeature
from app.ws.manager import manager

logger = logging.getLogger(__name__)


class ProxyManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_proxy(self) -> dict | None:
        result = await self.db.execute(
            select(ProxyPool)
            .where(ProxyPool.status == "available", ProxyPool.health_score >= 60)
            .order_by(ProxyPool.health_score.desc(), ProxyPool.last_used_at.asc().nullsfirst())
            .limit(1)
        )
        proxy = result.scalar_one_or_none()
        if not proxy:
            return None

        proxy.last_used_at = datetime.now(timezone.utc)
        return {"ip": proxy.ip, "port": proxy.port, "protocol": proxy.protocol, "id": str(proxy.id)}

    async def mark_proxy_fail(self, proxy_id: str):
        await self.db.execute(
            update(ProxyPool)
            .where(ProxyPool.id == uuid.UUID(proxy_id))
            .values(fail_count=ProxyPool.fail_count + 1, health_score=ProxyPool.health_score - 10)
        )

    async def mark_proxy_banned(self, proxy_id: str):
        await self.db.execute(
            update(ProxyPool)
            .where(ProxyPool.id == uuid.UUID(proxy_id))
            .values(status="banned", health_score=0)
        )


class RiskDetector:
    RISK_PATTERNS = {
        "captcha": {"keywords": ["验证码", "captcha", "verify", "安全验证"], "level": "high"},
        "login_required": {"keywords": ["登录", "login", "sign in"], "level": "high"},
        "rate_limit": {"keywords": ["频繁", "too many", "rate limit", "429", "请求过于频繁"], "level": "medium"},
        "ip_blocked": {"keywords": ["封禁", "blocked", "forbidden", "403"], "level": "critical"},
    }

    RISK_STATUS_CODES = {403, 429, 461}

    @classmethod
    def detect(cls, response_text: str, status_code: int) -> dict | None:
        if status_code in cls.RISK_STATUS_CODES:
            messages = {
                403: "HTTP 403 - 风控拦截",
                429: "HTTP 429 - 频率限制",
                461: "HTTP 461 - 验证码触发",
            }
            return {
                "risk_type": {403: "ip_blocked", 429: "rate_limit", 461: "captcha"}.get(status_code, "unknown"),
                "risk_level": {403: "critical", 429: "medium", 461: "high"}.get(status_code, "medium"),
                "detail": {"status_code": status_code, "message": messages.get(status_code, f"HTTP {status_code}")},
            }

        if status_code >= 500:
            return {
                "risk_type": "server_error",
                "risk_level": "low",
                "detail": {"status_code": status_code, "message": f"HTTP {status_code} - 服务端异常"},
            }

        text_lower = response_text.lower()
        for risk_type, config in cls.RISK_PATTERNS.items():
            for keyword in config["keywords"]:
                if keyword in text_lower:
                    return {
                        "risk_type": risk_type,
                        "risk_level": config["level"],
                        "detail": {"keyword": keyword},
                    }

        try:
            data = json.loads(response_text)
            error_code = data.get("error_code", -1)
            if error_code in (461, 300):
                return {
                    "risk_type": "captcha",
                    "risk_level": "high",
                    "detail": {"api_error_code": error_code, "message": f"API error_code={error_code} - 风控拦截"},
                }
            msg = str(data.get("msg", "")).lower()
            for risk_type, config in cls.RISK_PATTERNS.items():
                for keyword in config["keywords"]:
                    if keyword in msg:
                        return {
                            "risk_type": risk_type,
                            "risk_level": config["level"],
                            "detail": {"keyword": keyword, "api_msg": data.get("msg", "")},
                        }
        except (json.JSONDecodeError, AttributeError):
            pass

        return None

    async def record_risk_event(
        self,
        db: AsyncSession,
        task_id: uuid.UUID | None,
        platform: str,
        risk_type: str,
        risk_level: str,
        detail: dict,
        proxy_id: uuid.UUID | None = None,
    ):
        event = RiskEvent(
            task_id=task_id,
            platform=platform,
            risk_type=risk_type,
            risk_level=risk_level,
            detail=detail,
            proxy_id=proxy_id,
        )
        db.add(event)


class DataPersister:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_parsed_data(self, user_id: uuid.UUID, parsed: dict) -> Product:
        platform = parsed.get("platform", "")
        platform_product_id = parsed.get("platform_product_id", "")

        existing = await self.db.execute(
            select(Product).where(
                Product.user_id == user_id,
                Product.platform == platform,
                Product.platform_product_id == platform_product_id,
            )
        )
        product = existing.scalar_one_or_none()

        if product:
            if parsed.get("product_name"):
                product.product_name = parsed["product_name"]
            if parsed.get("shop_name"):
                product.shop_name = parsed["shop_name"]
            if parsed.get("category"):
                product.category = parsed["category"]
            if parsed.get("image_url"):
                product.image_url = parsed["image_url"]
            if parsed.get("product_url"):
                product.product_url = parsed["product_url"]
            product.last_collected_at = datetime.now(timezone.utc)
        else:
            product = Product(
                user_id=user_id,
                platform=platform,
                platform_product_id=platform_product_id,
                product_name=parsed.get("product_name", "未知商品"),
                shop_name=parsed.get("shop_name"),
                category=parsed.get("category"),
                image_url=parsed.get("image_url"),
                product_url=parsed.get("product_url"),
                is_active=True,
                last_collected_at=datetime.now(timezone.utc),
            )
            self.db.add(product)
            await self.db.flush()

        latest_feature_result = await self.db.execute(
            select(ProductFeature)
            .where(ProductFeature.product_id == product.id)
            .order_by(ProductFeature.collected_at.desc())
            .limit(1)
        )
        latest_feature = latest_feature_result.scalar_one_or_none()

        new_price = Decimal(str(parsed["price"])) if parsed.get("price") is not None else None
        new_sales = parsed.get("sales_count")

        daily_sales = None
        if latest_feature and new_sales is not None and latest_feature.sales_count is not None:
            daily_sales = max(0, new_sales - latest_feature.sales_count)

        feature = ProductFeature(
            product_id=product.id,
            price=new_price,
            sales_count=new_sales,
            monthly_sales=parsed.get("monthly_sales"),
            rating=Decimal(str(parsed["rating"])) if parsed.get("rating") is not None else None,
            review_count=parsed.get("review_count"),
            favorite_count=parsed.get("favorite_count"),
            source="collect",
            collected_at=datetime.now(timezone.utc),
        )
        self.db.add(feature)

        if daily_sales is not None and daily_sales > 0:
            product.trend = daily_sales

        return product


class CollectEngine:
    def __init__(self, db: AsyncSession, max_concurrency: int = 8):
        self.db = db
        self.max_concurrency = max_concurrency
        self.rate_controller = AdaptiveRateController()
        self.session_manager = SessionManager()
        self.proxy_manager = ProxyManager(db)
        self.risk_detector = RiskDetector()
        self.persister = DataPersister(db)
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def execute_task(self, task_id: uuid.UUID) -> dict:
        result = await self.db.execute(select(CollectTask).where(CollectTask.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return {"status": "error", "message": "任务不存在"}

        task.status = "running"
        task.started_at = datetime.now(timezone.utc)
        await self.db.flush()

        items_result = await self.db.execute(
            select(CollectTaskItem).where(CollectTaskItem.task_id == task_id)
        )
        items = items_result.scalars().all()

        if not items:
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)
            task.progress = 100
            await self.db.flush()
            return {"status": "completed", "collected": 0}

        success_count = 0
        fail_count = 0
        risk_count = 0
        product_count = 0
        _lock = asyncio.Lock()
        total = len(items)

        async def process_item(item: CollectTaskItem):
            nonlocal success_count, fail_count, risk_count, product_count
            async with self._semaphore:
                await self.rate_controller.acquire()
                try:
                    fetch_result = await self._fetch_item(task.platform, item.target_id)
                    raw_text = fetch_result.get("raw_text", "")
                    status_code = fetch_result.get("status_code", 200)

                    risk = self.risk_detector.detect(raw_text, status_code)

                    if risk:
                        async with _lock:
                            risk_count += 1
                        self.rate_controller.on_risk_detected()
                        await self.risk_detector.record_risk_event(
                            self.db, task.id, task.platform, risk["risk_type"], risk["risk_level"], risk["detail"]
                        )
                        item.status = "risk_detected"
                        item.error_message = risk["risk_type"]

                        if risk["risk_level"] in ("high", "critical"):
                            await self.session_manager.rotate_fingerprint(task.platform)

                        try:
                            await manager.send_to_user(str(task.user_id), {
                                "type": "collect:risk_alert",
                                "data": {
                                    "task_id": str(task.id),
                                    "platform": task.platform,
                                    "risk_type": risk["risk_type"],
                                    "risk_level": risk["risk_level"],
                                    "detail": risk["detail"],
                                    "target_id": item.target_id,
                                },
                                "ts": datetime.now(timezone.utc).isoformat(),
                            })
                        except Exception:
                            pass
                    else:
                        parser = get_parser(task.platform)
                        parsed = parser.parse(raw_text, status_code, item.target_id)

                        if parsed:
                            self.rate_controller.on_success()
                            item.status = "completed"
                            item.result = parsed
                            item.completed_at = datetime.now(timezone.utc)

                            try:
                                product = await self.persister.save_parsed_data(task.user_id, parsed)
                                async with _lock:
                                    product_count += 1
                            except Exception as e:
                                logger.error(f"Failed to persist data for {item.target_id}: {e}")

                            async with _lock:
                                success_count += 1
                        else:
                            self.rate_controller.on_success()
                            item.status = "completed"
                            item.result = {"raw_captured": True, "target_id": item.target_id}
                            item.completed_at = datetime.now(timezone.utc)
                            async with _lock:
                                success_count += 1

                except Exception as e:
                    self.rate_controller.on_error()
                    item.status = "failed"
                    item.error_message = str(e)[:500]
                    async with _lock:
                        fail_count += 1
                    logger.error(f"Item {item.target_id} failed: {e}")

                async with _lock:
                    done = success_count + fail_count + risk_count
                    task.progress = min(99, int(done / total * 100))

                try:
                    await manager.send_to_user(str(task.user_id), {
                        "type": "collect:progress",
                        "data": {
                            "task_id": str(task.id),
                            "progress": task.progress,
                            "status": task.status,
                            "success": success_count,
                            "failed": fail_count,
                            "risk_detected": risk_count,
                            "done": done,
                            "total": total,
                        },
                        "ts": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception:
                    pass

        await asyncio.gather(*[process_item(item) for item in items])

        task.progress = 100
        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc)
        task.result_summary = {
            "success": success_count,
            "failed": fail_count,
            "risk_detected": risk_count,
            "products_created": product_count,
            "total": total,
        }

        await self.db.flush()

        await self.session_manager.close_all()

        logger.info(
            f"Task {task_id} completed: {success_count} success, {fail_count} failed, "
            f"{risk_count} risk, {product_count} products"
        )

        return task.result_summary

    async def _fetch_item(self, platform: str, target_id: str) -> dict:
        proxy = await self.proxy_manager.get_proxy()
        proxy_url = None
        proxy_id = None
        if proxy:
            proxy_url = f"{proxy['protocol']}://{proxy['ip']}:{proxy['port']}"
            proxy_id = proxy["id"]

        session, fingerprint = await self.session_manager.get_session(platform, proxy_url)

        adapter_map = {
            "xhs": self._fetch_xhs,
            "douyin": self._fetch_douyin,
            "taobao": self._fetch_taobao,
            "jd": self._fetch_jd,
            "pdd": self._fetch_pdd,
        }
        fetcher = adapter_map.get(platform, self._fetch_generic)

        try:
            result = await fetcher(session, fingerprint, target_id, proxy_url)
            return result
        except aiohttp.ClientError as e:
            if proxy_id:
                await self.proxy_manager.mark_proxy_fail(proxy_id)
            raise

    async def _fetch_xhs(
        self,
        session: aiohttp.ClientSession,
        fingerprint: dict,
        target_id: str,
        proxy_url: str | None = None,
    ) -> dict:
        headers = dict(fingerprint)
        headers["Referer"] = f"https://www.xiaohongshu.com/explore/{target_id}"
        headers["Origin"] = "https://www.xiaohongshu.com"
        headers["Content-Type"] = "application/json;charset=UTF-8"

        payload = {
            "source_note_id": target_id,
            "image_scenes": ["CRD_WM_WEBP"],
        }

        try:
            async with session.post(
                "https://edith.xiaohongshu.com/api/sns/web/v1/feed",
                headers=headers,
                json=payload,
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=20),
                ssl=False,
            ) as resp:
                text = await resp.text()
                if resp.status == 200:
                    return {"raw_text": text, "status_code": resp.status}
        except Exception:
            pass

        headers2 = dict(fingerprint)
        headers2["Referer"] = f"https://www.xiaohongshu.com/goods/{target_id}"

        async with session.get(
            f"https://mall.xiaohongshu.com/api/store/jpd/edith/detail/h5/toc?version=0.0.5&item_id={target_id}",
            headers=headers2,
            proxy=proxy_url,
            timeout=aiohttp.ClientTimeout(total=20),
            ssl=False,
        ) as resp:
            text = await resp.text()
            return {"raw_text": text, "status_code": resp.status}

    async def _fetch_douyin(
        self,
        session: aiohttp.ClientSession,
        fingerprint: dict,
        target_id: str,
        proxy_url: str | None = None,
    ) -> dict:
        headers = dict(fingerprint)
        headers["Referer"] = f"https://www.douyin.com/video/{target_id}"

        async with session.get(
            f"https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={target_id}&aid=6383",
            headers=headers,
            proxy=proxy_url,
            timeout=aiohttp.ClientTimeout(total=20),
            ssl=False,
        ) as resp:
            text = await resp.text()
            return {"raw_text": text, "status_code": resp.status}

    async def _fetch_taobao(
        self,
        session: aiohttp.ClientSession,
        fingerprint: dict,
        target_id: str,
        proxy_url: str | None = None,
    ) -> dict:
        headers = dict(fingerprint)
        headers["Referer"] = f"https://item.taobao.com/item.htm?id={target_id}"

        async with session.get(
            f"https://h5api.m.taobao.com/h5/mtop.taobao.detail.getdetail/6.0/?data=%7B%22itemNumId%22%3A%22{target_id}%22%7D",
            headers=headers,
            proxy=proxy_url,
            timeout=aiohttp.ClientTimeout(total=20),
            ssl=False,
        ) as resp:
            text = await resp.text()
            return {"raw_text": text, "status_code": resp.status}

    async def _fetch_jd(
        self,
        session: aiohttp.ClientSession,
        fingerprint: dict,
        target_id: str,
        proxy_url: str | None = None,
    ) -> dict:
        headers = dict(fingerprint)
        headers["Referer"] = f"https://item.jd.com/{target_id}.html"
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"

        async with session.get(
            f"https://item.m.jd.com/product/{target_id}.html",
            headers=headers,
            proxy=proxy_url,
            timeout=aiohttp.ClientTimeout(total=20),
            ssl=False,
        ) as resp:
            text = await resp.text()
            return {"raw_text": text, "status_code": resp.status}

    async def _fetch_pdd(
        self,
        session: aiohttp.ClientSession,
        fingerprint: dict,
        target_id: str,
        proxy_url: str | None = None,
    ) -> dict:
        headers = dict(fingerprint)
        headers["Referer"] = f"https://mobile.yangkeduo.com/goods.html?goods_id={target_id}"

        async with session.get(
            f"https://mobile.yangkeduo.com/proxy/api/goods?goods_id={target_id}",
            headers=headers,
            proxy=proxy_url,
            timeout=aiohttp.ClientTimeout(total=20),
            ssl=False,
        ) as resp:
            text = await resp.text()
            return {"raw_text": text, "status_code": resp.status}

    async def _fetch_generic(
        self,
        session: aiohttp.ClientSession,
        fingerprint: dict,
        target_id: str,
        proxy_url: str | None = None,
    ) -> dict:
        return {"raw_text": "", "status_code": 404, "parsed": {}}
