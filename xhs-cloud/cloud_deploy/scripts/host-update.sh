#!/bin/bash
# 选品云端独立部署 — git pull 后一键更新
# 仓库: https://github.com/haha222ha/vuemonitor  目录: xhs-cloud/
#
# 【服务器一键 — 选品云端】
#   cd /opt/vuemonitor && git fetch origin main && git reset --hard origin/main
#   rsync -a /opt/vuemonitor/xhs-cloud/cloud_deploy/ /opt/xhs-cloud/cloud_deploy/ --delete
#   cd /opt/xhs-cloud && bash cloud_deploy/scripts/host-update.sh
#
# 【vuemonitor 现网 — 不变】
#   cd /opt/vuemonitor && git fetch origin main && git reset --hard origin/main && bash scripts/host-update.sh
#
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

ROOT="${DEPLOY_ROOT:-/opt/xhs-cloud}"
if [ -d "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)" ]; then
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi
cd "$ROOT"

log() { echo -e "  ${CYAN}[*]${NC} $1"; }
ok() { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}!${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; exit 1; }

echo ""
echo "  ========================================"
echo "  |   XHS Monitor 云端更新 (2G 优化)     |"
echo "  ========================================"
echo "  目录: $ROOT"
echo ""

if command -v free &>/dev/null; then
  AVAIL=$(free -m | awk '/^Mem:/{print $7}')
  log "可用内存: ${AVAIL}MB"
  if [ "$AVAIL" -lt 150 ]; then
    warn "内存紧张，跳过非必要步骤"
  fi
fi

ENV_FILE="${XHS_ENV_FILE:-$ROOT/.env}"
if [ ! -f "$ENV_FILE" ]; then
  fail "缺少 $ENV_FILE，请先运行 install.sh"
fi

log "Python 依赖"
if [ ! -x "$ROOT/venv/bin/pip" ]; then
  python3 -m venv "$ROOT/venv"
fi
"$ROOT/venv/bin/pip" install -q -U pip
"$ROOT/venv/bin/pip" install -q -r "$ROOT/cloud_deploy/requirements-cloud.txt"

log "PG schema（若已配置 XHS_DATABASE_URL）"
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
if [[ "${XHS_DATABASE_URL:-}" == postgres* ]]; then
  "$ROOT/venv/bin/python" - <<'PY' || warn "PG init 失败，请检查 XHS_DATABASE_URL"
import os, sys
sys.path.insert(0, os.environ.get("XHS_CLOUD_ROOT", "/opt/xhs-cloud"))
from cloud_deploy.scripts.bootstrap_env import bootstrap
bootstrap()
from cloud_deploy.cloud_api.database import init_db, ensure_admin
init_db()
ensure_admin()
print("PG schema OK")
PY
else
  warn "未配置 XHS_DATABASE_URL，跳过 PG init"
fi

log "systemd"
if [ -d "$ROOT/cloud_deploy/systemd" ]; then
  sudo cp "$ROOT/cloud_deploy/systemd/"*.service /etc/systemd/system/ 2>/dev/null || true
  sudo cp "$ROOT/cloud_deploy/systemd/"*.timer /etc/systemd/system/ 2>/dev/null || true
  sudo systemctl daemon-reload
fi

if systemctl is-enabled xhs-cloud-api.service &>/dev/null; then
  log "重启 xhs-cloud-api"
  sudo systemctl restart xhs-cloud-api.service
else
  warn "xhs-cloud-api 未 enable，跳过 restart"
fi

if systemctl is-enabled xhs-ingest-report.timer &>/dev/null; then
  sudo systemctl restart xhs-ingest-report.timer || true
fi

for t in xhs-daily-report xhs-weekly-report xhs-monthly-report xhs-prune-snapshots; do
  if systemctl is-enabled "${t}.timer" &>/dev/null; then
    sudo systemctl restart "${t}.timer" || true
  fi
done

log "健康检查"
sleep 2
PORT="${XHS_CLOUD_PORT:-8080}"
if curl -sf "http://127.0.0.1:${PORT}/api/v1/health" >/dev/null; then
  ok "API http://127.0.0.1:${PORT}/api/v1/health"
else
  warn "API 未响应，请 systemctl status xhs-cloud-api"
fi

if command -v nginx &>/dev/null && [ -f /etc/nginx/sites-enabled/xhs-monitor.conf ]; then
  sudo nginx -t && sudo systemctl reload nginx && ok "nginx reload"
fi

ok "更新完成"
echo ""
