#!/bin/bash
# 服务器一次性导入（上传 server_sync_pack 后执行）
#
# 用法（数据在 import_batch 下）:
#   bash /opt/xhs-cloud/cloud_deploy/scripts/server_import.sh
#
# 或数据刚 scp 到 import_batch:
#   bash /opt/xhs-cloud/data/import_batch/server_import.sh
#
set -euo pipefail

ROOT="/opt/xhs-cloud"
BATCH="${XHS_IMPORT_BATCH:-$ROOT/data/import_batch}"
export PYTHONPATH="$ROOT"

echo ""
echo "  ========================================"
echo "  |   选品云 · 首次数据导入 + 纯线上    |"
echo "  ========================================"
echo "  数据目录: $BATCH"
echo ""

[[ -d "$BATCH/historical_reports" ]] || { echo "缺少 $BATCH/historical_reports"; exit 1; }
[[ -d "$BATCH/monitor_pool" ]] || { echo "缺少 $BATCH/monitor_pool"; exit 1; }

echo "==> 1/4 历史日报 import"
"$ROOT/venv/bin/python" "$ROOT/cloud_deploy/scripts/import_historical_reports.py" \
  --root "$BATCH/historical_reports"

echo "==> 2/4 监控池 sold_history import"
"$ROOT/venv/bin/python" "$ROOT/cloud_deploy/scripts/import_monitor_pool_offline.py" \
  --pack "$BATCH/monitor_pool"

echo "==> 3/4 纯线上 enable（daemon + 日/周/月报 timer）"
bash "$ROOT/cloud_deploy/scripts/enable_pure_online.sh"

echo "==> 4/4 验收 + 重启 daemon"
bash "$ROOT/cloud_deploy/scripts/verify_pure_online.sh"
sudo systemctl restart xhs-daemon

echo ""
echo "完成。期望 verify 输出 monitor_goods > 0"
