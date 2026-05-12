import logging
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)

_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
_span_id_var: ContextVar[str] = ContextVar("span_id", default="")

_traces: dict[str, dict] = {}
MAX_TRACES = 1000


def get_trace_id() -> str:
    return _trace_id_var.get()


def get_span_id() -> str:
    return _span_id_var.get()


def generate_trace_id() -> str:
    return uuid.uuid4().hex[:16]


def generate_span_id() -> str:
    return uuid.uuid4().hex[:8]


class TracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if request.url.path in ("/metrics", "/health", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        trace_id = request.headers.get("X-Trace-ID", generate_trace_id())
        span_id = generate_span_id()
        parent_span_id = request.headers.get("X-Span-ID", "")

        _trace_id_var.set(trace_id)
        _span_id_var.set(span_id)

        trace = _traces.setdefault(trace_id, {
            "trace_id": trace_id,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "spans": [],
        })

        span = {
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "operation": f"{request.method} {request.url.path}",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "tags": {
                "http.method": request.method,
                "http.url": str(request.url),
                "http.client_ip": request.client.host if request.client else "",
            },
        }

        import time
        start = time.time()

        try:
            response = await call_next(request)
            span["status"] = "ok"
            span["tags"]["http.status_code"] = str(response.status_code)
        except Exception as e:
            span["status"] = "error"
            span["tags"]["error"] = str(e)
            raise
        finally:
            span["duration_ms"] = round((time.time() - start) * 1000, 2)
            span["end_time"] = datetime.now(timezone.utc).isoformat()
            trace["spans"].append(span)

            if len(_traces) > MAX_TRACES:
                oldest = min(_traces.keys(), key=lambda k: _traces[k].get("start_time", ""))
                _traces.pop(oldest, None)

        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Span-ID"] = span_id
        return response


def add_custom_span(operation: str, tags: dict[str, str] | None = None, duration_ms: float = 0) -> str:
    trace_id = _trace_id_var.get()
    if not trace_id:
        return ""

    span_id = generate_span_id()
    parent_span_id = _span_id_var.get()

    span = {
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "operation": operation,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": datetime.now(timezone.utc).isoformat(),
        "duration_ms": duration_ms,
        "status": "ok",
        "tags": tags or {},
    }

    trace = _traces.setdefault(trace_id, {
        "trace_id": trace_id,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "spans": [],
    })
    trace["spans"].append(span)
    return span_id


def get_trace(trace_id: str) -> dict | None:
    return _traces.get(trace_id)


def get_all_traces(limit: int = 50) -> list[dict]:
    sorted_traces = sorted(
        _traces.values(),
        key=lambda t: t.get("start_time", ""),
        reverse=True,
    )
    return sorted_traces[:limit]


def clear_traces():
    _traces.clear()