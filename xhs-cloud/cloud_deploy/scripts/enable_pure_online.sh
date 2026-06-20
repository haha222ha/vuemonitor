#!/bin/bash
# 纯线上全自动 — 一键启用（禁用混合模式 ingest，开启 daemon + 日/周/月报 timer）
#
# 前置：
#   1. /opt/xhs-cloud/.env 已配置（bootstrap_from_vuemonitor.sh）
#   2. 爬虫已部署到 XHS_CRAWLER_ROOT（含 xhs_full_sold_fetch.py）
#   3. PG schema 已初始化
#
# 用法：
#   bash /opt/xhs-cloud/cloud_deploy/scripts/enable_pure_online.sh
#
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

ROOT="${XHS_CLOUD_ROOT:-/opt/xhs-cloud}"
ENV_FILE="${XHS_ENV_FILE:-$ROOT/.env}"

log() { echo -e "  ${CYAN}[*]${NC} $1"; }
ok() { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}!${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; exit 1; }

echo ""
echo "  ========================================"
echo "  |   选品云 · 纯线上全自动 启用          |"
echo "  ========================================"
echo ""

[[ -f "$ENV_FILE" ]] || fail "缺少 $ENV_FILE，请先运行 bootstrap_from_vuemonitor.sh"

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

CRAWLER="${XHS_CRAWLER_ROOT:-/opt/xhs/crawler}"
[[ -d "$CRAWLER" ]] || warn "爬虫目录不存在: $CRAWLER（请上传后编辑 .env 中 XHS_CRAWLER_ROOT）"

log "检查 PG 连接"
"$ROOT/venv/bin/python" - <<'PY' || fail "PG 不可用，请检查 XHS_DATABASE_URL"
import os, sys
sys.path.insert(0, os.environ.get("XHS_CLOUD_ROOT", "/opt/xhs-cloud"))
from cloud_deploy.scripts.bootstrap_env import bootstrap
bootstrap()
from cloud_deploy.cloud_api.database import init_db
init_db()
print("PG OK")
PY
ok "PostgreSQL xhs_monitor schema"

log "检查 ⑥补缺挂机模块"
FETCH_OK=$("$ROOT/venv/bin/python" - <<PY 2>/dev/null || true
import os, sys
crawler = os.environ.get("XHS_CRAWLER_ROOT", "${CRAWLER}")
if crawler and os.path.isdir(crawler):
    sys.path.insert(0, crawler)
try:
    from xhs_full_sold_daemon import FullSoldSyncDaemon
    from xhs_full_sold_fetch import fetch_sold_detail, ENGINE_CHAIN
    print("OK", ENGINE_CHAIN)
except ImportError as e:
    print("MISSING", e)
PY
)
if [[ "$FETCH_OK" != OK* ]]; then
  warn "未找到 ⑥补缺挂机模块（xhs_full_sold_daemon / xhs_full_sold_fetch）"
  warn "请将 Windows 爬虫目录上传到 $CRAWLER，例如："
  warn "  scp -r D:\\jiekoufenxi\\小红书多设备爬虫\\* admin@服务器:/opt/xhs/crawler/"
  read -r -p "  仍要继续启用 timer（稍后补爬虫）？[y/N] " ans
  [[ "${ans,,}" == "y" ]] || exit 1
else
  ok "⑥补缺挂机可用 引擎链=${FETCH_OK#OK }"
fi

log "禁用混合模式 ingest timer"
if systemctl is-enabled xhs-ingest-report.timer &>/dev/null; then
  sudo systemctl disable --now xhs-ingest-report.timer || true
  ok "已关闭 xhs-ingest-report.timer"
else
  ok "xhs-ingest-report.timer 未启用（跳过）"
fi

log "启用纯线上服务"
UNITS=(
  xhs-cloud-api.service
  xhs-daemon.service
  xhs-daily-report.timer
  xhs-weekly-report.timer
  xhs-monthly-report.timer
  xhs-prune-snapshots.timer
)
for u in "${UNITS[@]}"; do
  sudo systemctl enable "$u"
done
sudo systemctl restart xhs-cloud-api.service
sudo systemctl restart xhs-daemon.service || warn "xhs-daemon 启动失败，检查 journalctl -u xhs-daemon"
for t in xhs-daily-report xhs-weekly-report xhs-monthly-report xhs-prune-snapshots; do
  sudo systemctl restart "${t}.timer" || true
done
ok "systemd 已配置"

echo ""
log "定时任务一览"
systemctl list-timers --no-pager 'xhs-*' 2>/dev/null || systemctl list-timers --no-pager | grep xhs || true

echo ""
log "健康检查"
sleep 2
PORT="${XHS_CLOUD_PORT:-8080}"
curl -sf "http://127.0.0.1:${PORT}/api/v1/health" && ok "API :${PORT} 正常" || warn "API 未响应"

echo ""
echo "  ── 纯线上流水线 ──"
echo "  24h  xhs-daemon (⑥补缺挂机) → API 多引擎扫池，写 PG"
echo "  17:00 xhs-daily-report → PG 生成日报 + zip（每天）"
echo "  周日 17:00             → 周报 zip"
echo "  每月1日 17:00          → 月报 zip"
echo "  03:30 xhs-prune        → 清理 90 天快照"
echo ""
echo "  会员下载: https://monitor.xhs365.cn/member"
echo ""
warn "首次运行建议先导入历史监控池（一次性）："
echo "  import_historical_reports.py + import_monitor_pool_offline.py"
echo "  详见 xhs-cloud/docs/DEPLOY_CHECKLIST.md 第三节"
echo ""
ok "纯线上全自动已启用"
