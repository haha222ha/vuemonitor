# -*- coding: utf-8 -*-
"""
精品库双向同步 — 对齐需求规格书 v1.6 §5

用法（先加载 D:\\xhs-data\\config\\portable_paths.env + local_sync.env）:
  python tools/cloud_sync_premium.py push
  python tools/cloud_sync_premium.py pull
  python tools/cloud_sync_premium.py backfill --pending
  python tools/cloud_sync_premium.py push-daily --since 2026-06-01
  python tools/cloud_sync_premium.py sync-full --since 2026-06-01
"""
from __future__ import annotations

import json
import os
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request

_TOOLS = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_TOOLS)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from xhs_portable_paths import bootstrap_portable_env, bootstrap_sync_env

bootstrap_portable_env(_ROOT)
bootstrap_sync_env()

from xhs_premium_store import connect, premium_backend

_STATE_FILE = os.path.join(
    os.environ.get("XHS_SYNC_LOG_DIR", r"D:\xhs-data\logs"),
    "premium_sync_state.json",
)


def _log(msg: str, log_func=None) -> None:
    fn = log_func or print
    fn(f"[cloud-sync-premium] {msg}")


def _client_id() -> str:
    return os.environ.get(
        "XHS_SYNC_CLIENT_ID",
        f"local_app:{socket.gethostname()}",
    )


def _api_base() -> str:
    return os.environ.get("XHS_CLOUD_API_URL", "").rstrip("/")


def _sync_key() -> str:
    return os.environ.get("XHS_CLOUD_SYNC_KEY", "")


def _require_cloud() -> None:
    if not _api_base() or not _sync_key():
        raise RuntimeError("请配置 XHS_CLOUD_API_URL + XHS_CLOUD_SYNC_KEY（local_sync.env）")


def _post_json(path: str, payload: dict) -> dict:
    _require_cloud()
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{_api_base()}{path}",
        data=body,
        headers={"Content-Type": "application/json", "X-Sync-Key": _sync_key()},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {detail}") from e


def _get_json(path: str, params: dict | None = None) -> dict:
    _require_cloud()
    url = f"{_api_base()}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"X-Sync-Key": _sync_key()},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def _row_dict(cursor, row) -> dict:
    cols = [d[0] for d in cursor.description]
    return {cols[i]: row[i] for i in range(len(cols))}


def _load_local_version() -> int:
    try:
        if os.path.isfile(_STATE_FILE):
            with open(_STATE_FILE, "r", encoding="utf-8") as f:
                return int(json.load(f).get("last_pull_version") or 0)
    except Exception:
        pass
    return 0


def _save_local_version(v: int) -> None:
    os.makedirs(os.path.dirname(_STATE_FILE) or ".", exist_ok=True)
    data = {}
    if os.path.isfile(_STATE_FILE):
        try:
            with open(_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    data["last_pull_version"] = int(v)
    with open(_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


_UPSERT_COLS = (
    "goods_id", "title", "tier", "lifecycle", "primary_keyword", "store_id", "store_name",
    "deal_price", "sold_num", "velocity_1d", "actual_velocity_1d", "burst_score",
    "report_count", "first_report_date", "last_report_date", "scan_priority",
    "shop_fans", "shop_sales", "shop_fans_delta_1d", "streak_sold_up_days",
    "last_app_scan", "last_metric_scan", "last_scan_engine", "updated_at",
)


def _fetch_goods_rows(goods_ids: list[str] | None = None, limit: int = 0) -> list[dict]:
    conn = connect()
    c = conn.cursor()
    cols = ", ".join(_UPSERT_COLS)
    sql = f"SELECT {cols} FROM premium_goods WHERE lifecycle < 3"
    params: list = []
    if goods_ids:
        ph = ",".join("%s" if premium_backend() == "postgresql" else "?" for _ in goods_ids)
        sql += f" AND goods_id IN ({ph})"
        params.extend(goods_ids)
    sql += " ORDER BY updated_at DESC"
    if limit > 0:
        sql += f" LIMIT {int(limit)}"
    c.execute(sql, params)
    rows = [_row_dict(c, r) for r in c.fetchall()]
    conn.close()
    return rows


def push_upsert(
    goods_ids: list[str] | None = None,
    limit: int = 0,
    batch_size: int = 200,
    log_func=None,
) -> dict:
    rows = _fetch_goods_rows(goods_ids, limit=limit)
    if not rows:
        return {"accepted": 0, "rows": 0}
    total = 0
    server_version = 0
    for i in range(0, len(rows), batch_size):
        chunk = rows[i:i + batch_size]
        for r in chunk:
            r.setdefault("scan_owner", "local")
            r.setdefault("last_scan_engine", "app")
        resp = _post_json(
            "/api/v1/sync/premium-upsert",
            {
                "client_id": _client_id(),
                "rows": chunk,
            },
        )
        total += int(resp.get("accepted") or len(chunk))
        server_version = int(resp.get("server_version") or server_version)
        _log(f"upsert batch {i // batch_size + 1}: {len(chunk)} → {total:,}", log_func)
    return {"accepted": total, "server_version": server_version}


def push_upsert_goods_ids(goods_ids: list[str], log_func=None) -> dict:
    ids = [str(g).strip() for g in goods_ids if g and len(str(g)) >= 5]
    if not ids:
        return {"accepted": 0}
    return push_upsert(goods_ids=ids, log_func=log_func)


def push_snapshots_backfill_for_goods(
    goods_id: str,
    log_func=None,
) -> dict:
    conn = connect()
    c = conn.cursor()
    c.execute(
        """
        SELECT goods_id, snap_date, sold_num, deal_price, delta, actual_delta,
               velocity_1d, source, created_at
        FROM premium_goods_daily WHERE goods_id=?
        ORDER BY snap_date
        """,
        (goods_id,),
    )
    g_daily = [_row_dict(c, r) for r in c.fetchall()]
    c.execute("SELECT store_id FROM premium_goods WHERE goods_id=?", (goods_id,))
    srow = c.fetchone()
    store_id = str(srow[0] or "") if srow else ""
    s_daily: list[dict] = []
    if store_id:
        c.execute(
            """
            SELECT store_id, snap_date, shop_fans, shop_sales, shop_fans_delta,
                   scan_owner, scan_engine, source, created_at
            FROM premium_store_daily WHERE store_id=?
            ORDER BY snap_date
            """,
            (store_id,),
        )
        s_daily = [_row_dict(c, r) for r in c.fetchall()]
    conn.close()
    if not g_daily and not s_daily:
        return {"goods_id": goods_id, "skipped": True}
    resp = _post_json(
        "/api/v1/sync/premium-snapshots-backfill",
        {
            "client_id": _client_id(),
            "goods_id": goods_id,
            "goods_daily": g_daily,
            "store_daily": s_daily,
        },
    )
    _log(f"backfill upload {goods_id}: {resp}", log_func)
    return resp


def backfill_pending(
    max_days: int = 90,
    limit: int = 0,
    upload_cloud: bool = True,
    log_func=None,
) -> dict:
    from xhs_db_schema import DB_PATH
    from xhs_premium_daily import backfill_pending_snapshots

    local = backfill_pending_snapshots(
        main_path=DB_PATH,
        max_days=max_days,
        limit=limit,
        log_func=lambda m: _log(m, log_func),
    )
    if not upload_cloud or not _api_base():
        return local
    conn = connect()
    c = conn.cursor()
    c.execute(
        """
        SELECT goods_id FROM premium_sync_state
        WHERE snapshots_backfill_done=1
        ORDER BY updated_at DESC
        """
    )
    gids = [r[0] for r in c.fetchall()]
    if limit > 0:
        gids = gids[:limit]
    conn.close()
    uploaded = 0
    for gid in gids:
        try:
            push_snapshots_backfill_for_goods(gid, log_func=log_func)
            uploaded += 1
        except Exception as e:
            _log(f"upload {gid} 失败: {e}", log_func)
    local["cloud_uploaded"] = uploaded
    return local


def pull_premium_changes(log_func=None) -> dict:
    since = _load_local_version()
    resp = _get_json("/api/v1/sync/premium-changes", {"since": since, "limit": 500})
    rows = resp.get("rows") or []
    latest = int(resp.get("latest_version") or since)
    if not rows:
        _log(f"pull: 无新变更 (since={since})", log_func)
        return {"pulled": 0, "latest_version": latest}

    conn = connect()
    c = conn.cursor()
    n = 0
    scan_cols = {
        "sold_num", "velocity_1d", "actual_velocity_1d", "deal_price",
        "shop_fans", "shop_sales", "shop_fans_delta_1d", "last_metric_scan",
        "last_app_scan", "last_scan_engine", "title", "store_id", "store_name",
    }
    for row in rows:
        gid = row.get("goods_id")
        if not gid:
            continue
        sets = []
        vals = []
        for col in scan_cols:
            if col in row and row[col] is not None:
                sets.append(f"{col}=?")
                vals.append(row[col])
        if not sets:
            continue
        vals.append(str(gid))
        c.execute(
            f"UPDATE premium_goods SET {', '.join(sets)}, updated_at=? WHERE goods_id=?",
            (*vals[:-1], row.get("updated_at") or "", vals[-1]),
        )
        n += c.rowcount
    conn.commit()
    conn.close()
    _save_local_version(latest)
    _log(f"pull: {n} 行写回本地, version→{latest}", log_func)
    return {"pulled": n, "latest_version": latest}


def push_daily(
    since_date: str = "",
    limit: int = 0,
    batch_size: int = 500,
    log_func=None,
) -> dict:
    """批量推送 premium_goods_daily 日快照到云（历史增量同步）。"""
    conn = connect()
    c = conn.cursor()
    ph = "%s" if premium_backend() == "postgresql" else "?"
    sql = """
        SELECT goods_id, snap_date, sold_num, deal_price, delta, actual_delta,
               velocity_1d, source, created_at
        FROM premium_goods_daily
    """
    params: list = []
    if since_date:
        sql += f" WHERE snap_date >= {ph}"
        params.append(since_date)
    sql += " ORDER BY snap_date, goods_id"
    if limit > 0:
        sql += f" LIMIT {int(limit)}"
    c.execute(sql, params)
    rows = [_row_dict(c, r) for r in c.fetchall()]
    conn.close()
    if not rows:
        _log("push-daily: 无待推送日快照", log_func)
        return {"rows": 0, "upserted": 0}
    total = 0
    batches = (len(rows) + batch_size - 1) // batch_size
    for i in range(0, len(rows), batch_size):
        chunk = rows[i : i + batch_size]
        resp = _post_json(
            "/api/v1/sync/premium-daily-upsert",
            {
                "client_id": _client_id(),
                "batch_id": f"daily-{i // batch_size + 1}",
                "rows": chunk,
                "final_batch": (i + batch_size) >= len(rows),
            },
        )
        total += int(resp.get("rows_upserted") or len(chunk))
        _log(
            f"push-daily batch {i // batch_size + 1}/{batches}: {len(chunk)} → 累计 {total:,}",
            log_func,
        )
    return {"rows": len(rows), "upserted": total, "since_date": since_date or "all"}


def sync_full_to_cloud(since_date: str = "", log_func=None) -> dict:
    """精品全量上云：当前行 + 日快照 + 历史 backfill（规格书主路径）。"""
    upsert = push_upsert(log_func=log_func)
    daily = push_daily(since_date=since_date, log_func=log_func)
    backfill = backfill_pending(upload_cloud=True, log_func=log_func)
    pull = pull_premium_changes(log_func=log_func)
    return {"upsert": upsert, "daily": daily, "backfill": backfill, "pull": pull}


def push_all(log_func=None) -> dict:
    upsert = push_upsert(log_func=log_func)
    pull = pull_premium_changes(log_func=log_func)
    return {"upsert": upsert, "pull": pull}


def main():
    import argparse

    ap = argparse.ArgumentParser(description="精品库双向同步 v1.6")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-days", type=int, default=90)
    ap.add_argument("--goods-id", default="")
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--since", default="", help="push-daily/sync-full: 仅推送 snap_date>=该日期")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("push", help="POST premium-upsert")
    sub.add_parser("pull", help="GET premium-changes → 写回本地")
    sub.add_parser("push-all", help="push + pull")
    p_daily = sub.add_parser("push-daily", help="批量 POST premium_goods_daily")
    p_daily.add_argument("--batch-size", type=int, default=500)
    p_sync = sub.add_parser("sync-full", help="push + push-daily + backfill + pull")
    p_bf = sub.add_parser("backfill", help="本地 backfill + 可选上云")
    p_bf.add_argument("--pending", action="store_true")
    args = ap.parse_args()

    if args.cmd == "push":
        push_upsert(limit=args.limit)
    elif args.cmd == "pull":
        pull_premium_changes()
    elif args.cmd == "push-all":
        push_all()
    elif args.cmd == "push-daily":
        push_daily(since_date=args.since, limit=args.limit, batch_size=args.batch_size)
    elif args.cmd == "sync-full":
        sync_full_to_cloud(since_date=args.since)
    elif args.cmd == "backfill":
        if args.goods_id:
            from xhs_db_schema import DB_PATH
            from xhs_premium_daily import backfill_premium_snapshots_for_goods

            conn = connect()
            main = __import__("xhs_db_schema", fromlist=["_db_connect"])._db_connect(DB_PATH)
            r = backfill_premium_snapshots_for_goods(conn, main, args.goods_id, max_days=args.max_days)
            conn.close()
            main.close()
            if not args.no_upload:
                push_snapshots_backfill_for_goods(args.goods_id)
            print(r)
        elif args.pending:
            backfill_pending(max_days=args.max_days, limit=args.limit, upload_cloud=not args.no_upload)
        else:
            ap.error("backfill 需 --pending 或 --goods-id")


if __name__ == "__main__":
    main()
