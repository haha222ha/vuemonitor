# -*- coding: utf-8 -*-
"""当日销量快照跳过条件（App / ⑤ / ⑥ 共用）。"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_DB = os.path.join(APP_DIR, "crawl_data", "xhs_burst_monitor.db")
# ATTACH 别名：不可用 main（与连接默认库名冲突）
MAIN_DB_ALIAS = "xhs"

# 用于 SQL 片段：商品 g 或 track_goods 表别名 goods_id 列（需先 attach_main_db）
SKIP_TODAY_SQL = """
  AND NOT EXISTS (
      SELECT 1 FROM xhs.sold_history h
      WHERE h.goods_id = {gid} AND h.snapshot_date = date('now','localtime')
  )
  AND NOT EXISTS (
      SELECT 1 FROM xhs.sold_snapshots s
      WHERE s.goods_id = {gid}
        AND s.snapshot_time >= date('now','localtime')
  )
"""

SKIP_TODAY_SQL_MAIN = """
  AND NOT EXISTS (
      SELECT 1 FROM sold_history h
      WHERE h.goods_id = goods.goods_id AND h.snapshot_date = date('now','localtime')
  )
  AND NOT EXISTS (
      SELECT 1 FROM sold_snapshots s
      WHERE s.goods_id = goods.goods_id
        AND s.snapshot_time >= date('now','localtime')
  )
"""


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


def attach_main_db(conn, main_db=MAIN_DB, alias=MAIN_DB_ALIAS):
    """将主库挂到当前连接（别名 xhs，避免与 SQLite 默认 main 冲突）。"""
    if not os.path.isfile(main_db):
        return
    try:
        conn.execute(f"ATTACH DATABASE ? AS {alias}", (main_db,))
    except sqlite3.OperationalError as e:
        if "already" in str(e).lower():
            return
        raise


def count_skip_today_eligible(main_db=MAIN_DB):
    """主库：活跃且有销量、但今日尚无快照的商品数（⑥ 候选规模参考）。"""
    if not os.path.isfile(main_db):
        return 0
    conn = sqlite3.connect(main_db, timeout=60)
    conn.execute("PRAGMA query_only=ON")
    c = conn.cursor()
    c.execute(
        f"""SELECT COUNT(*) FROM goods
            WHERE lifecycle<3 AND sold_num>0
            {SKIP_TODAY_SQL_MAIN}"""
    )
    n = int(c.fetchone()[0] or 0)
    conn.close()
    return n


def count_today_snapshots(main_db=MAIN_DB):
    if not os.path.isfile(main_db):
        return 0, 0
    conn = sqlite3.connect(main_db, timeout=60)
    conn.execute("PRAGMA query_only=ON")
    c = conn.cursor()
    td = today_str()
    c.execute("SELECT COUNT(*) FROM sold_history WHERE snapshot_date=?", (td,))
    hist = int(c.fetchone()[0] or 0)
    c.execute(
        "SELECT COUNT(DISTINCT goods_id) FROM sold_snapshots WHERE snapshot_time>=?",
        (td,),
    )
    snap = int(c.fetchone()[0] or 0)
    conn.close()
    return hist, snap
