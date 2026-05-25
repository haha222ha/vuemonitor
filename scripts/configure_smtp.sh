#!/usr/bin/env bash
# Configure NetEase / generic SMTP in server/.env (run on production host only).
#
# One-liner (edit SMTP_PASS and TEST_TO, then paste in SSH):
#   cd /opt/vuemonitor && git fetch origin main && git reset --hard origin/main && \
#   SMTP_PASS='你的授权码' TEST_TO='收件测试邮箱@example.com' bash scripts/configure_smtp.sh
#
# Or interactive (will prompt for authorization code):
#   cd /opt/vuemonitor && bash scripts/configure_smtp.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/server/.env}"

# 网易企业邮：云主机上 587+STARTTLS 常被断开，默认用 SSL 994
SMTP_HOST="${SMTP_HOST:-smtp.qiye.163.com}"
SMTP_PORT="${SMTP_PORT:-994}"
SMTP_USER="${SMTP_USER:-netease@elysys.net}"
SMTP_FROM="${SMTP_FROM:-$SMTP_USER}"
SMTP_USE_TLS="${SMTP_USE_TLS:-false}"
SMTP_USE_SSL="${SMTP_USE_SSL:-true}"
TEST_TO="${TEST_TO:-}"

if [[ -z "${SMTP_PASS:-}" ]]; then
  echo "请输入网易客户端授权码（输入不可见）："
  read -rs SMTP_PASS
  echo
  if [[ -z "$SMTP_PASS" ]]; then
    echo "ERROR: SMTP_PASS 为空"
    exit 1
  fi
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: 找不到 $ENV_FILE"
  exit 1
fi

export ENV_FILE SMTP_HOST SMTP_PORT SMTP_USER SMTP_PASS SMTP_FROM SMTP_USE_TLS SMTP_USE_SSL

python3 <<'PY'
import os
import re
from pathlib import Path

env_path = Path(os.environ["ENV_FILE"])
text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""

updates = {
    "SMTP_HOST": os.environ["SMTP_HOST"],
    "SMTP_PORT": os.environ["SMTP_PORT"],
    "SMTP_USER": os.environ["SMTP_USER"],
    "SMTP_PASSWORD": os.environ["SMTP_PASS"],
    "SMTP_FROM": os.environ["SMTP_FROM"],
    "SMTP_USE_TLS": os.environ["SMTP_USE_TLS"],
    "SMTP_USE_SSL": os.environ["SMTP_USE_SSL"],
}

def env_line(key: str, val: str) -> str:
    # dotenv 会把 $ 当变量展开；密码/含特殊字符的值必须加引号
    if key == "SMTP_PASSWORD" or "$" in val or "%" in val or " " in val:
        escaped = val.replace("'", "'\"'\"'")
        return f"{key}='{escaped}'"
    return f"{key}={val}"


for key, val in updates.items():
    line = env_line(key, val) + "\n"
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    if pattern.search(text):
        text = pattern.sub(line.rstrip(), text)
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text += line

env_path.write_text(text, encoding="utf-8")
print(f"OK: updated SMTP in {env_path}")
for k in updates:
    if k == "SMTP_PASSWORD":
        print(f"  {k}=***")
    else:
        print(f"  {k}={updates[k]}")
PY

echo "Restarting vuemonitor..."
if command -v systemctl >/dev/null 2>&1; then
  sudo systemctl restart vuemonitor
  sleep 3
  curl -sf "http://127.0.0.1:8000/health" >/dev/null && echo "API health OK" || echo "WARN: health check failed, wait and retry"
fi

if [[ -n "$TEST_TO" ]]; then
  echo "Sending test email to $TEST_TO ..."
  (
    cd "$ROOT/server"
    export PYTHONPATH="$ROOT/server"
    "$ROOT/server/.venv/bin/python3" "$ROOT/scripts/test_smtp.py" --to "$TEST_TO"
  ) && echo "Test email sent." \
    || echo "Test send failed — check SMTP_PASSWORD is quoted in .env; journalctl -u vuemonitor -n 30"
else
  echo "Skip test (set TEST_TO=your@email.com to send test mail)"
fi

echo "Done. Run: python3 scripts/audit_runtime.py  (SMTP configured: YES)"
