import asyncio
import logging
import time

from app.core.redis import get_redis
from app.middleware.prometheus import gauge_set
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

_ALERT_COOLDOWN_SECONDS = 1800
_last_alert_times: dict[str, float] = {}


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
        slo_data = await redis.hgetall(SLO_KEY)

        total_requests = int(slo_data.get("total_requests", "0") or "0")
        error_requests = int(slo_data.get("error_requests", "0") or "0")

        for slo_name, slo in self._slos.items():
            try:
                if slo_name == "availability":
                    await self._eval_availability(slo, window_start, now, total_requests, error_requests)
                elif slo_name.startswith("latency"):
                    await self._eval_latency(slo, window_start, now)
                elif slo_name == "error_budget_burn":
                    await self._eval_error_budget(slo, window_start, now, total_requests, error_requests)
            except Exception as e:
                logger.error(f"SLO evaluation failed for {slo_name}: {e}")

    async def _eval_availability(self, slo: dict, window_start: float, now: float,
                                  total_requests: int, error_requests: int):
        target = slo["target"]
        total_budget = (1 - target) * SLO_WINDOW

        if total_requests > 0:
            current_availability = 1 - (error_requests / total_requests)
            consumed_budget = error_requests / total_requests * SLO_WINDOW
            remaining_budget = max(0, total_budget - consumed_budget)
        else:
            current_availability = 1.0
            remaining_budget = total_budget

        gauge_set("slo_availability_target", target)
        gauge_set("slo_availability_current", current_availability)
        gauge_set("slo_error_budget_seconds", remaining_budget)

        if remaining_budget < 3600:
            await self._send_alert_throttled(
                "availability_critical",
                "critical",
                "SLO 告警: 错误预算不足",
                f"API 可用性错误预算仅剩 {remaining_budget:.0f} 秒（当前可用性 {current_availability:.4f}），低于 1 小时阈值",
            )
        elif remaining_budget < total_budget * 0.25:
            await self._send_alert_throttled(
                "availability_warning",
                "warning",
                "SLO 警告: 错误预算偏低",
                f"API 可用性错误预算剩余 {remaining_budget:.0f} 秒（当前可用性 {current_availability:.4f}），低于 25% 阈值",
            )

    async def _eval_latency(self, slo: dict, window_start: float, now: float):
        threshold = slo.get("threshold", 1.0)
        gauge_set(f"slo_{slo.get('name', '').replace(' ', '_').lower()}_threshold", threshold)

    async def _eval_error_budget(self, slo: dict, window_start: float, now: float,
                                  total_requests: int, error_requests: int):
        target = _DEFAULT_SLOS["availability"]["target"]
        total_budget = (1 - target) * SLO_WINDOW

        if total_requests > 0 and error_requests > 0:
            error_rate = error_requests / total_requests
            projected_errors = error_rate * SLO_WINDOW
            burn_rate = projected_errors / total_budget if total_budget > 0 else 0
        else:
            burn_rate = 0

        gauge_set("slo_error_budget_burn_rate", burn_rate)

        if burn_rate > 10:
            await self._send_alert_throttled(
                "burn_rate_critical",
                "critical",
                "SLO 严重告警: 错误预算快速消耗",
                f"错误预算消耗速率 = {burn_rate:.1f}x，超过 10x 阈值",
            )
        elif burn_rate > 2:
            await self._send_alert_throttled(
                "burn_rate_warning",
                "warning",
                "SLO 告警: 错误预算消耗加速",
                f"错误预算消耗速率 = {burn_rate:.1f}x，超过 2x 阈值",
            )

    async def _send_alert_throttled(self, alert_key: str, level: str, title: str, detail: str):
        now = time.time()
        last_sent = _last_alert_times.get(alert_key, 0)
        if now - last_sent < _ALERT_COOLDOWN_SECONDS:
            return
        _last_alert_times[alert_key] = now
        await alert_service.send_alert(level=level, title=title, detail=detail)

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
