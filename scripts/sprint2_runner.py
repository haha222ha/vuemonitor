#!/usr/bin/env python3
"""Sprint 2 (P1): sync loop, license activation, discovery."""

from __future__ import annotations

import argparse
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(__file__))
from e2e_api_flow import api, extract_token, StepResult  # noqa: E402


def run_sprint2(
    base: str,
    admin_email: str,
    admin_password: str,
) -> list[StepResult]:
    results: list[StepResult] = []
    suffix = uuid.uuid4().hex[:8]
    nickname = f"s2_{suffix}"
    password = "Sprint2Test123!"
    token: str | None = None
    product_id: str | None = None
    license_code: str | None = None

    def step(name: str, ok: bool, detail: str) -> None:
        results.append(StepResult(name, ok, detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")

    # User setup
    code, _ = api(
        "POST",
        base,
        "/api/v1/auth/register",
        body={"nickname": nickname, "password": password},
    )
    step("S2_register", code in (200, 201), f"HTTP {code}")

    code, payload = api("POST", base, "/api/v1/auth/login", body={"account": nickname, "password": password})
    token = extract_token(payload) if code == 200 else None
    step("S2_login", token is not None, f"HTTP {code}")
    if not token:
        return results

    code, payload = api(
        "POST",
        base,
        "/api/v1/products",
        token=token,
        body={"platform": "xhs", "platform_product_id": f"s2{suffix}", "product_name": f"S2同步测试{suffix}"},
    )
    if code == 201 and isinstance(payload, dict):
        data = payload.get("data") or {}
        product_id = data.get("id") if isinstance(data, dict) else None
    step("S2_product", product_id is not None, f"HTTP {code}")

    # E-10 sync
    code, payload = api("GET", base, "/api/v1/sync/status", token=token)
    step("E10_sync_status", code == 200, f"HTTP {code}")

    if product_id:
        code, payload = api(
            "POST",
            base,
            "/api/v1/sync/push",
            token=token,
            body={
                "platform": "xhs",
                "platform_product_id": f"s2{suffix}",
                "features": [{"price": 99.0, "sales_count": 100, "source": "e2e_test"}],
            },
        )
        ok = code == 200 and isinstance(payload, dict) and payload.get("code") == 0
        step("E10_sync_push", ok, f"HTTP {code}")

        code, payload = api(
            "POST",
            base,
            "/api/v1/sync/pull",
            token=token,
            body={"product_id": product_id},
        )
        ok = code == 200 and isinstance(payload, dict)
        step("E10_sync_pull", ok, f"HTTP {code}")

        code, payload = api(
            "POST",
            base,
            "/api/v1/sync/batch-push",
            token=token,
            body={"products": [], "features": [], "categories": [], "deletions": []},
        )
        ok = code == 200 and isinstance(payload, dict)
        step("E10_batch_push", ok, f"HTTP {code}")

    # E-9 discovery (auth required)
    code, _ = api("GET", base, "/api/v1/discovery/hot-goods", token=token)
    step("E9_discovery", code in (200, 503), f"HTTP {code}")

    # E-6 license — admin generates, user activates
    code, payload = api(
        "POST",
        base,
        "/api/v1/admin/login",
        body={"username": admin_email, "password": admin_password},
    )
    admin_token = payload.get("access_token") if isinstance(payload, dict) and code == 200 else None
    step("E6_admin_login", admin_token is not None, f"HTTP {code}")

    if admin_token:
        code, payload = api(
            "POST",
            base,
            "/api/v1/admin/licenses/generate",
            token=admin_token,
            body={"plan": "pro", "duration_days": 30, "count": 1},
        )
        if code == 200 and isinstance(payload, dict):
            data = payload.get("data") or {}
            codes = data.get("codes") if isinstance(data, dict) else None
            if codes and len(codes) > 0:
                license_code = codes[0]
        step("E6_generate_license", license_code is not None, f"HTTP {code} code={license_code}")

    if license_code and token:
        code, payload = api(
            "POST",
            base,
            "/api/v1/license/activate",
            token=token,
            body={
                "license_key": license_code,
                "device_fingerprint": f"e2e-device-{suffix}",
                "device_name": "E2E Test",
            },
        )
        ok = code == 200 and isinstance(payload, dict) and payload.get("code") == 0
        step("E6_activate_license", ok, f"HTTP {code}")

        code, _ = api("GET", base, "/api/v1/user/profile", token=token)
        step("E6_profile_after_license", code == 200, f"HTTP {code}")

    return results


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--admin-email", default=os.environ.get("ADMIN_EMAIL", "admin@xhs365.cn"))
    p.add_argument("--admin-password", default=os.environ.get("ADMIN_PASSWORD", "Admin123!ChangeMe"))
    args = p.parse_args()
    print(f"Sprint 2 @ {args.base_url}\n")
    results = run_sprint2(args.base_url.rstrip("/"), args.admin_email, args.admin_password)
    failed = [r for r in results if not r.ok]
    print(f"\nSprint2: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
