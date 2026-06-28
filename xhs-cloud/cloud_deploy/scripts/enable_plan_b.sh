#!/bin/bash
# 方案 B：本地 gen_report + 上传 zip，云端只分发（关闭云自算报告 timer）
#
# 用法: bash /opt/xhs-cloud/cloud_deploy/scripts/enable_plan_b.sh
set -euo pipefail

ROOT="${XHS_CLOUD_ROOT:-/opt/xhs-cloud}"
ENV_FILE="${XHS_ENV_FILE:-$ROOT/.env}"

echo "=== 方案 B：云分发模式（本地 17:00 上传报告）==="

for unit in xhs-daily-report.timer xhs-daily-report.service xhs-ingest-report.timer xhs-ingest-report.service \
  xhs-weekly-report.timer xhs-weekly-report.service xhs-monthly-report.timer xhs-monthly-report.service; do
  if systemctl list-unit-files "$unit" 2>/dev/null | grep -q enabled; then
    echo "  禁用 $unit"
    sudo systemctl disable --now "$unit" 2>/dev/null || true
  fi
done

if [[ -f "$ENV_FILE" ]]; then
  grep -q '^XHS_REPORT_INGEST_SYNC_PG=' "$ENV_FILE" || echo 'XHS_REPORT_INGEST_SYNC_PG=0' >> "$ENV_FILE"
else
  echo "  警告: 未找到 $ENV_FILE"
fi

echo "  确保 xhs-cloud-api 运行（接收 POST /api/v1/sync/report-upload）"
sudo systemctl enable --now xhs-cloud-api.service 2>/dev/null || true

echo ""
echo "完成。"
echo "  • 本地主程序 17:00 自动 gen_report + upload-bundle"
echo "  • 云不再自算日/周/月报 timer（已关，由本地编排 API 触发）"
echo "  • 会员 portal 下载本地推送的 zip"
echo ""
echo "若 report-upload 接口 404，请 rsync 最新 xhs-cloud 并: sudo systemctl restart xhs-cloud-api"
