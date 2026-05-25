#!/usr/bin/env python3
"""Check server/.env for production readiness (SMTP, AI, secrets)."""

from __future__ import annotations

import os
import sys

ENV_PATH = os.environ.get("ENV_FILE", os.path.join(os.path.dirname(os.path.dirname(__file__)), "server", ".env"))


def load_env(path: str) -> dict[str, str]:
    out: dict[str, str] = {}
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def main() -> int:
    env = load_env(ENV_PATH)
    if not env:
        print(f"FAIL: no .env at {ENV_PATH}")
        return 1

    checks: list[tuple[str, object, bool]] = [
        ("JWT_SECRET", lambda v: bool(v) and v != "change-me-in-production", True),
        ("JWT_REFRESH_SECRET", lambda v: bool(v) and "change-me" not in v, True),
        ("ENCRYPTION_KEY", lambda v: len(v) >= 32, True),
        ("DB_PASSWORD", lambda v: bool(v) and v not in ("saas_pass", "changeme"), True),
        ("DEEPSEEK_API_KEY", lambda v: len(v) >= 8, False),
        ("OPENAI_API_KEY", lambda v: len(v) >= 8, False),
        ("SMTP_HOST", lambda v: bool(v), False),
        ("SMTP_USER", lambda v: bool(v), False),
        ("SMTP_PASSWORD", lambda v: bool(v), False),
    ]

    fail = 0
    print(f"Checking {ENV_PATH}\n")
    for key, fn, required in checks:
        val = env.get(key, "")
        ok = fn(val) if val or required else True
        if not val and not required:
            mark = "SKIP"
        elif ok:
            mark = "OK "
        else:
            mark = "MISS"
        if not ok and (required or val):
            fail += 1
        hint = "(set)" if ok and key.endswith("PASSWORD") or key.endswith("KEY") or key.endswith("SECRET") else (val[:20] if ok else "")
        print(f"  {mark} {key} {hint}")

    if fail:
        print(f"\n{fail} item(s) need configuration before full Sprint 1 AI + email.")
        return 1
    print("\nProduction env looks ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
