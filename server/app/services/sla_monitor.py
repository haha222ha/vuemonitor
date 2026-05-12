import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from app.core.redis import get_redis
from app.middleware.prometheus import counter_inc, gauge_set
from app.services.alert_service import alert_service

logger = logging.getLogger(__name__)

SLO_KEY = "slo:metrics"
SLO_WINDOW = 30 * 24 * 3600

_DEFAULT_SLOS: dict[str, dict] = {
    "availability": {
        "name": "API 可用性",
        "target": 0.999,
        "description": "API 请求成功率 >= 99.9%",
        "metric": "http_requests_total",
        "good_filter": 'status!~"5.."',
    },
    "latency_p95": {
        "name": "P95 延迟",
        "target": 0.5,
        "description": "95% 请求延迟 <= 500ms",
        "metric": "http_request_duration_seconds",
        "threshold": 0.5,
    },
    "latency_p99": {
        "name": "P99 延迟",
        "target": 2.0,
        "description": "99% 请求延迟 <= 2s",
        "metric": "http_request_duration_seconds",
        "threshold": 2.0,
    },
    "error_budget_burn": {
        "name": "错误预算消耗率",
        "target": 1.0,
        "description": "错误预算消耗速率 <= 1x",
    },
}


class SLAMonitor:
    def __init__(self):
        self._slos = dict(_DEFAULT_SLOS)
        self._running = False

    async def start(self):
        self._running = True
        asyncio.create_task(self._monitor_loop())
        logger.info("SLA Monitor started")

    async def stop(self):
        self._running = False

    async def _monitor_loop(self):
        while self._running:
            try:
                await self._evaluate_slos()
            except Exception as e:
                logger.error(f"SLA evaluation error: {e}")
            await asyncio.sleep(60)

    async def _evaluate_slos(self):
        now = time.time()
        window_start = now - SLO_WINDOW

        redis = await get_redis()
        metrics = await redis.hgetall(SLO_KEY)

        for slo_name, slo in self._slos.items():
            try:
                if slo_name == "availability":
                    await self._eval_availability(slo, window_start, now)
                elif slo_name.startswith("latency"):
                    await self._eval_latency(slo, window_start, now)
                elif slo_name == "error_budget_burn":
                    await self._eval_error_budget(slo, window_start, now)
            except Exception as e:
                logger.error(f"SLO evaluation failed for {slo_name}: {e}")

    async def _eval_availability(self, slo: dict, window_start: float, now: float):
        target = slo["target"]
        error_budget = (1 - target) * SLO_WINDOW

        gauge_set("slo_availability_target", target)
        gauge_set("slo_error_budget_seconds", error_budget)

        if error_budget < 3600:
            await alert_service.send_alert(
                title="SLO 告警: 错误预算不足",
                message=f"API 可用性错误预算仅剩 {error_budget:.0f} 秒，低于 1 小时阈值",
                severity="critical",
                channel="webhook",
            )

    async def _eval_latency(self, slo: dict, window_start: float, now: float):
        threshold = slo.get("threshold", 1.0)
        gauge_set(f"slo_{slo.get('name', '').replace(' ', '_').lower()}_threshold", threshold)

    async def _eval_error_budget(self, slo: dict, window_start: float, now: float):
        burn_rate = 1.0
        gauge_set("slo_error_budget_burn_rate", burn_rate)

        if burn_rate > 10:
            await alert_service.send_alert(
                title="SLO 严重告警: 错误预算快速消耗",
                message=f"错误预算消耗速率 = {burn_rate:.1f}x，超过 10x 阈值",
                severity="critical",
                channel="webhook",
            )
        elif burn_rate > 2:
            await alert_service.send_alert(
                title="SLO 告警: 错误预算消耗加速",
                message=f"错误预算消耗速率 = {burn_rate:.1f}x，超过 2x 阈值",
                severity="warning",
                channel="webhook",
            )

    def get_slos(self) -> dict:
        return dict(self._slos)

    def update_slo(self, name: str, config: dict) -> dict:
        self._slos[name] = {**self._slos.get(name, {}), **config}
        return self._slos[name]

    def delete_slo(self, name: str) -> bool:
        if name in ("availability", "latency_p95", "latency_p99", "error_budget_burn"):
            return False
        return self._slos.pop(name, None) is not None


sla_monitor = SLAMonitor()