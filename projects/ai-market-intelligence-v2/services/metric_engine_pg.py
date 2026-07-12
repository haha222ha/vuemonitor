# -*- coding: utf-8 -*-
"""
PG 数据源骨架（Phase 2 Shadow 管道）。

环境变量:
  INSIGHT_PG_DSN=postgresql://...
  INSIGHT_DATA_SOURCE=pg|sample  (默认 sample)

未配置 DSN 时 load_items 返回 None，由管道回退 mock。
"""
from __future__ import annotations

import os
from typing import Any


def pg_configured() -> bool:
    return bool((os.environ.get("INSIGHT_PG_DSN") or "").strip())


def load_items(report_date: str, *, limit: int = 5000) -> list[dict[str, Any]] | None:
    """
    从 PG 读取内部商品快照（仅管道内使用，不得对外序列化）。

    生产 SQL 示例（待对接 xhs-cloud schema）:
      SELECT title, price, actual_v1d, gr, first_seen_days, is_new
      FROM raw_product_snapshots
      WHERE snapshot_date = %(date)s
      LIMIT %(limit)s
    """
    # 限制 limit 上限,防止误传超大值拖垮 PG
    limit = max(1, min(limit, 50000))
    dsn = (os.environ.get("INSIGHT_PG_DSN") or "").strip()
    if not dsn:
        return None
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError as e:
        raise RuntimeError("INSIGHT_PG_DSN 已配置但未安装 psycopg2") from e

    sql = """
        SELECT
            title,
            COALESCE(price, 0) AS price,
            COALESCE(actual_v1d, 0) AS actual_v1d,
            COALESCE(gr, 0) AS gr,
            COALESCE(first_seen_days, 99) AS first_seen_days,
            COALESCE(is_new, false) AS is_new
        FROM raw_product_snapshots
        WHERE snapshot_date = %s
        LIMIT %s
    """
    with psycopg2.connect(dsn, cursor_factory=RealDictCursor) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (report_date, limit))
            rows = cur.fetchall()
    return [dict(r) for r in rows]
