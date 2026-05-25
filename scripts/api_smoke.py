#!/usr/bin/env python3
"""Core API smoke test for XHS365 — run against local or production base URL."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def _request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: float = 15.0,
) -> tuple[int, Any]:
    data = None
    req_headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    req = Request(url, data=data, headers=req_headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            status = resp.status
    except HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        status = e.code
    try:
        payload = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        payload = raw
    return status, payload


def run_smoke(base_url: str, skip_auth: bool) -> list[CheckResult]:
    base = base_url.rstrip("/")
    results: list[CheckResult] = []

    def record(name: str, ok: bool, detail: str) -> None:
        results.append(CheckResult(name=name, ok=ok, detail=detail))
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}: {detail}")

    status, payload = _request("GET", f"{base}/health")
    record(
        "health",
        status == 200 and isinstance(payload, dict) and payload.get("status") in ("healthy", "degraded"),
        f"HTTP {status} {payload}",
    )

    status, payload = _request("GET", f"{base}/api/v1/health")
    record("api_health", status == 200, f"HTTP {status}")

    public_gets = [
        ("categories", "/api/v1/categories"),
        ("discovery", "/api/v1/discovery/hot-goods"),
    ]
    for name, path in public_gets:
        status, payload = _request("GET", f"{base}{path}")
        record(name, status in (200, 401, 403), f"HTTP {status}")

    if skip_auth:
        return results

    suffix = uuid.uuid4().hex[:8]
    email = f"smoke_{suffix}@test.local"
    password = "SmokeTest123!"

    status, payload = _request(
        "POST",
        f"{base}/api/v1/auth/register",
        body={"email": email, "password": password, "nickname": f"smoke_{suffix}"},
    )
    registered = status in (200, 201) or (
        status == 400 and isinstance(payload, dict) and "已注册" in str(payload.get("message", ""))
    )
    record("auth_register", registered, f"HTTP {status}")

    status, payload = _request(
        "POST",
        f"{base}/api/v1/auth/login",
        body={"account": email, "password": password},
    )
    token = None
    if status == 200 and isinstance(payload, dict):
        token = payload.get("access_token")
        if not token:
            data = payload.get("data")
            if isinstance(data, dict):
                token = data.get("access_token")
    record("auth_login", token is not None, f"HTTP {status}")

    if not token:
        return results

    auth_headers = {"Authorization": f"Bearer {token}"}

    for name, path in [
        ("user_profile", "/api/v1/user/profile"),
        ("products_list", "/api/v1/products"),
        ("sync_status", "/api/v1/sync/status"),
        ("monitor_rules", "/api/v1/monitor/rules"),
    ]:
        status, _ = _request("GET", f"{base}{path}", headers=auth_headers)
        record(name, status in (200, 404), f"HTTP {status}")

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="XHS365 API smoke test")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="API base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--skip-auth",
        action="store_true",
        help="Only run public health/category checks",
    )
    args = parser.parse_args()

    print(f"Smoke test target: {args.base_url}\n")
    try:
        results = run_smoke(args.base_url, args.skip_auth)
    except URLError as e:
        print(f"[FAIL] connection: {e}")
        return 1

    failed = [r for r in results if not r.ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
