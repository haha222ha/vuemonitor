# -*- coding: utf-8 -*-
"""
PostgreSQL 业务库（会员 / 报告索引 / 监控池）。
环境变量 XHS_DATABASE_URL=postgresql://user:pass@127.0.0.1:5432/你的库名
"""
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta

import psycopg2
import psycopg2.extras

from cloud_deploy.cloud_api.config import get_settings

psycopg2.extras.register_uuid()


def _conn():
    s = get_settings()
    if not s.xhs_database_url:
        raise RuntimeError("未配置 XHS_DATABASE_URL")
    conn = psycopg2.connect(s.xhs_database_url)
    conn.autocommit = False
    return conn


def init_db() -> None:
    conn = _conn()
    try:
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
                    shop_fsr NUMERIC(8,4),
                    goods_fsr NUMERIC(8,4),
                    behavior VARCHAR(128),
                    is_virtual BOOLEAN,
                    base_hours NUMERIC(8,2),
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
                CREATE TABLE IF NOT EXISTS sync_checkpoints (
                    client_id VARCHAR(64) PRIMARY KEY,
                    last_report_date DATE,
                    last_sold_hist_date DATE,
                    last_goods_id VARCHAR(32),
                    meta_json JSONB,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_rdi_date_v1d ON report_daily_items(report_date, v1d DESC);
                CREATE INDEX IF NOT EXISTS idx_rdi_goods ON report_daily_items(goods_id, report_date DESC);
                CREATE INDEX IF NOT EXISTS idx_monitor_active ON monitor_goods(monitor_status, last_v1d DESC);
                CREATE INDEX IF NOT EXISTS idx_monitor_v1d ON monitor_goods(last_v1d DESC) WHERE last_v1d > 0;
                """
            )
        conn.commit()
    finally:
        conn.close()


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
                exp = datetime.now() + timedelta(days=3650)
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
                """SELECT u.id, u.username, m.expires_at, m.status
                   FROM users u JOIN memberships m ON m.user_id=u.id
                   WHERE u.id=%s ORDER BY m.id DESC LIMIT 1""",
                (user_id,),
            )
            row = c.fetchone()
            if not row or row["status"] != "active":
                return None
            if row["expires_at"] < datetime.now():
                return None
            return {
                "id": row["id"],
                "username": row["username"],
                "expires_at": row["expires_at"].strftime("%Y-%m-%d %H:%M:%S"),
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
            if not m or m["status"] != "active" or m["expires_at"] < datetime.now():
                return None
            return {
                "id": u["id"],
                "username": u["username"],
                "expires_at": m["expires_at"].strftime("%Y-%m-%d %H:%M:%S"),
            }
    finally:
        conn.close()


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
                        "summary": meta.get("filter_label") or meta.get("scope_label") or "",
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
