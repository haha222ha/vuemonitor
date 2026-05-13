"""Database maintenance utilities.

Usage:
    python -m scripts.db_maintenance vacuum
    python -m scripts.db_maintenance analyze
    python -m scripts.db_maintenance reindex
    python -m scripts.db_maintenance stats
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import async_engine
from sqlalchemy import text


async def run_vacuum():
    async with async_engine.connect() as conn:
        await conn.execute(text("VACUUM ANALYZE"))
        print("[OK] VACUUM ANALYZE completed")


async def run_analyze():
    async with async_engine.connect() as conn:
        await conn.execute(text("ANALYZE"))
        print("[OK] ANALYZE completed")


async def run_reindex():
    async with async_engine.connect() as conn:
        tables = [
            "users", "products", "product_features", "ai_analyses",
            "collect_tasks", "collect_task_items", "monitor_rules",
            "alert_rules", "alert_events", "analysis_results",
            "license_codes", "license_activations",
            "security_audit_log", "operation_audit_log",
        ]
        for table in tables:
            try:
                await conn.execute(text(f"REINDEX TABLE {table}"))
                print(f"  [OK] REINDEX {table}")
            except Exception as e:
                print(f"  [SKIP] {table}: {e}")
        print("[OK] REINDEX completed")


async def run_stats():
    async with async_engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT
                schemaname,
                tablename,
                n_live_tup AS row_count,
                n_dead_tup AS dead_rows,
                last_vacuum,
                last_autovacuum,
                last_analyze,
                last_autoanalyze
            FROM pg_stat_user_tables
            ORDER BY n_dead_tup DESC
        """))
        rows = result.fetchall()

        print(f"\n{'Table':<30} {'Rows':>10} {'Dead':>10} {'Last Vacuum':<22} {'Last Analyze':<22}")
        print("-" * 96)
        for row in rows:
            vacuum = str(row[4] or row[5] or "-")[:19]
            analyze = str(row[6] or row[7] or "-")[:19]
            print(f"{row[1]:<30} {row[2]:>10} {row[3]:>10} {vacuum:<22} {analyze:<22}")

        result = await conn.execute(text("""
            SELECT
                indexrelname,
                relname,
                idx_scan,
                idx_tup_read,
                idx_tup_fetch
            FROM pg_stat_user_indexes
            WHERE idx_scan = 0
            ORDER BY relname
        """))
        unused = result.fetchall()
        if unused:
            print(f"\nUnused indexes (idx_scan=0):")
            for row in unused:
                print(f"  {row[1]}.{row[0]}")

        result = await conn.execute(text("SELECT pg_database_size(current_database())"))
        db_size = result.scalar()
        print(f"\nDatabase size: {db_size / 1024 / 1024:.1f} MB")


COMMANDS = {
    "vacuum": run_vacuum,
    "analyze": run_analyze,
    "reindex": run_reindex,
    "stats": run_stats,
}


async def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: python -m scripts.db_maintenance <{'|'.join(COMMANDS.keys())}>")
        sys.exit(1)

    cmd = sys.argv[1]
    print(f"Running: {cmd}")
    await COMMANDS[cmd]()
    await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
