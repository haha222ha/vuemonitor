import json
import logging
from datetime import datetime, timezone
from typing import Any

import structlog

from app.config import get_settings

logger = structlog.get_logger()


class AlertService:
    def __init__(self):
        self._channels: list[dict] = []
        self._alert_history: list[dict] = []
        self._max_history = 1000

    def add_channel(self, channel_type: str, config: dict):
        self._channels.append({"type": channel_type, "config": config})

    async def send_alert(self, level: str, title: str, detail: str, extra: dict | None = None):
        alert = {
            "id": str(len(self._alert_history) + 1),
            "level": level,
            "title": title,
            "detail": detail,
            "extra": extra or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._alert_history.append(alert)
        if len(self._alert_history) > self._max_history:
            self._alert_history = self._alert_history[-self._max_history:]

        logger.error(
            "alert_triggered",
            level=level,
            title=title,
            detail=detail,
            extra=extra,
        )

        for channel in self._channels:
            try:
                if channel["type"] == "webhook":
                    await self._send_webhook(channel["config"], alert)
                elif channel["type"] == "email":
                    await self._send_email(channel["config"], alert)
                elif channel["type"] == "log":
                    self._send_log(alert)
            except Exception as e:
                logger.error("alert_channel_failed", channel=channel["type"], error=str(e))

    async def _send_webhook(self, config: dict, alert: dict):
        import httpx

        url = config.get("url")
        if not url:
            return

        payload = {
            "text": f"[{alert['level'].upper()}] {alert['title']}",
            "alert": alert,
        }

        headers = config.get("headers", {})
        headers["Content-Type"] = "application/json"

        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json=payload, headers=headers)

    async def _send_email(self, config: dict, alert: dict):
        from app.services.email_service import EmailService

        email_service = EmailService()
        recipients = config.get("recipients", [])
        if not recipients:
            return

        subject = f"[{alert['level'].upper()}] {alert['title']}"
        body = f"Level: {alert['level']}\nTitle: {alert['title']}\nDetail: {alert['detail']}\nTime: {alert['timestamp']}"
        if alert.get("extra"):
            body += f"\nExtra: {json.dumps(alert['extra'], ensure_ascii=False)}"

        for recipient in recipients:
            try:
                await email_service.send_email(recipient, subject, body)
            except Exception:
                pass

    def _send_log(self, alert: dict):
        settings = get_settings()
        log_line = json.dumps(alert, ensure_ascii=False) if settings.LOG_FORMAT == "json" else \
            f"[ALERT][{alert['level'].upper()}] {alert['title']} - {alert['detail']}"
        print(log_line)

    def get_alert_history(self, level: str | None = None, limit: int = 50) -> list[dict]:
        alerts = self._alert_history
        if level:
            alerts = [a for a in alerts if a["level"] == level]
        return alerts[-limit:]

    def get_alert_stats(self) -> dict:
        from collections import Counter

        level_counts = Counter(a["level"] for a in self._alert_history)
        return {
            "total": len(self._alert_history),
            "by_level": dict(level_counts),
        }


alert_service = AlertService()


def configure_structlog():
    settings = get_settings()

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if settings.LOG_FORMAT == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
