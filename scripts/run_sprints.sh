#!/bin/bash
# Run Sprint 1 + Sprint 2 API validation on host or CI
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE="${API_BASE:-http://127.0.0.1:8000}"
RUN_AI="${RUN_AI:-0}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@xhs365.cn}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-Admin123!ChangeMe}"

cd "$ROOT/server"
source .venv/bin/activate
export PYTHONPATH="$ROOT/server"

echo "========== Sprint 1 (P0) =========="
AI_FLAG=""
[ "$RUN_AI" = "1" ] && AI_FLAG="--run-ai"
python3 "$ROOT/scripts/sprint1_runner.py" --base-url "$BASE" $AI_FLAG
S1=$?

echo ""
echo "========== Sprint 2 (P1) =========="
python3 "$ROOT/scripts/sprint2_runner.py" --base-url "$BASE" \
  --admin-email "$ADMIN_EMAIL" --admin-password "$ADMIN_PASSWORD"
S2=$?

echo ""
if [ "$S1" -eq 0 ] && [ "$S2" -eq 0 ]; then
  echo "All sprints passed"
  exit 0
fi
echo "Sprint failures: S1=$S1 S2=$S2"
exit 1
