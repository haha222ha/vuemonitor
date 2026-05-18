import json
import time
import uuid
from datetime import datetime, timezone

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.database import engine
from sqlalchemy import text

SENSITIVE_HEADERS = {"authorization", "cookie", "x-api-key", "x-csrf-token"}
SENSITIVE_BODY_KEYS = {"password", "token", "secret", "credit_card", "api_key", "private_key"}
SUSPICIOUS_PATTERNS = [
    "' OR ", '" OR ', "1=1", "UNION SELECT", "-- ", "; DROP ",
    "<script>", "javascript:", "onerror=", "onload=",
    "../", "..\\", "/etc/passwd", "/proc/self",
    "${", "#{", "%{", "{{",
]

AUDITED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class SecurityAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith(("/docs", "/redoc", "/openapi.json", "/health")):
            return await call_next(request)

        request_id = str(uuid.uuid4())[:8]
        start = time.time()
        audit_record = {
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params) if request.query_params else None,
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "user_id": None,
            "risk_score": 0,
            "risk_flags": [],
            "status_code": None,
            "response_time_ms": None,
        }

        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from app.core.security import decode_access_token
                payload = decode_access_token(auth_header[7:])
                audit_record["user_id"] = payload.get("sub")
            except Exception:
                audit_record["risk_flags"].append("invalid_token")
                audit_record["risk_score"] += 20

        if request.method in AUDITED_METHODS:
            try:
                body = await request.body()
                if body:
                    body_risk = self._analyze_body_sync(body)
                    audit_record["risk_score"] += body_risk["score"]
                    audit_record["risk_flags"].extend(body_risk["flags"])
            except Exception:
                pass

        query_risk = self._analyze_query(request)
        audit_record["risk_score"] += query_risk["score"]
        audit_record["risk_flags"].extend(query_risk["flags"])

        header_risk = self._analyze_headers(request)
        audit_record["risk_score"] += header_risk["score"]
        audit_record["risk_flags"].extend(header_risk["flags"])

        try:
            response: Response = await call_next(request)
            audit_record["status_code"] = response.status_code

            if response.status_code == 401:
                audit_record["risk_flags"].append("auth_failure")
                audit_record["risk_score"] += 15
            elif response.status_code == 403:
                audit_record["risk_flags"].append("access_denied")
                audit_record["risk_score"] += 20
            elif response.status_code >= 500:
                audit_record["risk_flags"].append("server_error")
                audit_record["risk_score"] += 10
            elif response.status_code == 429:
                audit_record["risk_flags"].append("rate_limited")
                audit_record["risk_score"] += 25

        except Exception as exc:
            audit_record["status_code"] = 500
            audit_record["risk_flags"].append("unhandled_exception")
            audit_record["risk_score"] += 30
            raise
        finally:
            audit_record["response_time_ms"] = round((time.time() - start) * 1000, 1)
            audit_record["risk_flags"] = list(set(audit_record["risk_flags"]))

            if audit_record["risk_score"] > 0 or request.method in AUDITED_METHODS:
                await self._persist_audit(audit_record)

            if audit_record["risk_score"] >= 50:
                import logging
                security_logger = logging.getLogger("security.audit")
                security_logger.warning(
                    "high_risk_request",
                    extra={"audit": audit_record},
                )

        return response

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _analyze_body_sync(self, body: bytes) -> dict:
        result = {"score": 0, "flags": []}
        try:
            if not body:
                return result
            body_str = body.decode("utf-8", errors="replace")

            for pattern in SUSPICIOUS_PATTERNS:
                if pattern.lower() in body_str.lower():
                    result["score"] += 30
                    result["flags"].append(f"suspicious_pattern:{pattern.strip()[:20]}")
                    break

            try:
                parsed = json.loads(body_str)
                if isinstance(parsed, dict):
                    for key in parsed:
                        if key.lower() in SENSITIVE_BODY_KEYS:
                            result["flags"].append(f"sensitive_field:{key}")
                    if len(body_str) > 100000:
                        result["score"] += 10
                        result["flags"].append("oversized_body")
            except json.JSONDecodeError:
                pass

        except Exception:
            pass
        return result

    def _analyze_query(self, request: Request) -> dict:
        result = {"score": 0, "flags": []}
        query_str = str(request.query_params)
        if not query_str:
            return result

        for pattern in SUSPICIOUS_PATTERNS:
            if pattern.lower() in query_str.lower():
                result["score"] += 30
                result["flags"].append(f"query_injection:{pattern.strip()[:20]}")
                break

        if len(query_str) > 2000:
            result["score"] += 10
            result["flags"].append("oversized_query")

        return result

    def _analyze_headers(self, request: Request) -> dict:
        result = {"score": 0, "flags": []}

        content_type = request.headers.get("content-type", "")
        if request.method in AUDITED_METHODS and "json" not in content_type and "form" not in content_type:
            if content_type:
                result["score"] += 5
                result["flags"].append("unexpected_content_type")

        if not request.headers.get("user-agent"):
            result["score"] += 10
            result["flags"].append("missing_user_agent")

        if request.headers.get("x-forwarded-for", "").count(",") > 5:
            result["score"] += 15
            result["flags"].append("header_spoofing_suspect")

        return result

    async def _persist_audit(self, record: dict):
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text("""
                        INSERT INTO security_audit_log
                        (request_id, timestamp, method, path, query, client_ip,
                         user_agent, user_id, risk_score, risk_flags,
                         status_code, response_time_ms)
                        VALUES
                        (:request_id, :timestamp, :method, :path, :query, :client_ip,
                         :user_agent, :user_id, :risk_score, :risk_flags::jsonb,
                         :status_code, :response_time_ms)
                    """),
                    {
                        "request_id": record["request_id"],
                        "timestamp": record["timestamp"],
                        "method": record["method"],
                        "path": record["path"],
                        "query": record["query"],
                        "client_ip": record["client_ip"],
                        "user_agent": record["user_agent"][:500],
                        "user_id": record["user_id"],
                        "risk_score": record["risk_score"],
                        "risk_flags": json.dumps(record["risk_flags"]),
                        "status_code": record["status_code"],
                        "response_time_ms": record["response_time_ms"],
                    },
                )
        except Exception:
            pass
