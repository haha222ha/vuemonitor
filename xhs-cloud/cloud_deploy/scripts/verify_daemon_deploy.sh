#!/bin/bash
# 确认 xhs-daemon 已部署为新配置（gap_only / 500 / 120s / 无 risk 全池）
set -euo pipefail

ROOT="${XHS_CLOUD_ROOT:-/opt/xhs-cloud}"
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

ok() { echo -e "  ${GREEN}✓${NC} $1"; }
bad() { echo -e "  ${RED}✗${NC} $1"; FAIL=1; }
info() { echo -e "  ${CYAN}·${NC} $1"; }

FAIL=0
echo ""
echo "=== xhs-daemon 部署校验 ==="

if systemctl is-active --quiet xhs-daemon; then
  ok "xhs-daemon 运行中"
else
  bad "xhs-daemon 未运行 — 执行: sudo systemctl status xhs-daemon"
fi

if grep -q 'gap_only' "$ROOT/cloud_deploy/config/daemon.json" 2>/dev/null; then
  ok "daemon.json 含 gap_only"
else
  bad "daemon.json 未配置 gap_only — 请 git pull + rsync"
fi

if grep -q 'enable_risk_round.*false' "$ROOT/cloud_deploy/config/daemon.json" 2>/dev/null; then
  ok "daemon.json risk 全池已关闭"
else
  bad "daemon.json 仍启用 risk 全池"
fi

SVC="/etc/systemd/system/xhs-daemon.service"
if [[ -f "$SVC" ]] && grep -q 'XHS_DAEMON_BATCH_SIZE=500' "$SVC"; then
  ok "systemd batch=500"
else
  bad "systemd 仍为旧 batch — 执行: sudo cp $ROOT/cloud_deploy/systemd/xhs-daemon.service $SVC && sudo systemctl daemon-reload"
fi

if [[ -f "$SVC" ]] && grep -q 'XHS_DAEMON_COOLDOWN_SEC=120' "$SVC"; then
  ok "systemd cooldown=120s"
else
  bad "systemd 仍为旧 cooldown"
fi

if grep -q '_pick_gap_batch' "$ROOT/cloud_deploy/daemon/cloud_daemon.py" 2>/dev/null \
   && grep -q 'enable_risk_round' "$ROOT/cloud_deploy/daemon/cloud_daemon.py" 2>/dev/null; then
  ok "cloud_daemon.py 为新版本（gap_only + rounds）"
else
  bad "cloud_daemon.py 仍为旧版 — 请 rsync"
fi

info "最近 5 条 daemon 日志:"
journalctl -u xhs-daemon -n 5 --no-pager 2>/dev/null || true

if journalctl -u xhs-daemon --since "10 min ago" --no-pager 2>/dev/null | grep -q 'mode=gap_only'; then
  ok "启动日志含 mode=gap_only"
elif journalctl -u xhs-daemon --since "10 min ago" --no-pager 2>/dev/null | grep -q 'risk全池'; then
  bad "仍在 risk 全池模式 — 请 rm -f $ROOT/data/daemon_cycle_state.json && sudo systemctl restart xhs-daemon"
else
  info "未找到近期启动日志，请: journalctl -u xhs-daemon -f"
fi

echo ""
if [[ "$FAIL" -eq 0 ]]; then
  ok "部署校验通过"
else
  echo -e "  ${RED}存在异常项，请按提示修复后重启 xhs-daemon${NC}"
  exit 1
fi
