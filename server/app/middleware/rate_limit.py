import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.cache import rate_limit_sliding_window

logger = logging.getLogger(__name__)

PLAN_LIMITS: dict[str, dict[str, dict[str, tuple[int, int]]]] = {
    "free": {
        "default": {"GET": (60, 60), "POST": (15, 60), "PUT": (15, 60), "DELETE": (10, 60), "PATCH": (15, 60)},
        "paths": {
            "/api/v1/auth/login": (3, 60),
            "/api/v1/auth/register": (2, 60),
            "/api/v1/auth/refresh": (5, 60),
            "/api/v1/collect": (5, 120),
            "/api/v1/ai": (5, 120),
            "/api/v1/gdpr/export": (2, 3600),
            "/api/v1/gdpr/deletion-request": (1, 86400),
        },
    },
    "pro": {
        "default": {"GET": (180, 60), "POST": (60, 60), "PUT": (60, 60), "DELETE": (30, 60), "PATCH": (60, 60)},
        "paths": {
            "/api/v1/auth/login": (5, 60),
            "/api/v1/auth/register": (3, 60),
            "/api/v1/auth/refresh": (10, 60),
            "/api/v1/collect": (20, 60),
            "/api/v1/ai": (20, 60),
            "/api/v1/gdpr/export": (5, 3600),
            "/api/v1/gdpr/deletion-request": (1, 86400),
        },
    },
    "enterprise": {
        "default": {"GET": (600, 60), "POST": (200, 60), "PUT": (200, 60), "DELETE": (100, 60), "PATCH": (200, 60)},
        "paths": {
            "/api/v1/auth/login": (10, 60),
            "/api/v1/auth/register": (5, 60),
            "/api/v1/auth/refresh": (20, 60),
            "/api/v1/collect": (60, 60),
            "/api/v1/ai": (60, 60),
            "/api/v1/gdpr/export": (10, 3600),
            "/api/v1/gdpr/deletion-request": (2, 86400),
        },
    },
}

_DEFAULT_PLAN = "free"

_PATH_PREFIX_OVERRIDES: list[tuple[str, tuple[int, int]]] = [
    ("/api/v1/admin/", (30, 60)),
    ("/api/v1/audit/", (20, 60)),
    ("/api/v1/notifications/", (60, 60)),
    ("/api/v1/dashboard/", (120, 60)),
    ("/api/v1/products/", (90, 60)),
    ("/api/v1/monitor/", (60, 60)),
    ("/api/v1/teams/", (40, 60)),
    ("/api/v1/alert-rules/", (30, 60)),
    ("/api/v1/ai/templates/", (20, 60)),
    ("/api/v1/security/", (10, 60)),
]


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path.rstrip("/")
        method = request.method

        if not path.startswith("/api/v1/"):
            return await call_next(request)

        plan = self._get_user_plan(request)
        plan_config = PLAN_LIMITS.get(plan, PLAN_LIMITS[_DEFAULT_PLAN])

        max_requests, window_seconds = self._resolve_limit(path, method, plan_config)

        client_id = self._get_client_id(request)
        identifier = f"rl:{plan}:{method}:{path}:{client_id}"

        burst_key = f"burst:{identifier}"
        burst_allowed, _ = await rate_limit_sliding_window(burst_key, max_requests * 2, window_seconds * 10)

        allowed, remaining = await rate_limit_sliding_window(identifier, max_requests, window_seconds)

        if not allowed and not burst_allowed:
            logger.warning(f"Rate limit exceeded: {identifier}")
            return JSONResponse(
                status_code=429,
                content={
                    "code": 429,
                    "message": "请求过于频繁，请稍后再试",
                    "detail": f"Limit: {max_requests} per {window_seconds}s (plan: {plan})",
                },
                headers={
                    "Retry-After": str(window_seconds),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Plan": plan,
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Plan"] = plan
        return response

    def _resolve_limit(self, path: str, method: str, plan_config: dict) -> tuple[int, int]:
        path_limits = plan_config.get("paths", {})
        if path in path_limits:
            return path_limits[path]

        for prefix, limit in _PATH_PREFIX_OVERRIDES:
            if path.startswith(prefix):
                return limit

        default_limits = plan_config.get("default", {})
        return default_limits.get(method, (60, 60))

    def _get_user_plan(self, request: Request) -> str:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from app.core.security import decode_access_token
                payload = decode_access_token(auth_header[7:])
                return payload.get("plan", _DEFAULT_PLAN)
            except Exception:
                pass
        return _DEFAULT_PLAN

    def _get_client_id(self, request: Request) -> str:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return f"token:{auth_header[7:20]}"

        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"

        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"
