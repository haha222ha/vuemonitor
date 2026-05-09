import asyncio
import uuid
from datetime import datetime, timezone

import aiohttp
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.collect.rate_controller import AdaptiveRateController
from app.core.exceptions import AppException
from app.models.admin import ProxyPool, ProxyProvider, RiskEvent
from app.models.collect import CollectTask, CollectTaskItem


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
        "captcha": {"keywords": ["验证码", "captcha", "verify"], "level": "high"},
        "login_required": {"keywords": ["登录", "login", "sign in"], "level": "high"},
        "rate_limit": {"keywords": ["频繁", "too many", "rate limit", "429"], "level": "medium"},
        "ip_blocked": {"keywords": ["封禁", "blocked", "forbidden", "403"], "level": "critical"},
        "data_empty": {"keywords": [], "level": "low"},
    }

    @classmethod
    def detect(cls, response_text: str, status_code: int) -> dict | None:
        if status_code == 429:
            return {"risk_type": "rate_limit", "risk_level": "medium", "detail": {"status_code": 429}}
        if status_code == 403:
            return {"risk_type": "ip_blocked", "risk_level": "critical", "detail": {"status_code": 403}}

        text_lower = response_text.lower()
        for risk_type, config in cls.RISK_PATTERNS.items():
            for keyword in config["keywords"]:
                if keyword in text_lower:
                    return {"risk_type": risk_type, "risk_level": config["level"], "detail": {"keyword": keyword}}

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


class CollectEngine:
    def __init__(self, db: AsyncSession, max_concurrency: int = 8):
        self.db = db
        self.max_concurrency = max_concurrency
        self.rate_controller = AdaptiveRateController()
        self.proxy_manager = ProxyManager(db)
        self.risk_detector = RiskDetector()
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def execute_task(self, task_id: uuid.UUID) -> dict:
        result = await self.db.execute(select(CollectTask).where(CollectTask.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return {"status": "error", "message": "任务不存在"}

        task.status = "running"
        task.started_at = datetime.now(timezone.utc)

        items_result = await self.db.execute(
            select(CollectTaskItem).where(CollectTaskItem.task_id == task_id)
        )
        items = items_result.scalars().all()

        if not items:
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)
            return {"status": "completed", "collected": 0}

        success_count = 0
        fail_count = 0
        risk_count = 0
        _lock = asyncio.Lock()

        async def process_item(item: CollectTaskItem):
            nonlocal success_count, fail_count, risk_count
            async with self._semaphore:
                await self.rate_controller.acquire()
                try:
                    data = await self._fetch_item(task.platform, item.target_id)
                    risk = self.risk_detector.detect(data.get("raw_text", ""), data.get("status_code", 200))

                    if risk:
                        async with _lock:
                            risk_count += 1
                        self.rate_controller.on_risk_detected()
                        await self.risk_detector.record_risk_event(
                            self.db, task.id, task.platform, risk["risk_type"], risk["risk_level"], risk["detail"]
                        )
                        item.status = "risk_detected"
                        item.error_message = risk["risk_type"]
                    else:
                        self.rate_controller.on_success()
                        item.status = "completed"
                        item.result = data.get("parsed", {})
                        item.completed_at = datetime.now(timezone.utc)
                        async with _lock:
                            success_count += 1
                except Exception as e:
                    self.rate_controller.on_error()
                    item.status = "failed"
                    item.error_message = str(e)
                    async with _lock:
                        fail_count += 1

        await asyncio.gather(*[process_item(item) for item in items])

        task.progress = 100
        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc)
        task.result_summary = {
            "success": success_count,
            "failed": fail_count,
            "risk_detected": risk_count,
            "total": len(items),
        }

        await self.db.commit()

        return task.result_summary

    async def _fetch_item(self, platform: str, target_id: str) -> dict:
        proxy = await self.proxy_manager.get_proxy()

        adapter_map = {
            "xhs": self._fetch_xhs,
            "douyin": self._fetch_douyin,
            "taobao": self._fetch_taobao,
            "jd": self._fetch_jd,
            "pdd": self._fetch_pdd,
        }
        fetcher = adapter_map.get(platform, self._fetch_generic)

        proxy_url = None
        proxy_id = None
        if proxy:
            proxy_url = f"{proxy['protocol']}://{proxy['ip']}:{proxy['port']}"
            proxy_id = proxy["id"]

        try:
            result = await fetcher(target_id, proxy_url)
            return result
        except aiohttp.ClientError as e:
            if proxy_id:
                await self.proxy_manager.mark_proxy_fail(proxy_id)
            raise

    async def _fetch_xhs(self, target_id: str, proxy_url: str | None = None) -> dict:
        return await self._http_get(
            f"https://edith.xiaohongshu.com/api/sns/web/v1/feed",
            proxy_url,
            headers={"User-Agent": "Mozilla/5.0"},
        )

    async def _fetch_douyin(self, target_id: str, proxy_url: str | None = None) -> dict:
        return await self._http_get(
            f"https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={target_id}",
            proxy_url,
        )

    async def _fetch_taobao(self, target_id: str, proxy_url: str | None = None) -> dict:
        return await self._http_get(
            f"https://h5api.m.taobao.com/h5/mtop.taobao.detail.getdetail/6.0/?data=%7B%22itemNumId%22%3A%22{target_id}%22%7D",
            proxy_url,
        )

    async def _fetch_jd(self, target_id: str, proxy_url: str | None = None) -> dict:
        return await self._http_get(
            f"https://item.m.jd.com/product/{target_id}.html",
            proxy_url,
        )

    async def _fetch_pdd(self, target_id: str, proxy_url: str | None = None) -> dict:
        return await self._http_get(
            f"https://mobile.yangkeduo.com/proxy/api/goods?goods_id={target_id}",
            proxy_url,
        )

    async def _fetch_generic(self, target_id: str, proxy_url: str | None = None) -> dict:
        return {"raw_text": "", "status_code": 404, "parsed": {}}

    async def _http_get(self, url: str, proxy_url: str | None = None, headers: dict | None = None) -> dict:
        default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/html, */*",
        }
        if headers:
            default_headers.update(headers)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, proxy=proxy_url, headers=default_headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                text = await resp.text()
                return {"raw_text": text, "status_code": resp.status, "parsed": {}}
