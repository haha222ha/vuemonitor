#!/usr/bin/env python3
"""
Runtime audit: AI providers + admin account (run on production host).
Does not print secret values.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = Path(os.environ.get("ENV_FILE", ROOT / "server" / ".env"))
API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000").rstrip("/")


def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if not ENV_PATH.is_file():
        return out
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def http_get(path: str, token: str | None = None) -> tuple[int, dict | str | None]:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(f"{API_BASE}{path}", headers=headers, method="GET")
    try:
        with urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else None
    except Exception as e:
        return 0, str(e)


def http_post(path: str, body: dict, token: str | None = None) -> tuple[int, dict | str | None]:
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(f"{API_BASE}{path}", data=data, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else None
    except Exception as e:
        return 0, str(e)


def mask(s: str) -> str:
    if not s:
        return "(empty)"
    if len(s) <= 8:
        return "***"
    return f"{s[:4]}...{s[-4:]}"


async def audit_db_admin() -> None:
    sys.path.insert(0, str(ROOT / "server"))
    os.environ.setdefault("PYTHONPATH", str(ROOT / "server"))

    from sqlalchemy import func, select

    from app.core.database import async_session_factory, init_db
    from app.models.user import User

    await init_db()
    async with async_session_factory() as db:
        count = await db.execute(
            select(func.count()).select_from(User).where(User.role == "admin", User.is_active.is_(True))
        )
        n = count.scalar() or 0
        print(f"  DB admin users (active): {n}")
        if n > 0:
            result = await db.execute(
                select(User.email, User.nickname, User.plan).where(User.role == "admin").limit(5)
            )
            for email, nick, plan in result.all():
                print(f"    - email={email or '(none)'} nickname={nick} plan={plan}")


def main() -> int:
    print("========== XHS365 Runtime Audit ==========\n")
    env = load_env()
    print(f"Env file: {ENV_PATH} ({'found' if env else 'MISSING'})\n")

    print("--- AI configuration (.env, masked) ---")
    ds = env.get("DEEPSEEK_API_KEY", "")
    oa = env.get("OPENAI_API_KEY", "")
    print(f"  DEEPSEEK_API_KEY: {'SET ' + mask(ds) if ds else 'MISSING'}")
    print(f"  DEEPSEEK_MODEL: {env.get('DEEPSEEK_MODEL', 'deepseek-v4-flash')}")
    print(f"  AI_DEFAULT_PROVIDER: {env.get('AI_DEFAULT_PROVIDER', 'deepseek')}")
    print(f"  OPENAI_API_KEY: {'SET ' + mask(oa) if oa else 'MISSING'}")
    print(f"  DeepSeek base_url (code): https://www.packyapi.com/v1")

    print("\n--- AI runtime API ---")
    code, payload = http_get("/api/v1/ai/status")
    if code == 200 and isinstance(payload, dict):
        data = payload.get("data") or payload
        print(f"  GET /ai/status HTTP {code}")
        print(f"    ai_enabled: {data.get('ai_enabled')}")
        print(f"    available_providers: {data.get('available_providers')}")
        print(f"    default_provider: {data.get('default_provider')}")
        types = data.get("analysis_types") or []
        print(f"    analysis_types: {len(types)} types")
        if not data.get("ai_enabled"):
            print("  WARN: ai_enabled=false — DEEPSEEK/OPENAI key not loaded by running process")
            print("        Restart: sudo systemctl restart vuemonitor")
    else:
        print(f"  FAIL /ai/status HTTP {code} {payload}")

    print("\n--- Admin ---")
    admin_email = env.get("ADMIN_EMAIL") or os.environ.get("ADMIN_EMAIL", "admin@xhs365.cn")
    admin_pass = env.get("ADMIN_PASSWORD") or os.environ.get("ADMIN_PASSWORD", "")
    print(f"  Test login email: {admin_email}")
    if admin_pass:
        code, payload = http_post("/api/v1/admin/login", {"username": admin_email, "password": admin_pass})
        ok = code == 200 and isinstance(payload, dict) and payload.get("access_token")
        print(f"  POST /admin/login: {'OK' if ok else 'FAIL'} HTTP {code}")
    else:
        print("  POST /admin/login: SKIP (set ADMIN_PASSWORD in env or pass for test)")

    try:
        import asyncio

        print("\n--- Admin DB ---")
        asyncio.run(audit_db_admin())
    except Exception as e:
        print(f"  DB check skipped: {e}")

    print("\n--- SMTP (.env) ---")
    smtp_ok = bool(env.get("SMTP_HOST") and env.get("SMTP_USER") and env.get("SMTP_PASSWORD"))
    print(f"  SMTP configured: {'YES' if smtp_ok else 'NO (email codes log-only)'}")

    print("\n========== Summary ==========")
    ai_ok = bool(ds or oa)
    if ai_ok:
        print("AI keys present in .env. Confirm ai_enabled=true above after restart.")
    else:
        print("AI keys missing in .env file.")
    print("Admin: use DB list + admin login test above.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
