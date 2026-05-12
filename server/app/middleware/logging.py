import json
import time
import uuid
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start_time = time.monotonic()

        response = await call_next(request)

        duration_ms = round((time.monotonic() - start_time) * 1000, 2)

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params) if request.query_params else None,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("User-Agent", ""),
            "referer": request.headers.get("Referer", ""),
        }

        settings = get_settings()

        if response.status_code >= 500:
            log_entry["level"] = "error"
        elif response.status_code >= 400:
            log_entry["level"] = "warn"
        else:
            log_entry["level"] = "info"

        if settings.LOG_FORMAT == "json":
            print(json.dumps(log_entry, ensure_ascii=False))
        else:
            level = log_entry["level"].upper()
            print(f"[{log_entry['timestamp']}] [{level}] {request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms) req={request_id}")

        if response.status_code >= 500:
            from app.services.alert_service import alert_service
            await alert_service.send_alert(
                level="critical",
                title=f"Server Error: {request.method} {request.url.path}",
                detail=f"Status: {response.status_code}, Duration: {duration_ms}ms, Request: {request_id}",
            )

        response.headers["X-Request-ID"] = request_id
        return response
