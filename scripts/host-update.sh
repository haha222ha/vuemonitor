#!/bin/bash
# XHS365 主机一键更新 — 针对 2G RAM / 2 CPU（git pull 部署，不在服务器上 npm build）
#
# 【主机一键命令，复制这一行即可】
#   cd /opt/vuemonitor && git fetch origin main && git reset --hard origin/main && bash scripts/host-update.sh
#
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

ROOT="${DEPLOY_ROOT:-/opt/vuemonitor}"
if [ -d "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" ]; then
  ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi
cd "$ROOT"

log() { echo -e "  ${CYAN}[*]${NC} $1"; }
ok() { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}!${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; exit 1; }

echo ""
echo "  ========================================"
echo "  |   XHS365 主机更新 (2G 优化版)        |"
echo "  ========================================"
echo "  目录: $ROOT"
echo ""

# --- 内存保护：可用内存过低时先释放缓存 ---
if command -v free &>/dev/null; then
  AVAIL=$(free -m | awk '/^Mem:/{print $7}')
  log "可用内存: ${AVAIL}MB"
  if [ "$AVAIL" -lt 180 ]; then
    warn "内存紧张，尝试释放 page cache"
    sync 2>/dev/null || true
    echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null 2>&1 || true
  fi
fi

# --- 1. 拉取代码 ---
log "拉取最新代码 (origin/main)..."
git fetch origin main
BEFORE=$(git rev-parse HEAD)
git reset --hard origin/main
AFTER=$(git rev-parse HEAD)
if [ "$BEFORE" = "$AFTER" ]; then
  ok "代码已是最新 ($AFTER)"
else
  ok "代码已更新 $BEFORE -> $AFTER"
fi

# --- 2. 校验预构建前端（必须在本地/CI 构建后 push）---
for app in web-user web-admin web-intel; do
  if [ ! -f "$ROOT/$app/dist/index.html" ]; then
    fail "$app/dist/index.html 不存在。请在开发机运行: scripts/local-release.ps1 后 push"
  fi
done
ok "前端 dist 已就绪 (user/admin/intel)"

# --- 3. Python 依赖 + 迁移（轻量安装，避免 OOM）---
log "更新 Python 依赖..."
cd "$ROOT/server"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
export PIP_NO_CACHE_DIR=1
pip install -q -r requirements.txt
ok "Python 依赖已更新"

log "数据库迁移..."
export PYTHONPATH="$ROOT/server"
alembic upgrade head
ok "Alembic 迁移完成"

# --- 4. 重启服务（2G 建议单 worker，见 deploy/systemd）---
log "重启 API 服务..."
if systemctl is-active --quiet vuemonitor 2>/dev/null; then
  sudo systemctl restart vuemonitor
  ok "systemctl restart vuemonitor"
elif command -v docker &>/dev/null && [ -f "$ROOT/docker-compose.prod.yml" ]; then
  warn "未检测到 vuemonitor systemd，尝试 Docker（低内存模式）"
  export UVICORN_WORKERS=1
  COMPOSE="docker compose"
  command -v docker-compose &>/dev/null && COMPOSE="docker-compose"
  $COMPOSE -f docker-compose.prod.yml up -d --no-build --remove-orphans server postgres redis web-intel 2>/dev/null \
    || $COMPOSE -f docker-compose.yml up -d --no-build server postgres redis
  ok "Docker 服务已拉起"
else
  fail "未找到 vuemonitor 服务或 docker compose，请检查部署方式"
fi

if systemctl is-active --quiet nginx 2>/dev/null; then
  sudo nginx -t && sudo systemctl reload nginx
  ok "Nginx 已 reload"
fi

# --- 5. 健康检查 ---
log "健康检查..."
sleep 3
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000/health}"
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" || echo "000")
if [ "$CODE" = "200" ]; then
  ok "API health HTTP $CODE"
else
  fail "API health HTTP $CODE — 查看: journalctl -u vuemonitor -n 50 --no-pager"
fi

if [ -f "$ROOT/scripts/api_smoke.py" ]; then
  python3 "$ROOT/scripts/api_smoke.py" --base-url "${SMOKE_BASE:-http://127.0.0.1:8000}" --skip-auth || warn "冒烟部分失败（可忽略若仅缺外网）"
fi

echo ""
echo -e "  ${GREEN}更新完成${NC}"
echo "  提交: $(git log -1 --oneline)"
echo ""
