#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W1-5：Shadow 验收冒烟 — profile / insight library / view

用法（云主机）:
  export XHS_MEMBER_TOKEN='eyJ...'   # 见下方「Token 从哪来」
  python3 /opt/xhs-cloud/cloud_deploy/scripts/insight_shadow_smoke.py

或账号登录:
  export XHS_SMOKE_USER='你的用户名'
  export XHS_SMOKE_PASS='你的密码'
  python3 cloud_deploy/scripts/insight_shadow_smoke.py

期望 persona（可选校验）:
  export XHS_SMOKE_EXPECT=legacy_dual   # legacy_dual | insight_only | auto
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import uuid

ROOT = os.environ.get("XHS_CLOUD_ROOT", "/opt/xhs-cloud")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

BASE = os.environ.get("XHS_SMOKE_BASE", "http://127.0.0.1:8080").rstrip("/")
EXPECT = (os.environ.get("XHS_SMOKE_EXPECT") or "auto").strip().lower()

PASS = 0
FAIL = 0


def _log(ok: bool, name: str, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [PASS] {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  [FAIL] {name}" + (f" — {detail}" if detail else ""))


def _request(method: str, path: str, *, token: str | None = None, body: dict | None = None) -> tuple[int, dict]:
    url = f"{BASE}{path}"
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"detail": raw[:300]}


def _login() -> str:
    token = (os.environ.get("XHS_MEMBER_TOKEN") or os.environ.get("XHS_SMOKE_TOKEN") or "").strip()
    if token:
        return token
    user = (os.environ.get("XHS_SMOKE_USER") or "").strip()
    password = (os.environ.get("XHS_SMOKE_PASS") or "").strip()
    if not user or not password:
        print(
            "缺少 Token。任选其一:\n"
            "  1) export XHS_MEMBER_TOKEN=...  （浏览器 localStorage xhs_member_token）\n"
            "  2) export XHS_SMOKE_USER=... XHS_SMOKE_PASS=...\n",
            file=sys.stderr,
        )
        sys.exit(2)
    code, data = _request(
        "POST",
        "/api/v1/auth/login",
        body={
            "username": user,
            "password": password,
            "device_id": f"smoke:{uuid.uuid4().hex[:12]}",
            "device_label": "insight_shadow_smoke",
        },
    )
    if code != 200:
        print(f"登录失败 HTTP {code}: {data}", file=sys.stderr)
        sys.exit(2)
    token = (data.get("access_token") or "").strip()
    if not token:
        print("登录响应无 access_token", file=sys.stderr)
        sys.exit(2)
    print(f"  [info] 已登录 user={user}")
    return token


def _check_persona(profile: dict) -> None:
    insight = bool(profile.get("insight_enabled"))
    legacy = bool(profile.get("legacy_zip_enabled"))
    route = str(profile.get("portal_route") or "")
    plan = str(profile.get("plan_code") or "")

    if EXPECT == "auto":
        _log(insight, "profile.insight_enabled", str(insight))
        _log(legacy or not insight, "profile.legacy_zip 与 insight 组合合法", f"route={route} plan={plan}")
        return

    if EXPECT == "legacy_dual":
        _log(insight and legacy, "legacy_dual: insight+legacy", f"route={route}")
        _log(route == "legacy_dual", "portal_route=legacy_dual", route)
    elif EXPECT == "insight_only":
        _log(insight and not legacy, "insight_only: 仅 AI", f"route={route}")
        _log(route == "insight_only", "portal_route=insight_only", route)
    else:
        _log(False, "未知 XHS_SMOKE_EXPECT", EXPECT)


def main() -> int:
    print(f"Insight Shadow Smoke @ {BASE}")
    print(f"  expect persona: {EXPECT}")

    code, health = _request("GET", "/api/v1/health")
    _log(code == 200 and health.get("status") == "ok", "health", str(health))

    token = _login()

    code, profile = _request("GET", "/api/v1/member/profile", token=token)
    _log(code == 200, "GET /member/profile", f"HTTP {code}")
    if code != 200:
        print(json.dumps(profile, ensure_ascii=False, indent=2))
        return 1

    print(
        "  profile:",
        json.dumps(
            {
                k: profile.get(k)
                for k in ("username", "plan_code", "insight_enabled", "legacy_zip_enabled", "portal_route")
            },
            ensure_ascii=False,
        ),
    )
    _check_persona(profile)

    code, lib = _request("GET", "/api/v1/member/insight/library", token=token)
    items = lib.get("items") or []
    _log(code == 200, "GET /member/insight/library", f"items={len(items)}")
    if code == 200:
        shadow = lib.get("shadow_mode")
        _log(shadow is True or len(items) > 0, "shadow 库有数据或 shadow_mode", f"shadow={shadow}")

    if items:
        first = items[0]
        date = str(first.get("report_date") or "")[:10]
        cat = first.get("category") or ""
        view_path = f"/api/v1/member/insight/{date}/{cat}/view?access_token={token}"
        vcode, _ = _request("GET", view_path)
        _log(vcode == 200, "GET insight view HTML", f"{date}/{cat} HTTP {vcode}")
    else:
        _log(False, "insight library 非空", "请先跑 run_insight_report_shadow.sh")

    print("")
    print(f"Result: {PASS} passed, {FAIL} failed")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
