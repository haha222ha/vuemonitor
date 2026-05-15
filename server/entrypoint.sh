#!/bin/bash
set -e

export PYTHONPATH=/app

echo "[entrypoint] Running database migrations..."
alembic upgrade head

echo "[entrypoint] Starting application..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers ${UVICORN_WORKERS:-2} \
    --log-level ${LOG_LEVEL:-info} \
    --access-log
