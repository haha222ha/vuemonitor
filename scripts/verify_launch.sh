#!/usr/bin/env bash
# Full launch verification: health + smoke + sprints + public pages hints.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_BASE="${API_BASE:-http://127.0.0.1:8000}"
export API_BASE

echo "=== XHS365 Launch Verification ==="
echo "API_BASE=$API_BASE"

curl -sf "$API_BASE/health" >/dev/null && echo "OK health" || { echo "FAIL health"; exit 1; }

python3 "$ROOT/scripts/api_smoke.py" --base-url "$API_BASE"

cd "$ROOT/server"
# shellcheck disable=SC1091
source .venv/bin/activate 2>/dev/null || true
export PYTHONPATH="$ROOT/server"

if [ -f "$ROOT/scripts/run_sprints.sh" ]; then
  export RUN_AI="${RUN_AI:-0}"
  bash "$ROOT/scripts/run_sprints.sh" || echo "WARN: sprints partial fail"
fi

echo ""
echo "--- Public endpoints ---"
curl -sf "$API_BASE/api/v1/public/support" | python3 -m json.tool | head -20
curl -sf "$API_BASE/api/v1/public/downloads" | python3 -m json.tool

echo ""
echo "Done. Browser: /login /purchase /faq /download + admin licenses"
