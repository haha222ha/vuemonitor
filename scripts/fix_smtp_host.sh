#!/usr/bin/env bash
# Fix SMTP on host without full git reset (NetEase 994 + quoted password).
# Usage:
#   SMTP_PASS='授权码' TEST_TO='you@qq.com' bash scripts/fix_smtp_host.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/server/.env}"

SMTP_HOST="${SMTP_HOST:-smtp.qiye.163.com}"
SMTP_PORT="${SMTP_PORT:-994}"
SMTP_USER="${SMTP_USER:-netease@elysys.net}"
SMTP_FROM="${SMTP_FROM:-$SMTP_USER}"
SMTP_USE_TLS="${SMTP_USE_TLS:-false}"
SMTP_USE_SSL="${SMTP_USE_SSL:-true}"
TEST_TO="${TEST_TO:-}"

[[ -n "${SMTP_PASS:-}" ]] || { echo "ERROR: set SMTP_PASS='...'"; exit 1; }

export ENV_FILE SMTP_HOST SMTP_PORT SMTP_USER SMTP_PASS SMTP_FROM SMTP_USE_TLS SMTP_USE_SSL

python3 <<'PY'
import os, re
from pathlib import Path

def env_line(key: str, val: str) -> str:
    if key == "SMTP_PASSWORD" or "$" in val or "%" in val:
        escaped = val.replace("'", "'\"'\"'")
        return f"{key}='{escaped}'"
    return f"{key}={val}"

p = Path(os.environ["ENV_FILE"])
text = p.read_text(encoding="utf-8") if p.exists() else ""
updates = {
    "SMTP_HOST": os.environ["SMTP_HOST"],
    "SMTP_PORT": os.environ["SMTP_PORT"],
    "SMTP_USER": os.environ["SMTP_USER"],
    "SMTP_PASSWORD": os.environ["SMTP_PASS"],
    "SMTP_FROM": os.environ["SMTP_FROM"],
    "SMTP_USE_TLS": os.environ["SMTP_USE_TLS"],
    "SMTP_USE_SSL": os.environ["SMTP_USE_SSL"],
}
for key, val in updates.items():
    line = env_line(key, val)
    pat = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    text = pat.sub(line, text) if pat.search(text) else text + ("\n" if text and not text.endswith("\n") else "") + line + "\n"
p.write_text(text, encoding="utf-8")
print("OK:", p)
for k, v in updates.items():
    print(f"  {k}={'***' if k == 'SMTP_PASSWORD' else v}")
PY

sudo systemctl restart vuemonitor 2>/dev/null || true
sleep 4

if [[ -n "$TEST_TO" ]]; then
  cd "$ROOT/server"
  export PYTHONPATH="$ROOT/server"
  "$ROOT/server/.venv/bin/python3" "$ROOT/scripts/test_smtp.py" --to "$TEST_TO" || true
fi

echo "Done."
