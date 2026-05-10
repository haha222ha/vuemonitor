import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.cache import rate_limit_sliding_window

logger = logging.getLogger(__name__)

_DEFAULT_LIMITS: dict[str, tuple[int, int]] = {
    "POST": (30, 60),
    "PUT": (30, 60),
    "DELETE": (20, 60),
    "GET": (120, 60),
    "PATCH": (30, 60),
}

_PATH_OVERRIDES: dict[str, tuple[int, int]] = {
    "/api/v1/auth/login": (5, 60),
    "/api/v1/auth/register": (3, 60),
    "/api/v1/auth/refresh": (10, 60),
    "/api/v1/collect": (10, 60),
    "/api/v1/ai": (10, 120),
}


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path.rstrip("/")
        method = request.method

        if path.startswith("/api/v1/"):
            max_requests, window_seconds = _PATH_OVERRIDES.get(
                path, _DEFAULT_LIMITS.get(method, (60, 60))
            )
        else:
            return await call_next(request)

        client_id = self._get_client_id(request)
        identifier = f"{method}:{path}:{client_id}"

        allowed, remaining = await rate_limit_sliding_window(
            identifier, max_requests, window_seconds
        )

        if not allowed:
            logger.warning(f"Rate limit exceeded: {identifier}")
            return JSONResponse(
                status_code=429,
                content={
                    "code": 429,
                    "message": "请求过于频繁，请稍后再试",
                    "detail": f"Limit: {max_requests} per {window_seconds}s",
                },
                headers={
                    "Retry-After": str(window_seconds),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    def _get_client_id(self, request: Request) -> str:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return f"token:{auth_header[7:20]}"

        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"

        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"
