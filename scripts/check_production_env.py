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

    checks = [
        ("JWT_SECRET", lambda v: bool(v) and v != "change-me-in-production"),
        ("JWT_REFRESH_SECRET", lambda v: bool(v) and "change-me" not in v),
        ("ENCRYPTION_KEY", lambda v: len(v) >= 32),
        ("DB_PASSWORD", lambda v: bool(v) and v not in ("saas_pass", "changeme")),
        ("DEEPSEEK_API_KEY", lambda v: v.startswith("sk-") or len(v) > 20),
        ("SMTP_HOST", lambda v: bool(v)),
        ("SMTP_USER", lambda v: bool(v)),
        ("SMTP_PASSWORD", lambda v: bool(v)),
    ]

    fail = 0
    print(f"Checking {ENV_PATH}\n")
    for key, fn in checks:
        val = env.get(key, "")
        ok = fn(val)
        mark = "OK " if ok else "MISS"
        if not ok:
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
