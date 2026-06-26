# -*- coding: utf-8 -*-
"""
PostgreSQL 业务库（会员 / 报告索引 / 监控池）。
环境变量 XHS_DATABASE_URL=postgresql://user:pass@127.0.0.1:5432/你的库名
"""
from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone

import psycopg2
import psycopg2.extras
from psycopg2 import errors as pg_errors

from cloud_deploy.cloud_api.config import get_settings

psycopg2.extras.register_uuid()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _days_until(dt: datetime) -> int:
    return max(0, (_as_utc(dt) - _now()).days)


def _conn():
    s = get_settings()
    if not s.xhs_database_url:
        raise RuntimeError("未配置 XHS_DATABASE_URL")
    conn = psycopg2.connect(s.xhs_database_url)
    conn.autocommit = False
    return conn


_init_db_lock = threading.Lock()
_init_db_ready = False
_INIT_DB_ADVISORY_LOCK_KEY = 842001


def init_db() -> None:
    """初始化 schema（进程内只执行一次；跨进程用 PG advisory lock 串行迁移）。"""
    global _init_db_ready
    if _init_db_ready:
        return
    with _init_db_lock:
        if _init_db_ready:
            return
        for attempt in range(6):
            conn = _conn()
            locked = False
            try:
                with conn.cursor() as c:
                    c.execute("SELECT pg_advisory_lock(%s)", (_INIT_DB_ADVISORY_LOCK_KEY,))
                locked = True
                _init_db_on_conn(conn)
                conn.commit()
                _init_db_ready = True
                return
            except pg_errors.DeadlockDetected:
                try:
                    conn.rollback()
                except Exception:
                    pass
                if attempt >= 5:
                    raise
                time.sleep(0.4 * (attempt + 1))
            finally:
                if locked:
                    try:
                        with conn.cursor() as c:
                            c.execute("SELECT pg_advisory_unlock(%s)", (_INIT_DB_ADVISORY_LOCK_KEY,))
                        conn.commit()
                    except Exception:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                conn.close()


def _init_db_on_conn(conn) -> None:
        with conn.cursor() as c:
            c.execute("CREATE SCHEMA IF NOT EXISTS xhs_monitor")
            c.execute("SET search_path TO xhs_monitor, public")
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(64) UNIQUE NOT NULL,
                    password_hash VARCHAR(128) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS memberships (
                    id SERIAL PRIMARY KEY,
                    user_id INT NOT NULL REFERENCES users(id),
                    plan_code VARCHAR(32) DEFAULT 'monthly',
                    activated_at TIMESTAMPTZ NOT NULL,
                    expires_at TIMESTAMPTZ NOT NULL,
                    status VARCHAR(16) DEFAULT 'active'
                );
                CREATE TABLE IF NOT EXISTS auth_codes (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(32) UNIQUE NOT NULL,
                    plan_code VARCHAR(32) NOT NULL DEFAULT 'monthly',
                    duration_days INT NOT NULL DEFAULT 30,
                    max_activations INT NOT NULL DEFAULT 1,
                    current_activations INT NOT NULL DEFAULT 0,
                    status VARCHAR(16) NOT NULL DEFAULT 'unused',
                    note TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    expires_at TIMESTAMPTZ
                );
                CREATE TABLE IF NOT EXISTS auth_code_activations (
                    id SERIAL PRIMARY KEY,
                    auth_code_id INT NOT NULL REFERENCES auth_codes(id),
                    user_id INT NOT NULL REFERENCES users(id),
                    activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(auth_code_id, user_id)
                );
                CREATE TABLE IF NOT EXISTS report_archives (
                    report_date DATE NOT NULL,
                    archive_type VARCHAR(32) NOT NULL,
                    storage_path TEXT NOT NULL,
                    file_name VARCHAR(256) NOT NULL,
                    file_size_bytes BIGINT,
                    sha256 VARCHAR(64),
                    row_count INT,
                    meta_json JSONB,
                    status VARCHAR(16) DEFAULT 'published',
                    published_at TIMESTAMPTZ,
                    PRIMARY KEY (report_date, archive_type)
                );
                CREATE TABLE IF NOT EXISTS report_download_logs (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INT,
                    report_date DATE,
                    archive_type VARCHAR(32),
                    downloaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    ip INET
                );
                CREATE TABLE IF NOT EXISTS report_daily_meta (
                    report_date DATE PRIMARY KEY,
                    row_count INT,
                    virtual_count INT,
                    physical_count INT,
                    meta_json JSONB,
                    source VARCHAR(32),
                    generated_at TIMESTAMPTZ,
                    synced_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS monitor_goods (
                    goods_id VARCHAR(32) PRIMARY KEY,
                    title TEXT,
                    is_virtual BOOLEAN,
                    pool VARCHAR(16),
                    tier VARCHAR(16),
                    monitor_status VARCHAR(16) NOT NULL DEFAULT 'active',
                    first_tracked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    first_report_date DATE,
                    last_report_date DATE,
                    last_v1d NUMERIC(12,2) DEFAULT 0,
                    last_actual_v1d NUMERIC(12,2) DEFAULT 0,
                    peak_v1d NUMERIC(12,2) DEFAULT 0,
                    last_sold INT DEFAULT 0,
                    store_id VARCHAR(64),
                    store_name VARCHAR(256),
                    priority_score NUMERIC(12,2) DEFAULT 0,
                    source VARCHAR(32) DEFAULT 'daily_report',
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS report_daily_items (
                    report_date DATE NOT NULL,
                    goods_id VARCHAR(32) NOT NULL,
                    rank_no INT,
                    title TEXT,
                    price NUMERIC(12,2),
                    sold INT,
                    v1h NUMERIC(12,2),
                    v6h NUMERIC(12,2),
                    actual_v1d NUMERIC(12,2),
                    v1d NUMERIC(12,2),
                    actual_gr NUMERIC(12,4),
                    gr NUMERIC(12,4),
                    actual_vsr NUMERIC(12,4),
                    vsr NUMERIC(12,4),
                    acc NUMERIC(12,4),
                    burst NUMERIC(12,2),
                    pool VARCHAR(16),
                    first_seen TIMESTAMPTZ,
                    store_id VARCHAR(64),
                    store_name VARCHAR(256),
                    shelf_time TIMESTAMPTZ,
                    shop_sales INT,
                    shop_fans INT,
                    shop_fsr NUMERIC(12,4),
                    goods_fsr NUMERIC(12,4),
                    behavior TEXT,
                    is_virtual BOOLEAN,
                    base_hours NUMERIC(12,2),
                    base_at TIMESTAMPTZ,
                    anomaly VARCHAR(64),
                    PRIMARY KEY (report_date, goods_id)
                );
                CREATE TABLE IF NOT EXISTS goods_sold_daily (
                    goods_id VARCHAR(32) NOT NULL,
                    snapshot_date DATE NOT NULL,
                    sold_num INT NOT NULL,
                    deal_price NUMERIC(12,2),
                    delta INT,
                    source VARCHAR(32) DEFAULT 'local_sync',
                    PRIMARY KEY (goods_id, snapshot_date)
                );
                CREATE TABLE IF NOT EXISTS goods_metrics_daily (
                    goods_id VARCHAR(32) NOT NULL,
                    metric_date DATE NOT NULL,
                    v1d NUMERIC(12,2),
                    actual_v1d NUMERIC(12,2),
                    gr NUMERIC(12,4),
                    burst NUMERIC(12,2),
                    pool VARCHAR(16),
                    PRIMARY KEY (goods_id, metric_date)
                );
                CREATE TABLE IF NOT EXISTS goods_sync_state (
                    goods_id VARCHAR(32) PRIMARY KEY,
                    sold_daily_backfill_done BOOLEAN DEFAULT FALSE,
                    sold_snapshots_backfill_done BOOLEAN DEFAULT FALSE,
                    sold_daily_row_count INT DEFAULT 0,
                    sold_snapshots_row_count INT DEFAULT 0,
                    last_backfill_at TIMESTAMPTZ,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS goods_sold_snapshots (
                    goods_id VARCHAR(32) NOT NULL,
                    snapshot_time TIMESTAMPTZ NOT NULL,
                    sold_num INT,
                    data_source VARCHAR(32) DEFAULT 'local_sync',
                    PRIMARY KEY (goods_id, snapshot_time)
                );
                CREATE TABLE IF NOT EXISTS monitor_rules (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(128),
                    enabled BOOLEAN DEFAULT TRUE,
                    rule_json JSONB NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS monitor_alerts (
                    id BIGSERIAL PRIMARY KEY,
                    goods_id VARCHAR(32),
                    rule_id INT REFERENCES monitor_rules(id),
                    alert_type VARCHAR(64),
                    payload_json JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS sync_checkpoints (
                    client_id VARCHAR(64) PRIMARY KEY,
                    last_report_date DATE,
                    last_sold_hist_date DATE,
                    last_goods_id VARCHAR(32),
                    meta_json JSONB,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS full_sold_queue (
                    goods_id VARCHAR(32) PRIMARY KEY,
                    title TEXT DEFAULT '',
                    sold_num INT DEFAULT 0,
                    velocity_1d NUMERIC(12,2) DEFAULT 0,
                    pool VARCHAR(16) DEFAULT 'WATCH',
                    last_seen TIMESTAMPTZ,
                    queue_date DATE NOT NULL,
                    last_sync_at TIMESTAMPTZ,
                    sync_fail_count INT DEFAULT 0,
                    frozen_at TIMESTAMPTZ,
                    freeze_code INT DEFAULT 0,
                    seeded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_fsq_pending
                    ON full_sold_queue (queue_date, last_sync_at, frozen_at, velocity_1d);
                CREATE INDEX IF NOT EXISTS idx_rdi_date_v1d ON report_daily_items(report_date, v1d DESC);
                CREATE INDEX IF NOT EXISTS idx_rdi_goods ON report_daily_items(goods_id, report_date DESC);
                CREATE INDEX IF NOT EXISTS idx_monitor_active ON monitor_goods(monitor_status, last_v1d DESC);
                CREATE INDEX IF NOT EXISTS idx_monitor_v1d ON monitor_goods(last_v1d DESC) WHERE last_v1d > 0;
                CREATE INDEX IF NOT EXISTS idx_gss_time ON goods_sold_snapshots(snapshot_time);
                CREATE INDEX IF NOT EXISTS idx_gss_goods ON goods_sold_snapshots(goods_id, snapshot_time DESC);
                CREATE INDEX IF NOT EXISTS idx_ma_goods ON monitor_alerts(goods_id, created_at DESC);
                """
            )
            _migrate_legacy_columns(c)
            _seed_default_rules(c)
            try:
                from cloud_deploy.cloud_api.premium_schema_pg import init_premium_pg_schema

                init_premium_pg_schema(conn)
            except Exception:
                pass


def _migrate_legacy_columns(c) -> None:
    """旧库可能缺 status/published_at 列，补全以免 admin/stats 500。"""
    c.execute(
        "ALTER TABLE report_archives ADD COLUMN IF NOT EXISTS status VARCHAR(16) DEFAULT 'published'"
    )
    c.execute(
        "ALTER TABLE report_archives ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ"
    )
    # gen_report 的 shop_fsr/goods_fsr 可达 10^5+，旧表 NUMERIC(8,4) 会 overflow
    for col, typ in (
        ("shop_fsr", "NUMERIC(12,4)"),
        ("goods_fsr", "NUMERIC(12,4)"),
        ("base_hours", "NUMERIC(12,2)"),
        ("behavior", "TEXT"),
    ):
        c.execute(
            f"""
            DO $$ BEGIN
                ALTER TABLE report_daily_items ALTER COLUMN {col} TYPE {typ};
            EXCEPTION WHEN others THEN NULL;
            END $$;
            """
        )
    c.execute(
        "ALTER TABLE monitor_goods ADD COLUMN IF NOT EXISTS last_scan_at TIMESTAMPTZ"
    )
    c.execute(
        "ALTER TABLE monitor_goods ADD COLUMN IF NOT EXISTS last_scan_status VARCHAR(16)"
    )
    c.execute(
        "ALTER TABLE monitor_goods ADD COLUMN IF NOT EXISTS last_scan_engine VARCHAR(32)"
    )
    c.execute("ALTER TABLE monitor_goods ADD COLUMN IF NOT EXISTS shop_sales INT")
    c.execute("ALTER TABLE monitor_goods ADD COLUMN IF NOT EXISTS shop_fans INT")
    c.execute("ALTER TABLE monitor_goods ADD COLUMN IF NOT EXISTS first_seen TIMESTAMPTZ")
    c.execute("ALTER TABLE monitor_goods ADD COLUMN IF NOT EXISTS scan_claim_by VARCHAR(64)")
    c.execute("ALTER TABLE monitor_goods ADD COLUMN IF NOT EXISTS scan_claim_until TIMESTAMPTZ")
    c.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_monitor_scan_pending
            ON monitor_goods (monitor_status, last_scan_at NULLS FIRST, priority_score DESC)
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS daemon_scan_stats (
            id BIGSERIAL PRIMARY KEY,
            run_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            batch_size INT,
            ok INT,
            fail INT,
            risk INT,
            frozen INT,
            wall_ms INT,
            note TEXT
        )
        """
    )


def _seed_default_rules(c) -> None:
    c.execute("SELECT COUNT(*) FROM monitor_rules")
    if c.fetchone()[0] > 0:
        return
    defaults = [
        ("R01_burst_pool", {"id": "R01", "when": {"last_v1d_gte": 50, "pool_not": "BURST"}, "action": {"set_pool": "BURST", "priority_boost": 100}}),
        ("R02_idle_zero", {"id": "R02", "when": {"zero_v1d_days_gte": 7}, "action": {"set_status": "idle"}}),
        ("R03_drop_alert", {"id": "R03", "when": {"actual_v1d_drop_pct_gte": 80}, "action": {"alert_type": "drop"}}),
        ("R04_delisted", {"id": "R04", "when": {"scan_status": "frozen"}, "action": {"set_status": "delisted", "stop_scan": True}}),
    ]
    for name, rule in defaults:
        c.execute(
            "INSERT INTO monitor_rules (name, enabled, rule_json) VALUES (%s, TRUE, %s)",
            (name, json.dumps(rule, ensure_ascii=False)),
        )


def _hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return f"{salt}${digest}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    return _hash_password(password, salt).split("$", 1)[1] == digest


def ensure_admin() -> None:
    s = get_settings()
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("SET search_path TO xhs_monitor, public")
            c.execute("SELECT id FROM users WHERE username=%s", (s.xhs_cloud_admin_user,))
            if not c.fetchone():
                c.execute(
                    "INSERT INTO users (username, password_hash) VALUES (%s,%s) RETURNING id",
                    (s.xhs_cloud_admin_user, _hash_password(s.xhs_cloud_admin_pass)),
                )
                uid = c.fetchone()["id"]
                exp = _now() + timedelta(days=3650)
                c.execute(
                    """INSERT INTO memberships (user_id, plan_code, activated_at, expires_at, status)
                       VALUES (%s,'admin',NOW(),%s,'active')""",
                    (uid, exp),
                )
        conn.commit()
    finally:
        conn.close()


def get_active_member(user_id: int) -> dict | None:
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("SET search_path TO xhs_monitor, public")
            c.execute(
                """SELECT u.id, u.username, m.expires_at, m.status, m.plan_code
                   FROM users u JOIN memberships m ON m.user_id=u.id
                   WHERE u.id=%s ORDER BY m.id DESC LIMIT 1""",
                (user_id,),
            )
            row = c.fetchone()
            if not row or row["status"] != "active":
                return None
            c.execute(
                "SELECT 1 FROM memberships WHERE user_id=%s AND expires_at > NOW()",
                (user_id,),
            )
            if not c.fetchone():
                return None
            return {
                "id": row["id"],
                "username": row["username"],
                "expires_at": row["expires_at"].strftime("%Y-%m-%d %H:%M:%S"),
                "plan_code": row.get("plan_code") or "monthly",
                "days_remaining": _days_until(row["expires_at"]),
            }
    finally:
        conn.close()


def authenticate(username: str, password: str) -> dict | None:
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("SET search_path TO xhs_monitor, public")
            c.execute("SELECT id, username, password_hash FROM users WHERE username=%s", (username,))
            u = c.fetchone()
            if not u or not _verify_password(password, u["password_hash"]):
                return None
            c.execute(
                "SELECT status, expires_at FROM memberships WHERE user_id=%s ORDER BY id DESC LIMIT 1",
                (u["id"],),
            )
            m = c.fetchone()
            if not m or m["status"] != "active":
                return None
            c.execute(
                "SELECT 1 FROM memberships WHERE user_id=%s AND expires_at > NOW()",
                (u["id"],),
            )
            if not c.fetchone():
                return None
            return {
                "id": u["id"],
                "username": u["username"],
                "expires_at": m["expires_at"].strftime("%Y-%m-%d %H:%M:%S"),
            }
    finally:
        conn.close()


def archive_display_label(
    report_date: str, archive_type: str = "member_daily_zip", file_name: str = ""
) -> str:
    """会员报告库列表展示名：全量0618 / 周报0618 / 月报202606。"""
    date = str(report_date)[:10]
    mmdd = date.replace("-", "")[4:]
    if file_name:
        base = file_name.rsplit(".", 1)[0]
        if base.startswith(("全量", "周报", "月报")):
            return base
    if archive_type == "member_weekly_zip":
        return f"周报{mmdd}"
    if archive_type == "member_monthly_zip":
        return f"月报{date[:7].replace('-', '')}"
    return f"全量{mmdd}"


def list_archives(archive_type: str = "member_daily_zip") -> list[dict]:
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("SET search_path TO xhs_monitor, public")
            c.execute(
                """SELECT report_date, archive_type, file_name, file_size_bytes,
                          row_count, meta_json, published_at, status
                   FROM report_archives
                   WHERE archive_type=%s AND status='published'
                   ORDER BY report_date DESC""",
                (archive_type,),
            )
            rows = []
            for r in c.fetchall():
                meta = r["meta_json"] or {}
                if isinstance(meta, str):
                    meta = json.loads(meta)
                rows.append(
                    {
                        "report_date": r["report_date"].isoformat(),
                        "archive_type": r["archive_type"],
                        "file_name": r["file_name"],
                        "file_size_bytes": r["file_size_bytes"],
                        "row_count": r["row_count"],
                        "summary": archive_display_label(
                            r["report_date"].isoformat(),
                            r["archive_type"],
                            r["file_name"] or "",
                        ),
                        "published_at": r["published_at"].isoformat() if r["published_at"] else "",
                    }
                )
            return rows
    finally:
        conn.close()


def get_archive_path(report_date: str, archive_type: str = "member_daily_zip") -> str | None:
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("SET search_path TO xhs_monitor, public")
            c.execute(
                """SELECT storage_path FROM report_archives
                   WHERE report_date=%s AND archive_type=%s AND status='published'""",
                (report_date, archive_type),
            )
            r = c.fetchone()
            return r["storage_path"] if r else None
    finally:
        conn.close()


def log_download(user_id: int, report_date: str, archive_type: str, ip: str) -> None:
    conn = _conn()
    try:
        with conn.cursor() as c:
            c.execute("SET search_path TO xhs_monitor, public")
            c.execute(
                """INSERT INTO report_download_logs (user_id, report_date, archive_type, ip)
                   VALUES (%s,%s,%s,%s)""",
                (user_id, report_date, archive_type, ip or None),
            )
        conn.commit()
    finally:
        conn.close()


def upsert_report_archive(
    report_date: str,
    archive_type: str,
    storage_path: str,
    file_name: str,
    file_size: int,
    sha256: str,
    row_count: int,
    meta: dict,
) -> None:
    conn = _conn()
    try:
        with conn.cursor() as c:
            c.execute("SET search_path TO xhs_monitor, public")
            c.execute(
                """INSERT INTO report_archives (
                       report_date, archive_type, storage_path, file_name,
                       file_size_bytes, sha256, row_count, meta_json, status, published_at
                   ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'published',NOW())
                   ON CONFLICT (report_date, archive_type) DO UPDATE SET
                       storage_path=EXCLUDED.storage_path,
                       file_name=EXCLUDED.file_name,
                       file_size_bytes=EXCLUDED.file_size_bytes,
                       sha256=EXCLUDED.sha256,
                       row_count=EXCLUDED.row_count,
                       meta_json=EXCLUDED.meta_json,
                       published_at=NOW()""",
                (
                    report_date,
                    archive_type,
                    storage_path,
                    file_name,
                    file_size,
                    sha256,
                    row_count,
                    json.dumps(meta, ensure_ascii=False),
                ),
            )
        conn.commit()
    finally:
        conn.close()


PLAN_LABELS = {
    "weekly": "周会员",
    "monthly": "月度会员",
    "yearly": "年度会员",
    "admin": "管理员",
}


def _normalize_code(code: str) -> str:
    return code.strip().upper().replace(" ", "").replace("-", "")


def _gen_auth_code() -> str:
    return f"XHS-{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"


def generate_auth_codes(
    count: int = 1,
    plan_code: str = "monthly",
    duration_days: int = 30,
    max_activations: int = 1,
    note: str = "",
) -> list[str]:
    conn = _conn()
    codes = []
    try:
        with conn.cursor() as c:
            c.execute("SET search_path TO xhs_monitor, public")
            for _ in range(max(1, count)):
                code = _gen_auth_code()
                c.execute(
                    """INSERT INTO auth_codes
                       (code, plan_code, duration_days, max_activations, note)
                       VALUES (%s,%s,%s,%s,%s)""",
                    (code, plan_code, duration_days, max_activations, note or None),
                )
                codes.append(code)
        conn.commit()
        return codes
    finally:
        conn.close()


def list_auth_codes(limit: int = 100, status: str | None = None) -> list[dict]:
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("SET search_path TO xhs_monitor, public")
            sql = (
                """SELECT ac.id, ac.code, ac.plan_code, ac.duration_days, ac.max_activations,
                          ac.current_activations, ac.status, ac.note, ac.created_at, ac.expires_at,
                          act.first_activated_at,
                          act.activated_usernames,
                          mem.membership_expires_at
                   FROM auth_codes ac
                   LEFT JOIN (
                       SELECT aca.auth_code_id,
                              MIN(aca.activated_at) AS first_activated_at,
                              STRING_AGG(u.username, ', ' ORDER BY aca.activated_at) AS activated_usernames
                       FROM auth_code_activations aca
                       JOIN users u ON u.id = aca.user_id
                       GROUP BY aca.auth_code_id
                   ) act ON act.auth_code_id = ac.id
                   LEFT JOIN (
                       SELECT aca.auth_code_id,
                              MAX(m.expires_at) AS membership_expires_at
                       FROM auth_code_activations aca
                       JOIN memberships m ON m.user_id = aca.user_id
                       GROUP BY aca.auth_code_id
                   ) mem ON mem.auth_code_id = ac.id"""
            )
            params: list = []
            if status:
                sql += " WHERE ac.status = %s"
                params.append(status)
            sql += " ORDER BY ac.id DESC LIMIT %s"
            params.append(limit)
            c.execute(sql, params)
            rows = []
            for r in c.fetchall():
                membership_expires = r["membership_expires_at"]
                days_remaining = None
                if membership_expires:
                    days_remaining = _days_until(membership_expires)
                rows.append(
                    {
                        "id": r["id"],
                        "code": r["code"],
                        "plan_code": r["plan_code"],
                        "plan_label": PLAN_LABELS.get(r["plan_code"], r["plan_code"]),
                        "duration_days": r["duration_days"],
                        "max_activations": r["max_activations"],
                        "current_activations": r["current_activations"],
                        "status": r["status"],
                        "note": r["note"] or "",
                        "created_at": r["created_at"].isoformat() if r["created_at"] else "",
                        "expires_at": r["expires_at"].isoformat() if r["expires_at"] else "",
                        "first_activated_at": (
                            r["first_activated_at"].isoformat() if r["first_activated_at"] else ""
                        ),
                        "activated_usernames": r["activated_usernames"] or "",
                        "membership_expires_at": (
                            membership_expires.isoformat() if membership_expires else ""
                        ),
                        "days_remaining": days_remaining,
                    }
                )
            return rows
    finally:
        conn.close()


def revoke_auth_code(code: str) -> dict:
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("SET search_path TO xhs_monitor, public")
            row = _fetch_auth_code(c, code)
            if not row:
                raise ValueError("授权码不存在")
            if row["status"] == "revoked":
                raise ValueError("授权码已被吊销")
            c.execute("UPDATE auth_codes SET status='revoked' WHERE id=%s", (row["id"],))
        conn.commit()
        return {"code": row["code"], "status": "revoked"}
    finally:
        conn.close()


def get_admin_stats() -> dict:
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("SET search_path TO xhs_monitor, public")
            c.execute("SELECT COUNT(*) AS n FROM users")
            total_members = int(c.fetchone()["n"])
            c.execute(
                """SELECT COUNT(DISTINCT u.id) AS n
                   FROM users u
                   JOIN memberships m ON m.user_id = u.id
                   WHERE m.expires_at > NOW()"""
            )
            active_members = int(c.fetchone()["n"])
            c.execute("SELECT status, COUNT(*) AS n FROM auth_codes GROUP BY status")
            code_by_status = {r["status"]: int(r["n"]) for r in c.fetchall()}
            c.execute(
                """SELECT report_date, file_name
                   FROM report_archives
                   WHERE archive_type = 'member_daily_zip' AND status = 'published'
                   ORDER BY report_date DESC LIMIT 1"""
            )
            latest = c.fetchone()
            c.execute(
                """SELECT COUNT(*) AS n FROM report_archives
                   WHERE archive_type = 'member_daily_zip' AND status = 'published'"""
            )
            archive_count = int(c.fetchone()["n"])
            return {
                "total_members": total_members,
                "active_members": active_members,
                "auth_codes_unused": code_by_status.get("unused", 0),
                "auth_codes_active": code_by_status.get("active", 0),
                "auth_codes_revoked": code_by_status.get("revoked", 0),
                "auth_codes_total": sum(code_by_status.values()),
                "latest_report_date": (
                    latest["report_date"].isoformat() if latest and latest.get("report_date") else None
                ),
                "latest_report_file": latest["file_name"] if latest else None,
                "archive_count": archive_count,
            }
    finally:
        conn.close()


def _fetch_auth_code(c, code: str) -> dict | None:
    norm = _normalize_code(code)
    c.execute(
        """SELECT id, code, plan_code, duration_days, max_activations,
                  current_activations, status, expires_at
           FROM auth_codes
           WHERE REPLACE(REPLACE(UPPER(code), '-', ''), ' ', '') = %s""",
        (norm,),
    )
    return c.fetchone()


def _validate_auth_code_row(row: dict | None) -> dict:
    if not row:
        raise ValueError("授权码不存在")
    if row["status"] == "revoked":
        raise ValueError("授权码已被吊销")
    if row["current_activations"] >= row["max_activations"]:
        raise ValueError("授权码已达最大激活次数")
    if row["expires_at"] and _as_utc(row["expires_at"]) < _now():
        raise ValueError("授权码已过期")
    return row


def _extend_membership(c, user_id: int, plan_code: str, duration_days: int) -> datetime:
    c.execute(
        """SELECT expires_at FROM memberships
           WHERE user_id=%s AND status='active' ORDER BY expires_at DESC LIMIT 1""",
        (user_id,),
    )
    row = c.fetchone()
    now = _now()
    base = now
    if row and row[0] and _as_utc(row[0]) > now:
        base = _as_utc(row[0])
    expires = base + timedelta(days=duration_days)
    c.execute(
        """INSERT INTO memberships (user_id, plan_code, activated_at, expires_at, status)
           VALUES (%s,%s,NOW(),%s,'active')""",
        (user_id, plan_code, expires),
    )
    return expires


def register_with_auth_code(username: str, password: str, code: str) -> dict:
    username = (username or "").strip()
    if len(username) < 3:
        raise ValueError("用户名至少 3 个字符")
    if len(password or "") < 6:
        raise ValueError("密码至少 6 位")
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("SET search_path TO xhs_monitor, public")
            c.execute("SELECT id FROM users WHERE username=%s", (username,))
            if c.fetchone():
                raise ValueError("用户名已存在，请直接登录后使用授权码续费")
            row = _validate_auth_code_row(_fetch_auth_code(c, code))
            c.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s,%s) RETURNING id",
                (username, _hash_password(password)),
            )
            uid = c.fetchone()["id"]
            expires = _extend_membership(c, uid, row["plan_code"], row["duration_days"])
            c.execute(
                "INSERT INTO auth_code_activations (auth_code_id, user_id) VALUES (%s,%s)",
                (row["id"], uid),
            )
            c.execute(
                "UPDATE auth_codes SET current_activations=current_activations+1, status='active' WHERE id=%s",
                (row["id"],),
            )
        conn.commit()
        profile = get_member_profile(uid)
        if profile:
            return profile
        return {
            "id": uid,
            "username": username,
            "expires_at": expires.strftime("%Y-%m-%d %H:%M:%S"),
            "plan_code": row["plan_code"],
            "days_remaining": _days_until(expires),
            "is_active": True,
        }
    finally:
        conn.close()


def renew_with_auth_code(user_id: int, code: str) -> dict:
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
            c.execute("SET search_path TO xhs_monitor, public")
            row = _validate_auth_code_row(_fetch_auth_code(c, code))
            c.execute(
                "SELECT 1 FROM auth_code_activations WHERE auth_code_id=%s AND user_id=%s",
                (row["id"], user_id),
            )
            if c.fetchone():
                raise ValueError("您已使用过此授权码")
            _extend_membership(c, user_id, row["plan_code"], row["duration_days"])
            c.execute(
                "INSERT INTO auth_code_activations (auth_code_id, user_id) VALUES (%s,%s)",
                (row["id"], user_id),
            )
            c.execute(
                "UPDATE auth_codes SET current_activations=current_activations+1, status='active' WHERE id=%s",
                (row["id"],),
            )
        conn.commit()
        return get_member_profile(user_id) or {}
    finally:
        conn.close()


def get_member_profile(user_id: int) -> dict | None:
    member = get_active_member(user_id)
    if not member:
        conn = _conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as c:
                c.execute("SET search_path TO xhs_monitor, public")
                c.execute("SELECT username FROM users WHERE id=%s", (user_id,))
                u = c.fetchone()
                if not u:
                    return None
                c.execute(
                    """SELECT plan_code, expires_at, status FROM memberships
                       WHERE user_id=%s ORDER BY id DESC LIMIT 1""",
                    (user_id,),
                )
                m = c.fetchone()
                if not m:
                    return None
                days = _days_until(m["expires_at"])
                return {
                    "id": user_id,
                    "username": u["username"],
                    "plan_code": m["plan_code"],
                    "plan_label": PLAN_LABELS.get(m["plan_code"], m["plan_code"]),
                    "expires_at": m["expires_at"].strftime("%Y-%m-%d %H:%M:%S"),
                    "status": m["status"],
                    "days_remaining": days,
                    "is_active": False,
                    "expiry_warning": "会员已过期，请使用新授权码续费",
                }
        finally:
            conn.close()
    member["plan_label"] = PLAN_LABELS.get(
        member.get("plan_code", ""), member.get("plan_code", "")
    )
    member["is_active"] = True
    member["status"] = "active"
    days = member.get("days_remaining", 0)
    if days <= 0:
        member["expiry_warning"] = "会员今日到期，请尽快续费"
    elif days <= 7:
        member["expiry_warning"] = f"会员将在 {days} 天后到期"
    else:
        member["expiry_warning"] = ""
    return member


def list_report_library() -> dict:
    from cloud_deploy.reporting.constants import ARCHIVE_DAILY, ARCHIVE_MONTHLY, ARCHIVE_WEEKLY

    daily = list_archives(ARCHIVE_DAILY)
    weekly = list_archives(ARCHIVE_WEEKLY)
    monthly = list_archives(ARCHIVE_MONTHLY)
    return {
        "daily": daily,
        "weekly": weekly,
        "monthly": monthly,
        "total_count": len(daily) + len(weekly) + len(monthly),
    }
