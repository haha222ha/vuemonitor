# -*- coding: utf-8 -*-
"""
商品风险注册表 — 冻结/下架/失效商品的持久化标注与阶段性分析。

用途：
- 记录哪些商品已被平台冻结（600 item freeze）或不存在（602）
- 按风险等级（高/中/低）供选品参考：曾热后死、低动销死品等
- 按店铺聚合：哪些店冻结品多 → 高危店铺
- 导出 CSV 到桌面报告目录
"""
from __future__ import annotations

import argparse
import csv
import os
import sqlite3
from datetime import datetime, timedelta

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "crawl_data")
MAIN_DB = os.path.join(DATA_DIR, "xhs_burst_monitor.db")
REPORT_BASE = r"C:\Users\Administrator\Desktop\每日选品全量数据\风险分析"

RISK_TYPE_FROZEN = "frozen"
RISK_LABELS = {600: "商品已下架/冻结", 602: "商品不存在"}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS goods_risk_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    goods_id      TEXT NOT NULL,
    risk_type     TEXT NOT NULL DEFAULT 'frozen',
    risk_code     INTEGER NOT NULL DEFAULT 600,
    risk_label    TEXT DEFAULT '',
    risk_level    TEXT DEFAULT 'medium',
    source        TEXT DEFAULT '',
    detected_at   TEXT NOT NULL,
    title         TEXT DEFAULT '',
    sold_num      INTEGER DEFAULT 0,
    velocity_1d   REAL DEFAULT 0,
    pool          TEXT DEFAULT '',
    store_id      TEXT DEFAULT '',
    store_name    TEXT DEFAULT '',
    is_virtual    INTEGER DEFAULT -1,
    goods_type_detail TEXT DEFAULT '',
    region        TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_gre_goods ON goods_risk_events(goods_id);
CREATE INDEX IF NOT EXISTS idx_gre_time ON goods_risk_events(detected_at);
CREATE INDEX IF NOT EXISTS idx_gre_level ON goods_risk_events(risk_level);
CREATE INDEX IF NOT EXISTS idx_gre_store ON goods_risk_events(store_id);

CREATE TABLE IF NOT EXISTS goods_risk_registry (
    goods_id          TEXT PRIMARY KEY,
    risk_type         TEXT NOT NULL DEFAULT 'frozen',
    risk_code         INTEGER NOT NULL DEFAULT 600,
    risk_label        TEXT DEFAULT '',
    risk_level        TEXT DEFAULT 'medium',
    first_detected_at TEXT NOT NULL,
    last_detected_at  TEXT NOT NULL,
    detect_count      INTEGER DEFAULT 1,
    source_first      TEXT DEFAULT '',
    source_last       TEXT DEFAULT '',
    title             TEXT DEFAULT '',
    sold_num          INTEGER DEFAULT 0,
    velocity_1d       REAL DEFAULT 0,
    pool              TEXT DEFAULT '',
    store_id          TEXT DEFAULT '',
    store_name        TEXT DEFAULT '',
    is_virtual        INTEGER DEFAULT -1,
    goods_type_detail TEXT DEFAULT '',
    region            TEXT DEFAULT '',
    note              TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_grr_level ON goods_risk_registry(risk_level);
CREATE INDEX IF NOT EXISTS idx_grr_store ON goods_risk_registry(store_id);
CREATE INDEX IF NOT EXISTS idx_grr_last ON goods_risk_registry(last_detected_at);
"""


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def db_conn(db_path=MAIN_DB, timeout=30):
    conn = sqlite3.connect(db_path, timeout=timeout)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.row_factory = sqlite3.Row
    return conn


def ensure_risk_tables(conn=None):
    own = conn is None
    if own:
        conn = db_conn()
    conn.executescript(SCHEMA_SQL)
    if own:
        conn.commit()
        conn.close()


def calc_risk_level(pool="", velocity_1d=0, sold_num=0):
    """
    风险等级（供选品参考，非平台官方）：
    - high: 曾处 BURST/ACCEL 或日增>10 — 跟风后暴死，慎跟
    - medium: 有一定销量或动销 — 普通失效
    - low: 低动销/低销量 — 死库存类
    """
    p = (pool or "").upper()
    v1d = float(velocity_1d or 0)
    sold = int(sold_num or 0)
    if p in ("BURST", "ACCEL") or v1d > 10:
        return "high"
    if sold >= 500 or v1d > 0:
        return "medium"
    return "low"


def _load_goods_meta(c, goods_id):
    c.execute(
        """SELECT title, sold_num, velocity_1d, pool, store_id, store_name,
                  is_virtual, goods_type_detail, region
           FROM goods WHERE goods_id=?""",
        (goods_id,),
    )
    row = c.fetchone()
    if not row:
        return {}
    return {
        "title": row["title"] or "",
        "sold_num": int(row["sold_num"] or 0),
        "velocity_1d": float(row["velocity_1d"] or 0),
        "pool": row["pool"] or "WATCH",
        "store_id": row["store_id"] or "",
        "store_name": row["store_name"] or "",
        "is_virtual": int(row["is_virtual"] if row["is_virtual"] is not None else -1),
        "goods_type_detail": row["goods_type_detail"] or "",
        "region": row["region"] or "",
    }


def record_goods_risk(goods_id, code=600, source="", db_path=MAIN_DB):
    """写入风险事件 + 更新注册表（所有冻结/下架路径统一入口）。"""
    if not goods_id:
        return False
    code = int(code or 600)
    risk_type = RISK_TYPE_FROZEN
    risk_label = RISK_LABELS.get(code, f"code={code}")
    now = _now()

    conn = db_conn(db_path)
    ensure_risk_tables(conn)
    c = conn.cursor()
    meta = _load_goods_meta(c, goods_id)
    level = calc_risk_level(meta.get("pool"), meta.get("velocity_1d"), meta.get("sold_num"))

    c.execute(
        """INSERT INTO goods_risk_events
           (goods_id, risk_type, risk_code, risk_label, risk_level, source, detected_at,
            title, sold_num, velocity_1d, pool, store_id, store_name,
            is_virtual, goods_type_detail, region)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            goods_id,
            risk_type,
            code,
            risk_label,
            level,
            source or "",
            now,
            meta.get("title", ""),
            meta.get("sold_num", 0),
            meta.get("velocity_1d", 0),
            meta.get("pool", ""),
            meta.get("store_id", ""),
            meta.get("store_name", ""),
            meta.get("is_virtual", -1),
            meta.get("goods_type_detail", ""),
            meta.get("region", ""),
        ),
    )

    c.execute("SELECT goods_id, detect_count FROM goods_risk_registry WHERE goods_id=?", (goods_id,))
    existing = c.fetchone()
    if existing:
        c.execute(
            """UPDATE goods_risk_registry SET
               risk_code=?, risk_label=?, risk_level=?,
               last_detected_at=?, detect_count=detect_count+1,
               source_last=?, title=?, sold_num=?, velocity_1d=?,
               pool=?, store_id=?, store_name=?,
               is_virtual=?, goods_type_detail=?, region=?
               WHERE goods_id=?""",
            (
                code,
                risk_label,
                level,
                now,
                source or "",
                meta.get("title", ""),
                meta.get("sold_num", 0),
                meta.get("velocity_1d", 0),
                meta.get("pool", ""),
                meta.get("store_id", ""),
                meta.get("store_name", ""),
                meta.get("is_virtual", -1),
                meta.get("goods_type_detail", ""),
                meta.get("region", ""),
                goods_id,
            ),
        )
    else:
        c.execute(
            """INSERT INTO goods_risk_registry
               (goods_id, risk_type, risk_code, risk_label, risk_level,
                first_detected_at, last_detected_at, detect_count,
                source_first, source_last, title, sold_num, velocity_1d,
                pool, store_id, store_name, is_virtual, goods_type_detail, region)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                goods_id,
                risk_type,
                code,
                risk_label,
                level,
                now,
                now,
                1,
                source or "",
                source or "",
                meta.get("title", ""),
                meta.get("sold_num", 0),
                meta.get("velocity_1d", 0),
                meta.get("pool", ""),
                meta.get("store_id", ""),
                meta.get("store_name", ""),
                meta.get("is_virtual", -1),
                meta.get("goods_type_detail", ""),
                meta.get("region", ""),
            ),
        )

    conn.commit()
    conn.close()
    return True


def risk_summary(days=30, db_path=MAIN_DB):
    """阶段性汇总。"""
    ensure_risk_tables()
    since = (datetime.now() - timedelta(days=max(1, int(days)))).strftime("%Y-%m-%d")
    conn = db_conn(db_path)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM goods_risk_registry")
    total_registry = int(c.fetchone()[0] or 0)

    c.execute(
        """SELECT risk_level, COUNT(*) FROM goods_risk_registry
           WHERE date(last_detected_at) >= date(?) GROUP BY risk_level""",
        (since,),
    )
    by_level = {r[0]: int(r[1]) for r in c.fetchall()}

    c.execute(
        """SELECT COUNT(*) FROM goods_risk_events WHERE date(detected_at) >= date(?)""",
        (since,),
    )
    events_period = int(c.fetchone()[0] or 0)

    c.execute(
        """SELECT source, COUNT(*) FROM goods_risk_events
           WHERE date(detected_at) >= date(?) GROUP BY source ORDER BY 2 DESC""",
        (since,),
    )
    by_source = [(r[0] or "(未知)", int(r[1])) for r in c.fetchall()]

    c.execute(
        """SELECT store_id, store_name, COUNT(*) AS n,
                  SUM(CASE WHEN risk_level='high' THEN 1 ELSE 0 END) AS high_n
           FROM goods_risk_registry
           WHERE COALESCE(store_id,'')<>'' AND date(last_detected_at) >= date(?)
           GROUP BY store_id ORDER BY high_n DESC, n DESC LIMIT 15""",
        (since,),
    )
    top_shops = [dict(r) for r in c.fetchall()]

    conn.close()
    return {
        "days": days,
        "since": since,
        "total_registry": total_registry,
        "period_events": events_period,
        "by_level": by_level,
        "by_source": by_source,
        "top_shops": top_shops,
    }


def export_risk_reports(days=30, out_dir=None, db_path=MAIN_DB):
    """导出高危商品清单 + 店铺统计 + 文字摘要。"""
    ensure_risk_tables()
    since = (datetime.now() - timedelta(days=max(1, int(days)))).strftime("%Y-%m-%d")
    date_tag = datetime.now().strftime("%Y%m%d")
    base = out_dir or os.path.join(REPORT_BASE, date_tag)
    os.makedirs(base, exist_ok=True)

    conn = db_conn(db_path)
    c = conn.cursor()

    goods_path = os.path.join(base, f"高危商品清单_{days}天_{date_tag}.csv")
    c.execute(
        """SELECT goods_id, risk_level, risk_label, title, sold_num, velocity_1d,
                  pool, store_id, store_name, first_detected_at, last_detected_at,
                  source_first, source_last, detect_count, goods_type_detail, region
           FROM goods_risk_registry
           WHERE date(last_detected_at) >= date(?)
           ORDER BY
             CASE risk_level WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
             velocity_1d DESC, sold_num DESC""",
        (since,),
    )
    goods_rows = c.fetchall()
    with open(goods_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "商品ID",
                "风险等级",
                "风险类型",
                "标题",
                "销量",
                "日增量",
                "池",
                "店铺ID",
                "店铺名",
                "首次发现",
                "最近发现",
                "首次来源",
                "最近来源",
                "检测次数",
                "品类",
                "发货地",
            ]
        )
        for r in goods_rows:
            w.writerow(
                [
                    r["goods_id"],
                    r["risk_level"],
                    r["risk_label"],
                    r["title"],
                    r["sold_num"],
                    r["velocity_1d"],
                    r["pool"],
                    r["store_id"],
                    r["store_name"],
                    r["first_detected_at"],
                    r["last_detected_at"],
                    r["source_first"],
                    r["source_last"],
                    r["detect_count"],
                    r["goods_type_detail"],
                    r["region"],
                ]
            )

    shop_path = os.path.join(base, f"高危店铺统计_{days}天_{date_tag}.csv")
    c.execute(
        """SELECT store_id, store_name,
                  COUNT(*) AS frozen_total,
                  SUM(CASE WHEN risk_level='high' THEN 1 ELSE 0 END) AS high_risk,
                  SUM(CASE WHEN risk_level='medium' THEN 1 ELSE 0 END) AS medium_risk,
                  SUM(CASE WHEN risk_level='low' THEN 1 ELSE 0 END) AS low_risk,
                  MAX(last_detected_at) AS last_frozen_at
           FROM goods_risk_registry
           WHERE COALESCE(store_id,'')<>'' AND date(last_detected_at) >= date(?)
           GROUP BY store_id
           HAVING frozen_total >= 2
           ORDER BY high_risk DESC, frozen_total DESC""",
        (since,),
    )
    shop_rows = c.fetchall()
    with open(shop_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "店铺ID",
                "店铺名",
                "冻结商品数",
                "高危品数",
                "中危品数",
                "低危品数",
                "最近冻结时间",
            ]
        )
        for r in shop_rows:
            w.writerow(
                [
                    r["store_id"],
                    r["store_name"],
                    r["frozen_total"],
                    r["high_risk"],
                    r["medium_risk"],
                    r["low_risk"],
                    r["last_frozen_at"],
                ]
            )

    conn.close()

    summary = risk_summary(days=days, db_path=db_path)
    summary_path = os.path.join(base, f"风险分析摘要_{days}天_{date_tag}.txt")
    lines = [
        f"商品风险分析摘要（近 {days} 天，自 {since}）",
        f"生成时间: {_now()}",
        "",
        f"注册表累计: {summary['total_registry']:,} 个风险商品",
        f"本期新增事件: {summary['period_events']:,} 条",
        "",
        "按风险等级（本期活跃）:",
    ]
    for lv in ("high", "medium", "low"):
        n = summary["by_level"].get(lv, 0)
        label = {"high": "高危-曾热后死/慎跟", "medium": "中危-有销量失效", "low": "低危-低动销死品"}.get(
            lv, lv
        )
        lines.append(f"  {label}: {n:,}")
    lines.extend(["", "按发现来源:"])
    for src, n in summary["by_source"]:
        lines.append(f"  {src}: {n:,}")
    lines.extend(["", "TOP 高危店铺（冻结品≥2）:"])
    for i, s in enumerate(summary["top_shops"][:10], 1):
        lines.append(
            f"  {i}. {s.get('store_name') or s.get('store_id')} "
            f"冻结{s['n']} 其中高危{s['high_n']}"
        )
    lines.extend(
        [
            "",
            "说明:",
            "- high: 曾在 BURST/ACCEL 或日增量>10，跟风后暴死，建议不做同款",
            "- 店铺冻结品≥2 建议列入观察名单，选品时避开同店新品",
            f"- 商品明细: {os.path.basename(goods_path)}",
            f"- 店铺统计: {os.path.basename(shop_path)}",
        ]
    )
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return {
        "dir": base,
        "goods_csv": goods_path,
        "shop_csv": shop_path,
        "summary_txt": summary_path,
        "goods_count": len(goods_rows),
        "shop_count": len(shop_rows),
    }


def backfill_from_lifecycle3(limit=5000, db_path=MAIN_DB):
    """从历史 lifecycle=3 商品回填注册表（一次性/定期）。"""
    ensure_risk_tables()
    conn = db_conn(db_path)
    c = conn.cursor()
    c.execute(
        """SELECT g.goods_id FROM goods g
           LEFT JOIN goods_risk_registry r ON r.goods_id = g.goods_id
           WHERE g.lifecycle >= 3 AND r.goods_id IS NULL
           LIMIT ?""",
        (max(1, int(limit)),),
    )
    ids = [r[0] for r in c.fetchall()]
    conn.close()
    n = 0
    for gid in ids:
        if record_goods_risk(gid, code=600, source="backfill_lifecycle3", db_path=db_path):
            n += 1
    return n


REPORT_RISK_COLUMNS = [
    "goods_id",
    "title",
    "risk_level",
    "risk_label",
    "sold_num",
    "velocity_1d",
    "pool",
    "store_id",
    "store_name",
    "detected_at",
    "source",
    "goods_type_detail",
    "is_today",
]

RISK_LEVEL_LABELS = {
    "high": "高危-曾热后死",
    "medium": "中危-有销量失效",
    "low": "低危-低动销死品",
}


def load_report_risk_bundle(report_date=None, fallback_days=7, limit=2000, db_path=MAIN_DB):
    """
    供 gen_report 每日报告嵌入：优先今日新发现冻结品，不足则补近 fallback_days 天。
    数据来自主库 goods_risk_events / goods_risk_registry。
    """
    ensure_risk_tables()
    report_date = report_date or datetime.now().strftime("%Y-%m-%d")
    fallback_days = max(1, int(fallback_days or 7))
    limit = max(1, min(int(limit or 2000), 10000))

    conn = db_conn(db_path)
    c = conn.cursor()

    c.execute(
        """SELECT goods_id, title, risk_level, risk_label, sold_num, velocity_1d,
                  pool, store_id, store_name, detected_at, source,
                  goods_type_detail, 1 AS is_today
           FROM goods_risk_events
           WHERE date(detected_at) = date(?)
           ORDER BY CASE risk_level WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                    velocity_1d DESC, sold_num DESC
           LIMIT ?""",
        (report_date, limit),
    )
    items = [list(r) for r in c.fetchall()]
    seen = {r[0] for r in items}
    today_count = len(items)

    if len(items) < limit:
        c.execute(
            f"""SELECT goods_id, title, risk_level, risk_label, sold_num, velocity_1d,
                       pool, store_id, store_name, last_detected_at, source_last,
                       goods_type_detail, 0 AS is_today
                FROM goods_risk_registry
                WHERE date(last_detected_at) >= date(?, '-{fallback_days} days')
                  AND date(last_detected_at) < date(?)
                ORDER BY CASE risk_level WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                         velocity_1d DESC, sold_num DESC
                LIMIT ?""",
            (report_date, report_date, limit - len(items)),
        )
        for row in c.fetchall():
            if row[0] not in seen:
                items.append(list(row))
                seen.add(row[0])

    by_level = {"high": 0, "medium": 0, "low": 0}
    for row in items:
        lv = row[2] or "low"
        by_level[lv] = by_level.get(lv, 0) + 1

    c.execute("SELECT COUNT(*) FROM goods_risk_registry")
    total_registry = int(c.fetchone()[0] or 0)

    c.execute(
        """SELECT store_id, store_name, COUNT(*) AS n,
                  SUM(CASE WHEN risk_level='high' THEN 1 ELSE 0 END) AS high_n
           FROM goods_risk_registry
           WHERE COALESCE(store_id,'')<>'' AND date(last_detected_at) >= date(?, '-7 days')
           GROUP BY store_id
           HAVING n >= 2
           ORDER BY high_n DESC, n DESC
           LIMIT 20""",
        (report_date,),
    )
    top_shops = [
        [r["store_id"], r["store_name"] or "", int(r["n"]), int(r["high_n"] or 0)]
        for r in c.fetchall()
    ]
    conn.close()

    note = (
        f"今日新发现 {today_count} 个冻结/下架品"
        if today_count
        else f"今日暂无新发现，下列为近 {fallback_days} 天内标注的风险品"
    )

    return {
        "meta": {
            "report_date": report_date,
            "count": len(items),
            "today_count": today_count,
            "total_registry": total_registry,
            "high_count": by_level.get("high", 0),
            "medium_count": by_level.get("medium", 0),
            "low_count": by_level.get("low", 0),
            "fallback_days": fallback_days,
            "note": note,
            "guide": {
                "title": "冻结/下架风险品 — 选品避坑参考",
                "lines": [
                    "下列商品已被平台冻结或下架，不建议跟款或上架同款。",
                    "列表中「销量」为库内历史快照；标注后接口已无法拉取实时详情，请复制商品ID到小红书App核实。",
                    "高危(high)：曾在 BURST/ACCEL 或日增量>10 后失效 — 典型跟风暴死，慎做同款。",
                    "中危(medium)：有一定销量后失效 — 参考避坑，勿盲目复制标题/主图。",
                    "低危(low)：低动销死品 — 优先级低，但说明该链路过期或违规。",
                    "同店铺冻结品≥2：建议列入观察名单，选品时避开该店新品。",
                    "数据写入主库 goods_risk_registry，与 lifecycle=3 下架标记同步。",
                ],
            },
        },
        "columns": REPORT_RISK_COLUMNS,
        "level_labels": RISK_LEVEL_LABELS,
        "items": items,
        "shop_columns": ["store_id", "store_name", "frozen_count", "high_risk_count"],
        "top_shops": top_shops,
    }


def write_risk_csv(path, bundle):
    """将报告用风险 bundle 写入 CSV。"""
    headers = [
        "商品ID",
        "标题",
        "风险等级",
        "风险类型",
        "销量",
        "日增量",
        "池",
        "店铺ID",
        "店铺名",
        "发现时间",
        "来源",
        "品类",
        "是否今日新发现",
    ]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for row in bundle.get("items") or []:
            w.writerow(row)
    return path


def print_summary(days=30):
    s = risk_summary(days=days)
    print(f"=== 商品风险注册表 | 近 {s['days']} 天 ===")
    print(f"累计注册: {s['total_registry']:,}")
    print(f"本期事件: {s['period_events']:,}")
    print("等级分布:", s["by_level"])
    print("来源分布:", s["by_source"])
    print("TOP 店铺:")
    for row in s["top_shops"][:8]:
        print(f"  {row.get('store_name') or row['store_id']}: 冻结{row['n']} 高危{row['high_n']}")


def main():
    p = argparse.ArgumentParser(description="商品风险注册表 — 冻结/下架分析与导出")
    p.add_argument("--summary", action="store_true", help="打印阶段性摘要")
    p.add_argument("--export", action="store_true", help="导出 CSV 到桌面风险分析目录")
    p.add_argument("--days", type=int, default=30, help="分析窗口天数")
    p.add_argument("--backfill", type=int, default=0, metavar="N", help="从 lifecycle=3 回填 N 条")
    args = p.parse_args()

    ensure_risk_tables()

    if args.backfill > 0:
        n = backfill_from_lifecycle3(limit=args.backfill)
        print(f"回填完成: {n} 条")

    if args.summary or (not args.export and args.backfill <= 0):
        print_summary(days=args.days)

    if args.export:
        r = export_risk_reports(days=args.days)
        print(f"导出目录: {r['dir']}")
        print(f"商品清单: {r['goods_count']} 条 -> {r['goods_csv']}")
        print(f"店铺统计: {r['shop_count']} 家 -> {r['shop_csv']}")
        print(f"文字摘要: {r['summary_txt']}")


if __name__ == "__main__":
    main()
