# -*- coding: utf-8 -*-
"""SQLite 业务库（未配置 PG 时使用）。"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta

from cloud_deploy.cloud_api.config import get_settings


def _conn():
    s = get_settings()
    os.makedirs(os.path.dirname(s.xhs_cloud_api_db), exist_ok=True)
    conn = sqlite3.connect(s.xhs_cloud_api_db, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = _conn()
    c = conn.cursor()
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS memberships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_code TEXT DEFAULT 'monthly',
            activated_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS report_archives (
            report_date TEXT NOT NULL,
            archive_type TEXT NOT NULL,
            storage_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_size_bytes INTEGER,
            sha256 TEXT,
            row_count INTEGER,
            meta_json TEXT,
            status TEXT DEFAULT 'published',
            published_at TEXT,
            PRIMARY KEY (report_date, archive_type)
        );
        CREATE TABLE IF NOT EXISTS report_download_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            report_date TEXT,
            archive_type TEXT,
            downloaded_at TEXT NOT NULL,
            ip TEXT
        );
        """
    )
    conn.commit()
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
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=?", (s.xhs_cloud_admin_user,))
    row = c.fetchone()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not row:
        c.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?,?,?)",
            (s.xhs_cloud_admin_user, _hash_password(s.xhs_cloud_admin_pass), now),
        )
        uid = c.lastrowid
        exp = (datetime.now() + timedelta(days=3650)).strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            """INSERT INTO memberships (user_id, plan_code, activated_at, expires_at, status)
               VALUES (?,?,?,?,?)""",
            (uid, "admin", now, exp, "active"),
        )
        conn.commit()
    conn.close()


def get_active_member(user_id: int) -> dict | None:
    conn = _conn()
    c = conn.cursor()
    c.execute(
        """SELECT u.id, u.username, m.expires_at, m.status
           FROM users u JOIN memberships m ON m.user_id=u.id
           WHERE u.id=? ORDER BY m.id DESC LIMIT 1""",
        (user_id,),
    )
    row = c.fetchone()
    conn.close()
    if not row or row["status"] != "active":
        return None
    if row["expires_at"] < datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
        return None
    return {"id": row["id"], "username": row["username"], "expires_at": row["expires_at"]}


def authenticate(username: str, password: str) -> dict | None:
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT id, username, password_hash FROM users WHERE username=?", (username,))
    u = c.fetchone()
    if not u or not _verify_password(password, u["password_hash"]):
        conn.close()
        return None
    c.execute(
        "SELECT status, expires_at FROM memberships WHERE user_id=? ORDER BY id DESC LIMIT 1",
        (u["id"],),
    )
    m = c.fetchone()
    conn.close()
    if not m or m["status"] != "active":
        return None
    if m["expires_at"] < datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
        return None
    return {"id": u["id"], "username": u["username"], "expires_at": m["expires_at"]}


def list_archives(archive_type: str = "member_daily_zip") -> list[dict]:
    conn = _conn()
    c = conn.cursor()
    c.execute(
        """SELECT report_date, archive_type, file_name, file_size_bytes, row_count,
                  meta_json, published_at, status
           FROM report_archives
           WHERE archive_type=? AND status='published'
           ORDER BY report_date DESC""",
        (archive_type,),
    )
    rows = []
    for r in c.fetchall():
        meta = {}
        try:
            meta = json.loads(r["meta_json"] or "{}")
        except Exception:
            pass
        rows.append(
            {
                "report_date": r["report_date"],
                "archive_type": r["archive_type"],
                "file_name": r["file_name"],
                "file_size_bytes": r["file_size_bytes"],
                "row_count": r["row_count"],
                "summary": meta.get("filter_label") or meta.get("scope_label") or "",
                "published_at": r["published_at"],
            }
        )
    conn.close()
    return rows


def get_archive_path(report_date: str, archive_type: str = "member_daily_zip") -> str | None:
    conn = _conn()
    c = conn.cursor()
    c.execute(
        """SELECT storage_path FROM report_archives
           WHERE report_date=? AND archive_type=? AND status='published'""",
        (report_date, archive_type),
    )
    r = c.fetchone()
    conn.close()
    return r["storage_path"] if r else None


def log_download(user_id: int, report_date: str, archive_type: str, ip: str) -> None:
    conn = _conn()
    conn.execute(
        """INSERT INTO report_download_logs (user_id, report_date, archive_type, downloaded_at, ip)
           VALUES (?,?,?,?,?)""",
        (user_id, report_date, archive_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ip),
    )
    conn.commit()
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
    c = conn.cursor()
    c.execute(
        """INSERT INTO report_archives (
               report_date, archive_type, storage_path, file_name,
               file_size_bytes, sha256, row_count, meta_json, status, published_at
           ) VALUES (?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(report_date, archive_type) DO UPDATE SET
               storage_path=excluded.storage_path,
               file_name=excluded.file_name,
               file_size_bytes=excluded.file_size_bytes,
               sha256=excluded.sha256,
               row_count=excluded.row_count,
               meta_json=excluded.meta_json,
               published_at=excluded.published_at""",
        (
            report_date,
            archive_type,
            storage_path,
            file_name,
            file_size,
            sha256,
            row_count,
            json.dumps(meta, ensure_ascii=False),
            "published",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()
