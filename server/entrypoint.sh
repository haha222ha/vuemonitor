#!/bin/bash
set -e

export PYTHONPATH=/app

echo "[entrypoint] Running database migrations..."
MAX_RETRIES=3
RETRY_DELAY=5

for i in $(seq 1 $MAX_RETRIES); do
    if alembic upgrade head; then
        echo "[entrypoint] Migration completed successfully"
        break
    fi

    echo "[entrypoint] Migration attempt $i/$MAX_RETRIES failed"

    if [ $i -eq $MAX_RETRIES ]; then
        echo "[entrypoint] ERROR: All migration attempts failed"
        echo "[entrypoint] Current migration status:"
        alembic current 2>/dev/null || echo "  Unable to get current migration status"
        echo "[entrypoint] Manual intervention required. Exiting."
        exit 1
    fi

    echo "[entrypoint] Retrying in ${RETRY_DELAY}s..."
    sleep $RETRY_DELAY
    RETRY_DELAY=$((RETRY_DELAY * 2))
done

echo "[entrypoint] Starting application..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers ${UVICORN_WORKERS:-2} \
    --log-level ${LOG_LEVEL:-info} \
    --access-log
