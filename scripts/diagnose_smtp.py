#!/usr/bin/env python3
"""Try NetEase SMTP host/port combos (run on host: cd server && PYTHONPATH=. ../scripts/diagnose_smtp.py)."""

from __future__ import annotations

import os
import smtplib
import ssl
import sys
from pathlib import Path

SERVER = Path(__file__).resolve().parent.parent / "server"
os.chdir(SERVER)
sys.path.insert(0, str(SERVER))

# Load server/.env without pydantic ($ in password safe)
env: dict[str, str] = {}
for line in (SERVER / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    v = v.strip()
    if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
        v = v[1:-1]
    env[k.strip()] = v

user = env.get("SMTP_USER", "")
pwd = env.get("SMTP_PASSWORD", "")
if not user or not pwd:
    print("ERROR: SMTP_USER / SMTP_PASSWORD missing in server/.env")
    sys.exit(1)

print(f"SMTP_USER={user}")
print(f"SMTP_PASSWORD len={len(pwd)} (first char: {pwd[:1]!r})")
print()

candidates = [
    ("smtp.qiye.163.com", 994, "ssl"),
    ("smtp.qiye.163.com", 465, "ssl"),
    ("smtphz.qiye.163.com", 994, "ssl"),
    ("smtphz.qiye.163.com", 465, "ssl"),
    ("smtp.qiye.163.com", 587, "starttls"),
]

ctx = ssl.create_default_context()
for host, port, mode in candidates:
    label = f"{host}:{port} ({mode})"
    try:
        if mode == "ssl":
            with smtplib.SMTP_SSL(host, port, timeout=20, context=ctx) as s:
                s.ehlo()
                s.login(user, pwd)
        else:
            with smtplib.SMTP(host, port, timeout=20) as s:
                s.ehlo()
                s.starttls(context=ctx)
                s.ehlo()
                s.login(user, pwd)
        print(f"OK  {label}")
    except Exception as e:
        print(f"FAIL {label} -> {type(e).__name__}: {e}")
