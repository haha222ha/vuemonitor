#!/usr/bin/env bash
# Run a Python script with server/.env loaded (same cwd as vuemonitor systemd).
# Example:
#   bash scripts/run-server-cmd.sh scripts/test_smtp.py --to you@qq.com

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/server/.venv/bin/python3"
export PYTHONPATH="$ROOT/server"
cd "$ROOT/server"
exec "$PY" "$@"
