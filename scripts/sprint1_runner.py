#!/usr/bin/env python3
"""Sprint 1 (P0): monetization path — register, products, monitor, AI, refresh."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from typing import Any

# Reuse e2e helpers
sys.path.insert(0, os.path.dirname(__file__))
from e2e_api_flow import api, extract_token, StepResult  # noqa: E402


def run_sprint1(base: str, run_ai: bool) -> list[StepResult]:
    results: list[StepResult] = []
    suffix = uuid.uuid4().hex[:8]
    email = f"s1_{suffix}@test.local"
    password = "Sprint1Test123!"
    nickname = f"s1user_{suffix}"
    token: str | None = None
    refresh: str | None = None
    product_id: str | None = None

    def step(name: str, ok: bool, detail: str) -> None:
        results.append(StepResult(name, ok, detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")

    # E-1 register / login / profile / refresh
    code, _ = api("POST", base, "/api/v1/auth/register", body={"email": email, "password": password, "nickname": nickname})
    step("E1_register", code in (200, 201), f"HTTP {code}")

    code, payload = api("POST", base, "/api/v1/auth/login", body={"account": nickname, "password": password})
    token = extract_token(payload) if code == 200 else None
    refresh = payload.get("refresh_token") if isinstance(payload, dict) else None
    step("E1_login", token is not None, f"HTTP {code}")

    if not token:
        return results

    code, _ = api("GET", base, "/api/v1/user/profile", token=token)
    step("E1_profile", code == 200, f"HTTP {code}")

    if refresh:
        code, payload = api("POST", base, "/api/v1/auth/refresh", body={"refresh_token": refresh})
        new_token = extract_token(payload) if code == 200 else None
        step("E1_token_refresh", new_token is not None, f"HTTP {code}")
        if new_token:
            token = new_token

    # E-2 products
    code, payload = api(
        "POST",
        base,
        "/api/v1/products",
        token=token,
        body={"platform": "xhs", "platform_product_id": f"s1{suffix}", "product_name": f"S1商品{suffix}"},
    )
    if code == 201 and isinstance(payload, dict):
        data = payload.get("data") or {}
        product_id = data.get("id") if isinstance(data, dict) else None
    step("E2_create_product", product_id is not None, f"HTTP {code}")

    code, _ = api("GET", base, "/api/v1/products", token=token)
    step("E2_list_products", code == 200, f"HTTP {code}")

    if product_id:
        code, _ = api("GET", base, f"/api/v1/products/{product_id}", token=token)
        step("E2_product_detail", code == 200, f"HTTP {code}")

    # E-5 monitor
    if product_id:
        code, _ = api(
            "POST",
            base,
            "/api/v1/monitor/rules",
            token=token,
            body={
                "product_id": product_id,
                "rule_name": "S1价格监控",
                "rule_type": "price_drop",
                "conditions": {"threshold_percent": 5},
            },
        )
        step("E5_create_rule", code == 201, f"HTTP {code}")

        code, _ = api("GET", base, "/api/v1/monitor/rules", token=token)
        step("E5_list_rules", code == 200, f"HTTP {code}")

        code, _ = api("GET", base, "/api/v1/monitor/notifications", token=token)
        step("E5_notifications", code == 200, f"HTTP {code}")

        code, _ = api("GET", base, "/api/v1/alert-rules", token=token)
        step("E5_alert_rules", code in (200, 404), f"HTTP {code}")

    # E-4 AI
    if product_id and run_ai:
        code, payload = api(
            "POST",
            base,
            "/api/v1/ai/analyze",
            token=token,
            body={"product_id": product_id, "analysis_type": "basic_analysis"},
            timeout=120.0,
        )
        ok = code == 200 and isinstance(payload, dict) and payload.get("code") == 0
        step("E4_ai_basic", ok, f"HTTP {code}")
    elif product_id:
        code, _ = api("GET", base, "/api/v1/ai/status", token=token)
        step("E4_ai_status", code == 200, f"HTTP {code} (AI analyze skipped)")

    code, _ = api("GET", base, "/api/v1/categories", token=token)
    step("E2_categories", code in (200, 401), f"HTTP {code}")

    return results


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--run-ai", action="store_true")
    args = p.parse_args()
    print(f"Sprint 1 @ {args.base_url}\n")
    results = run_sprint1(args.base_url.rstrip("/"), args.run_ai)
    failed = [r for r in results if not r.ok]
    print(f"\nSprint1: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
