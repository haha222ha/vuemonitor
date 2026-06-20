#!/usr/bin/env python3
"""PG monitor_goods / full_sold_queue stats for verify_pure_online.sh."""
from __future__ import annotations

import os
import sys

ROOT = os.environ.get("XHS_CLOUD_ROOT", "/opt/xhs-cloud")
sys.path.insert(0, ROOT)

from cloud_deploy.scripts.bootstrap_env import bootstrap

bootstrap()

from cloud_deploy.cloud_api.database_pg import _conn, init_db
from cloud_deploy.daemon import pg_full_sold_queue as q

init_db()
conn = _conn()
with conn.cursor() as c:
    c.execute("SET search_path TO xhs_monitor, public")
    c.execute(
        "SELECT COUNT(*) FROM monitor_goods WHERE monitor_status IN ('active','idle')"
    )
    mg = c.fetchone()[0]
conn.close()
st = q.queue_stats()
print(
    f"monitor_goods={mg} queue_total={st['total']} "
    f"pending={st['pending']} synced={st['synced']}"
)
