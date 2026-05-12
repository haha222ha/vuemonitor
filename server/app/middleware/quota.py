import time
from datetime import datetime, timezone

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from app.core.redis import get_redis
from shared.constants.feature_gates import PLAN_LIMITS

_QUOTA_PATH_MAP = {
    "/api/v1/collect": ("dailyCollectLimit", "collect"),
    "/api/v1/ai/analyze": ("aiCallsPerDay", "ai"),
    "/api/v1/monitor": ("maxProducts", "monitor"),
    "/api/v1/ai/templates": ("aiCallsPerDay", "ai_template"),
}

_EXEMPT_PREFIXES = (
    "/api/v1/auth",
    "/api/v1/license",
    "/api/v1/health",
    "/api/v1/admin",
    "/api/v1/gdpr",
    "/api/v1/security",
    "/api/v1/operation-audit",
    "/docs",
    "/openapi.json",
    "/redoc",
)


class QuotaEnforcementMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path

        if path.startswith(_EXEMPT_PREFIXES):
            return await call_next(request)

        user = getattr(request.state, "user", None)
        if not user:
            return await call_next(request)

        plan = getattr(user, "plan", "free")
        limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

        for prefix, (quota_key, counter_name) in _QUOTA_PATH_MAP.items():
            if path.startswith(prefix):
                limit = limits.get(quota_key, -1)
                if limit == -1:
                    return await call_next(request)

                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                redis_key = f"quota:{counter_name}:{user.id}:{today}"

                try:
                    redis = await get_redis()
                    current = await redis.incr(redis_key)
                    if current == 1:
                        await redis.expire(redis_key, 86400)

                    if current > limit:
                        return JSONResponse(
                            status_code=429,
                            content={
                                "code": 42901,
                                "message": f"今日{counter_name}配额已用尽(限制:{limit}/天)，请升级套餐",
                                "data": {
                                    "quota_key": quota_key,
                                    "limit": limit,
                                    "current": current,
                                    "plan": plan,
                                },
                            },
                        )

                    response = await call_next(request)
                    response.headers["X-Quota-Limit"] = str(limit)
                    response.headers["X-Quota-Remaining"] = str(max(0, limit - current))
                    return response
                except Exception:
                    return await call_next(request)

        return await call_next(request)
