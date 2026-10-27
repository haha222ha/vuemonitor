# -*- coding: utf-8 -*-
"""云端 Cursor 遥控任务队列（手机提交 → 本机 worker claim → 回写结果）。"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from typing import Any

from cloud_deploy.cloud_api.config import get_settings

_lock = threading.RLock()
_MAX_TASKS = 200


def _root() -> str:
    return os.path.join(get_settings().xhs_data_dir, "agent_tasks")


def _path() -> str:
    return os.path.join(_root(), "queue.json")


def _empty() -> dict[str, Any]:
    return {"version": 1, "updated_at": "", "order": [], "tasks": {}}


def load() -> dict[str, Any]:
    path = _path()
    if not os.path.isfile(path):
        return _empty()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("order", [])
    data.setdefault("tasks", {})
    return data


def save(data: dict[str, Any]) -> None:
    os.makedirs(_root(), exist_ok=True)
    data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    tmp = _path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _path())


def _trim(data: dict[str, Any]) -> None:
    order = data.get("order") or []
    tasks = data.get("tasks") or {}
    while len(order) > _MAX_TASKS:
        old = order.pop(0)
        tasks.pop(old, None)
    data["order"] = order
    data["tasks"] = tasks


def submit(prompt: str, *, source: str = "web") -> dict[str, Any]:
    prompt = (prompt or "").strip()
    if not prompt:
        return {"ok": False, "error": "empty prompt"}
    if len(prompt) > 20000:
        return {"ok": False, "error": "prompt too long"}
    tid = uuid.uuid4().hex[:12]
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    row = {
        "id": tid,
        "prompt": prompt,
        "status": "pending",
        "source": str(source or "web")[:40],
        "created_at": now,
        "claimed_by": "",
        "claimed_at": "",
        "claim_expires_at": 0,
        "result": "",
        "error": "",
        "finished_at": "",
    }
    with _lock:
        data = load()
        data["tasks"][tid] = row
        data["order"].append(tid)
        _trim(data)
        save(data)
    return {"ok": True, "task": _public(row)}


def get_task(task_id: str) -> dict[str, Any] | None:
    tid = str(task_id or "").strip()
    with _lock:
        row = (load().get("tasks") or {}).get(tid)
        return _public(row) if row else None


def list_tasks(limit: int = 30) -> list[dict[str, Any]]:
    limit = max(1, min(100, int(limit or 30)))
    with _lock:
        data = load()
        tasks = data.get("tasks") or {}
        order = list(reversed(data.get("order") or []))
        out = []
        for tid in order:
            row = tasks.get(tid)
            if row:
                out.append(_public(row))
            if len(out) >= limit:
                break
        return out


def claim(*, worker_id: str, limit: int = 1, ttl_sec: int = 3600) -> dict[str, Any]:
    worker_id = str(worker_id or "").strip() or "cursor-worker"
    ttl_sec = max(120, int(ttl_sec or 3600))
    limit = max(1, min(5, int(limit or 1)))
    now = time.time()
    expire = now + ttl_sec
    claimed: list[dict[str, Any]] = []
    with _lock:
        data = load()
        tasks = data.get("tasks") or {}
        for tid in data.get("order") or []:
            row = tasks.get(tid)
            if not row:
                continue
            st = str(row.get("status") or "")
            if st == "pending":
                pass
            elif st == "running" and float(row.get("claim_expires_at") or 0) <= now:
                # 认领超时，可重新领取
                pass
            else:
                continue
            row["status"] = "running"
            row["claimed_by"] = worker_id
            row["claimed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            row["claim_expires_at"] = expire
            claimed.append(_public(row))
            if len(claimed) >= limit:
                break
        if claimed:
            save(data)
    return {
        "ok": True,
        "worker_id": worker_id,
        "claimed": len(claimed),
        "ttl_sec": ttl_sec,
        "items": claimed,
    }


def mark_result(
    *,
    task_id: str,
    worker_id: str = "",
    ok: bool = True,
    result: str = "",
    error: str = "",
) -> dict[str, Any]:
    tid = str(task_id or "").strip()
    with _lock:
        data = load()
        row = (data.get("tasks") or {}).get(tid)
        if not row:
            return {"ok": False, "error": "no task"}
        row["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        row.pop("claim_expires_at", None)
        if worker_id:
            row["claimed_by"] = str(worker_id)
        if ok:
            row["status"] = "done"
            row["result"] = str(result or "")[:50000]
            row["error"] = ""
        else:
            row["status"] = "error"
            row["error"] = str(error or result or "failed")[:5000]
            row["result"] = str(result or "")[:50000]
        save(data)
        return {"ok": True, "task": _public(row)}


def _public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "prompt": row.get("prompt") or "",
        "status": row.get("status") or "",
        "source": row.get("source") or "",
        "created_at": row.get("created_at") or "",
        "claimed_by": row.get("claimed_by") or "",
        "claimed_at": row.get("claimed_at") or "",
        "result": row.get("result") or "",
        "error": row.get("error") or "",
        "finished_at": row.get("finished_at") or "",
    }
