import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings

SENSITIVE_RESPONSE_HEADERS = {"set-cookie", "x-request-id"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        settings = get_settings()

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

            nonce = secrets.token_urlsafe(16)
            response.headers["Content-Security-Policy"] = (
                f"default-src 'self'; "
                f"script-src 'self' 'nonce-{nonce}'; "
                f"style-src 'self' 'nonce-{nonce}' https://fonts.googleapis.com; "
                f"font-src 'self' https://fonts.gstatic.com; "
                f"img-src 'self' data: https:; "
                f"connect-src 'self' https://api.deepseek.com https://api.openai.com wss:; "
                f"frame-ancestors 'none'"
            )
            response.headers["X-CSP-Nonce"] = nonce

            for header_name in SENSITIVE_RESPONSE_HEADERS:
                if header_name in response.headers:
                    value = response.headers[header_name]
                    if "token=" in value.lower() or "session=" in value.lower():
                        response.headers[header_name] = value.split(";")[0] + "; HttpOnly; Secure; SameSite=Strict"

        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"

        return response
