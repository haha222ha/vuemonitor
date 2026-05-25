#!/usr/bin/env python3
"""XHS365 API golden-path E2E (register -> product -> monitor -> AI)."""

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
class StepResult:
    name: str
    ok: bool
    detail: str


def api(
    method: str,
    base: str,
    path: str,
    *,
    body: dict | None = None,
    token: str | None = None,
    timeout: float = 60.0,
) -> tuple[int, Any]:
    url = f"{base.rstrip('/')}{path}"
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            code = resp.status
    except HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        code = e.code
    try:
        payload = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        payload = raw
    return code, payload


def extract_token(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    if payload.get("access_token"):
        return payload["access_token"]
    data = payload.get("data")
    if isinstance(data, dict) and data.get("access_token"):
        return data["access_token"]
    return None


def run_e2e(base_url: str, skip_ai: bool) -> list[StepResult]:
    base = base_url.rstrip("/")
    results: list[StepResult] = []
    suffix = uuid.uuid4().hex[:8]
    email = f"e2e_{suffix}@test.local"
    password = "E2eTest123!"
    nickname = f"e2e_{suffix}"
    token: str | None = None
    product_id: str | None = None

    def step(name: str, ok: bool, detail: str) -> None:
        results.append(StepResult(name, ok, detail))
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}: {detail}")

    code, payload = api("GET", base, "/health")
    step(
        "health",
        code == 200 and isinstance(payload, dict),
        f"HTTP {code} status={payload.get('status') if isinstance(payload, dict) else payload}",
    )

    code, payload = api(
        "POST",
        base,
        "/api/v1/auth/register",
        body={"email": email, "password": password, "nickname": nickname},
    )
    step("register", code in (200, 201), f"HTTP {code}")

    code, payload = api(
        "POST",
        base,
        "/api/v1/auth/login",
        body={"account": email, "password": password},
    )
    token = extract_token(payload) if code == 200 else None
    step("login", token is not None, f"HTTP {code}")

    if not token:
        return results

    code, payload = api("GET", base, "/api/v1/user/profile", token=token)
    step("profile", code == 200, f"HTTP {code}")

    code, payload = api(
        "POST",
        base,
        "/api/v1/products",
        token=token,
        body={
            "platform": "xhs",
            "platform_product_id": f"e2e{suffix}",
            "product_name": f"E2E商品{suffix}",
        },
    )
    if code == 201 and isinstance(payload, dict):
        data = payload.get("data") or {}
        product_id = data.get("id") if isinstance(data, dict) else None
    step("create_product", product_id is not None, f"HTTP {code} id={product_id}")

    if product_id:
        code, _ = api(
            "POST",
            base,
            "/api/v1/monitor/rules",
            token=token,
            body={
                "product_id": product_id,
                "rule_name": "E2E价格监控",
                "rule_type": "price_drop",
                "conditions": {"threshold_percent": 10},
            },
        )
        step("create_monitor_rule", code == 201, f"HTTP {code}")

        if not skip_ai:
            code, payload = api(
                "POST",
                base,
                "/api/v1/ai/analyze",
                token=token,
                body={
                    "product_id": product_id,
                    "analysis_type": "basic_analysis",
                },
                timeout=120.0,
            )
            ok = code == 200 and isinstance(payload, dict) and payload.get("code") == 0
            step("ai_basic_analysis", ok, f"HTTP {code}")
        else:
            step("ai_basic_analysis", True, "skipped")

    code, _ = api("GET", base, "/api/v1/sync/status", token=token)
    step("sync_status", code in (200, 404), f"HTTP {code}")

    code, _ = api("GET", base, "/api/v1/monitor/notifications", token=token)
    step("notifications", code == 200, f"HTTP {code}")

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="XHS365 API E2E golden path")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--skip-ai", action="store_true", help="Skip AI analyze (no API key)")
    args = parser.parse_args()

    print(f"E2E target: {args.base_url}\n")
    try:
        results = run_e2e(args.base_url, args.skip_ai)
    except URLError as e:
        print(f"[FAIL] connection: {e}")
        return 1

    failed = [r for r in results if not r.ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
