#!/bin/bash
# V2 情报 Shadow 预生成（L0）— 默认写 data/insight_shadow，不影响 Legacy zip
# 用法:
#   bash cloud_deploy/scripts/run_insight_report_shadow.sh
#   bash cloud_deploy/scripts/run_insight_report_shadow.sh 2026-07-12
set -euo pipefail

ROOT="${XHS_CLOUD_ROOT:-/opt/xhs-cloud}"
DATE="${1:-$(date +%Y-%m-%d)}"
PY="${ROOT}/venv/bin/python"
SCRIPT="${ROOT}/cloud_deploy/scripts/cloud_insight_report.py"

if [[ ! -x "$PY" ]]; then
  PY=python3
fi

if [[ ! -f "$SCRIPT" ]]; then
  echo "[insight-shadow] missing $SCRIPT" >&2
  exit 1
fi

cd "$ROOT"
export PYTHONPATH="${ROOT}:${PYTHONPATH:-}"
export XHS_INSIGHT_SHADOW="${XHS_INSIGHT_SHADOW:-1}"

AGG="${ROOT}/cloud_deploy/scripts/aggregate_daily_category_metrics.py"
if [[ -f "$AGG" ]]; then
  echo "[insight-shadow] pre-aggregate daily_category_metrics date=$DATE"
  "$PY" "$AGG" "$DATE" || echo "[insight-shadow] aggregate skipped (table may not exist yet)"
fi

echo "[insight-shadow] date=$DATE shadow=1"
exec "$PY" "$SCRIPT" --date "$DATE" --playbook full
