import logging
import sys
import traceback
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

_events: list[dict] = []
MAX_EVENTS = 500


class ErrorCapture:
    def __init__(self):
        self._dsn: str | None = None
        self._environment: str = "development"
        self._release: str = "0.0.0"
        self._enabled: bool = False

    def configure(
        self,
        dsn: str | None = None,
        environment: str = "development",
        release: str = "0.0.0",
    ):
        self._dsn = dsn
        self._environment = environment
        self._release = release
        self._enabled = True

        if dsn:
            logger.info(f"Error capture configured: env={environment}, release={release}")
        else:
            logger.info("Error capture running in local-only mode (no DSN)")

    def capture_exception(self, error: Exception, extra: dict[str, Any] | None = None):
        if not self._enabled:
            return

        event = {
            "event_id": _generate_event_id(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "error",
            "type": type(error).__name__,
            "message": str(error),
            "stacktrace": traceback.format_exc(),
            "environment": self._environment,
            "release": self._release,
            "extra": extra or {},
        }

        _events.append(event)
        if len(_events) > MAX_EVENTS:
            _events.pop(0)

        logger.error(f"[ErrorCapture] {event['type']}: {event['message']}")

        if self._dsn:
            self._send_to_sentry(event)

    def capture_message(self, message: str, level: str = "info", extra: dict[str, Any] | None = None):
        if not self._enabled:
            return

        event = {
            "event_id": _generate_event_id(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "type": "message",
            "message": message,
            "stacktrace": None,
            "environment": self._environment,
            "release": self._release,
            "extra": extra or {},
        }

        _events.append(event)
        if len(_events) > MAX_EVENTS:
            _events.pop(0)

    def _send_to_sentry(self, event: dict):
        import json
        import urllib.request

        payload = {
            "event_id": event["event_id"],
            "timestamp": event["timestamp"],
            "level": event["level"],
            "logger": "vuemonitor",
            "platform": "python",
            "exception": {
                "values": [{
                    "type": event["type"],
                    "value": event["message"],
                    "stacktrace": {
                        "frames": _parse_stacktrace(event.get("stacktrace", "")),
                    },
                }],
            },
            "tags": {
                "environment": event["environment"],
                "release": event["release"],
            },
            "extra": event.get("extra", {}),
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self._dsn + "/api/1/store/",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "X-Sentry-Auth": f"Sentry sentry_version=7, sentry_client=vuemonitor/1.0",
                },
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            logger.warning(f"Failed to send event to Sentry: {e}")

    def get_events(self, limit: int = 50, level: str | None = None) -> list[dict]:
        events = _events
        if level:
            events = [e for e in events if e.get("level") == level]
        return events[-limit:]

    def clear_events(self):
        _events.clear()


def _generate_event_id() -> str:
    import uuid
    return uuid.uuid4().hex


def _parse_stacktrace(stacktrace: str) -> list[dict]:
    frames = []
    for line in stacktrace.strip().split("\n"):
        line = line.strip()
        if line.startswith("File "):
            parts = line.replace('File "', "").split('", line ')
            if len(parts) == 2:
                filepath = parts[0]
                lineno = parts[1].replace(", in ", "|").split("|")
                frames.append({
                    "filename": filepath,
                    "lineno": int(lineno[0]) if lineno[0].isdigit() else 0,
                    "function": lineno[1] if len(lineno) > 1 else "",
                })
    return frames


error_capture = ErrorCapture()


def setup_error_capture():
    settings = get_settings()
    dsn = getattr(settings, "SENTRY_DSN", None)
    env = getattr(settings, "ENVIRONMENT", "development")
    release = getattr(settings, "APP_VERSION", "0.0.0")

    error_capture.configure(dsn=dsn, environment=env, release=release)

    def _global_exception_handler(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        error_capture.capture_exception(
            exc_value,
            extra={"unhandled": True},
        )

    sys.excepthook = _global_exception_handler