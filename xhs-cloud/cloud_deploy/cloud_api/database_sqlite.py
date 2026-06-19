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
        CREATE TABLE IF NOT EXISTS auth_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            plan_code TEXT NOT NULL DEFAULT 'monthly',
            duration_days INTEGER NOT NULL DEFAULT 30,
            max_activations INTEGER NOT NULL DEFAULT 1,
            current_activations INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'unused',
            note TEXT,
            created_at TEXT NOT NULL,
            expires_at TEXT
        );
        CREATE TABLE IF NOT EXISTS auth_code_activations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            auth_code_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            activated_at TEXT NOT NULL,
            UNIQUE(auth_code_id, user_id)
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
        """SELECT u.id, u.username, m.expires_at, m.status, m.plan_code
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
    exp = datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
    return {
        "id": row["id"],
        "username": row["username"],
        "expires_at": row["expires_at"],
        "plan_code": row["plan_code"] or "monthly",
        "days_remaining": max(0, (exp - datetime.now()).days),
    }


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
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    codes = []
    for _ in range(max(1, count)):
        code = _gen_auth_code()
        c.execute(
            """INSERT INTO auth_codes
               (code, plan_code, duration_days, max_activations, note, created_at)
               VALUES (?,?,?,?,?,?)""",
            (code, plan_code, duration_days, max_activations, note or None, now),
        )
        codes.append(code)
    conn.commit()
    conn.close()
    return codes


def list_auth_codes(limit: int = 100, status: str | None = None) -> list[dict]:
    conn = _conn()
    c = conn.cursor()
    sql = (
        """SELECT code, plan_code, duration_days, max_activations,
                  current_activations, status, note, created_at, expires_at
           FROM auth_codes"""
    )
    params: list = []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    c.execute(sql, params)
    rows = []
    for r in c.fetchall():
        rows.append(
            {
                "code": r["code"],
                "plan_code": r["plan_code"],
                "plan_label": PLAN_LABELS.get(r["plan_code"], r["plan_code"]),
                "duration_days": r["duration_days"],
                "max_activations": r["max_activations"],
                "current_activations": r["current_activations"],
                "status": r["status"],
                "note": r["note"] or "",
                "created_at": r["created_at"] or "",
                "expires_at": r["expires_at"] or "",
            }
        )
    conn.close()
    return rows


def get_admin_stats() -> dict:
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_members = int(c.fetchone()[0])
    c.execute(
        """SELECT COUNT(DISTINCT u.id)
           FROM users u
           JOIN memberships m ON m.user_id = u.id
           WHERE m.expires_at > datetime('now')"""
    )
    active_members = int(c.fetchone()[0])
    c.execute("SELECT status, COUNT(*) FROM auth_codes GROUP BY status")
    code_by_status = {r[0]: int(r[1]) for r in c.fetchall()}
    c.execute(
        """SELECT report_date, file_name
           FROM report_archives
           WHERE archive_type = 'member_daily_zip' AND status = 'published'
           ORDER BY report_date DESC LIMIT 1"""
    )
    latest = c.fetchone()
    c.execute(
        """SELECT COUNT(*) FROM report_archives
           WHERE archive_type = 'member_daily_zip' AND status = 'published'"""
    )
    archive_count = int(c.fetchone()[0])
    conn.close()
    return {
        "total_members": total_members,
        "active_members": active_members,
        "auth_codes_unused": code_by_status.get("unused", 0),
        "auth_codes_active": code_by_status.get("active", 0),
        "auth_codes_revoked": code_by_status.get("revoked", 0),
        "auth_codes_total": sum(code_by_status.values()),
        "latest_report_date": latest[0] if latest else None,
        "latest_report_file": latest[1] if latest else None,
        "archive_count": archive_count,
    }


def _fetch_auth_code(c, code: str):
    norm = _normalize_code(code)
    c.execute("SELECT * FROM auth_codes")
    for r in c.fetchall():
        if _normalize_code(r["code"]) == norm:
            return r
    return None


def _validate_auth_code_row(row) -> dict:
    if not row:
        raise ValueError("授权码不存在")
    if row["status"] == "revoked":
        raise ValueError("授权码已被吊销")
    if row["current_activations"] >= row["max_activations"]:
        raise ValueError("授权码已达最大激活次数")
    if row["expires_at"] and row["expires_at"] < datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
        raise ValueError("授权码已过期")
    return row


def _extend_membership(c, user_id: int, plan_code: str, duration_days: int) -> str:
    now = datetime.now()
    c.execute(
        "SELECT expires_at FROM memberships WHERE user_id=? AND status='active' ORDER BY expires_at DESC LIMIT 1",
        (user_id,),
    )
    row = c.fetchone()
    base = now
    if row and row["expires_at"] > now.strftime("%Y-%m-%d %H:%M:%S"):
        base = datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
    expires = (base + timedelta(days=duration_days)).strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        """INSERT INTO memberships (user_id, plan_code, activated_at, expires_at, status)
           VALUES (?,?,?,?,?)""",
        (user_id, plan_code, now.strftime("%Y-%m-%d %H:%M:%S"), expires, "active"),
    )
    return expires


def register_with_auth_code(username: str, password: str, code: str) -> dict:
    username = (username or "").strip()
    if len(username) < 3:
        raise ValueError("用户名至少 3 个字符")
    if len(password or "") < 6:
        raise ValueError("密码至少 6 位")
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=?", (username,))
    if c.fetchone():
        conn.close()
        raise ValueError("用户名已存在，请直接登录后使用授权码续费")
    row = _validate_auth_code_row(_fetch_auth_code(c, code))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        "INSERT INTO users (username, password_hash, created_at) VALUES (?,?,?)",
        (username, _hash_password(password), now),
    )
    uid = c.lastrowid
    expires = _extend_membership(c, uid, row["plan_code"], row["duration_days"])
    c.execute(
        "INSERT INTO auth_code_activations (auth_code_id, user_id, activated_at) VALUES (?,?,?)",
        (row["id"], uid, now),
    )
    c.execute(
        "UPDATE auth_codes SET current_activations=current_activations+1, status='active' WHERE id=?",
        (row["id"],),
    )
    conn.commit()
    conn.close()
    return get_member_profile(uid) or {
        "id": uid,
        "username": username,
        "expires_at": expires,
        "plan_code": row["plan_code"],
        "is_active": True,
    }


def renew_with_auth_code(user_id: int, code: str) -> dict:
    conn = _conn()
    c = conn.cursor()
    row = _validate_auth_code_row(_fetch_auth_code(c, code))
    c.execute(
        "SELECT 1 FROM auth_code_activations WHERE auth_code_id=? AND user_id=?",
        (row["id"], user_id),
    )
    if c.fetchone():
        conn.close()
        raise ValueError("您已使用过此授权码")
    _extend_membership(c, user_id, row["plan_code"], row["duration_days"])
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        "INSERT INTO auth_code_activations (auth_code_id, user_id, activated_at) VALUES (?,?,?)",
        (row["id"], user_id, now),
    )
    c.execute(
        "UPDATE auth_codes SET current_activations=current_activations+1, status='active' WHERE id=?",
        (row["id"],),
    )
    conn.commit()
    conn.close()
    return get_member_profile(user_id) or {}


def get_member_profile(user_id: int) -> dict | None:
    member = get_active_member(user_id)
    if not member:
        conn = _conn()
        c = conn.cursor()
        c.execute("SELECT username FROM users WHERE id=?", (user_id,))
        u = c.fetchone()
        if not u:
            conn.close()
            return None
        c.execute(
            "SELECT plan_code, expires_at, status FROM memberships WHERE user_id=? ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
        m = c.fetchone()
        conn.close()
        if not m:
            return None
        exp = datetime.strptime(m["expires_at"], "%Y-%m-%d %H:%M:%S")
        days = max(0, (exp - datetime.now()).days)
        return {
            "id": user_id,
            "username": u["username"],
            "plan_code": m["plan_code"],
            "plan_label": PLAN_LABELS.get(m["plan_code"], m["plan_code"]),
            "expires_at": m["expires_at"],
            "status": m["status"],
            "days_remaining": days,
            "is_active": False,
            "expiry_warning": "会员已过期，请使用新授权码续费",
        }
    member["plan_label"] = PLAN_LABELS.get(member.get("plan_code", ""), member.get("plan_code", ""))
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
