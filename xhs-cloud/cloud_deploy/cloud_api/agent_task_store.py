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
            if st in ("cancelled", "done", "error"):
                continue
            if st == "pending":
                pass
            elif st == "running" and float(row.get("claim_expires_at") or 0) <= now:
                # 认领超时，可重新领取（已撤销的不会进这里）
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


def cancel(task_id: str, *, reason: str = "cancelled_by_user") -> dict[str, Any]:
    """撤销排队中 / 执行中任务；worker 轮询到后停止等落盘，继续下一单。"""
    tid = str(task_id or "").strip()
    if not tid:
        return {"ok": False, "error": "empty task_id"}
    with _lock:
        data = load()
        row = (data.get("tasks") or {}).get(tid)
        if not row:
            return {"ok": False, "error": "no task"}
        st = str(row.get("status") or "")
        if st in ("done", "error", "cancelled"):
            return {
                "ok": True,
                "already_finished": True,
                "task": _public(row),
            }
        if st not in ("pending", "running"):
            return {"ok": False, "error": f"cannot cancel status={st}"}
        row["status"] = "cancelled"
        row["error"] = str(reason or "cancelled_by_user")[:500]
        row["result"] = row.get("result") or "已撤销：worker 将停止等待落盘并领取后续任务"
        row["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        row.pop("claim_expires_at", None)
        save(data)
        return {"ok": True, "task": _public(row)}


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
        # 已撤销：不覆盖为 done/error，避免 worker 迟到回写把撤销冲掉
        if str(row.get("status") or "") == "cancelled":
            return {"ok": True, "already_cancelled": True, "task": _public(row)}
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


def _worker_status_path() -> str:
    return os.path.join(_root(), "worker_status.json")


# 手机遥控页可见相位（写死）
_PHASE_MSG = {
    "idle": "本机空闲，可以提交新任务",
    "task_running": "Cursor 正在执行当前任务，请稍等",
    "auto_running": "脚本自动续跑中（无需你点确认），请稍等",
    "wait_user": "阶段已结束，请下达下一步指令",
    "error": "执行出错，请看任务详情或下达新指令",
}


def set_worker_status(
    *,
    phase: str,
    worker_id: str = "",
    task_id: str = "",
    hint: str = "",
    message: str = "",
    chain: int = 0,
    detail: str = "",
) -> dict[str, Any]:
    """本机 worker 心跳/阶段状态 → 手机遥控页顶部条。"""
    phase = str(phase or "idle").strip().lower()
    if phase not in _PHASE_MSG:
        phase = "idle"
    msg = (message or "").strip() or _PHASE_MSG[phase]
    row = {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_ts": time.time(),
        "phase": phase,
        "title": msg,
        "message": msg,
        "hint": str(hint or "")[:500],
        "detail": str(detail or "")[:800],
        "task_id": str(task_id or "")[:80],
        "chain": int(chain or 0),
        "worker_id": str(worker_id or "")[:80],
        "phone_action": (
            "请下达下一步指令"
            if phase == "wait_user"
            else (
                "请等待，无需操作"
                if phase in ("task_running", "auto_running")
                else ("可提交新任务" if phase == "idle" else "请查看错误并下新指令")
            )
        ),
    }
    with _lock:
        os.makedirs(_root(), exist_ok=True)
        path = _worker_status_path()
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(row, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    return {"ok": True, "worker": row}


def get_worker_status(*, stale_sec: float = 120.0) -> dict[str, Any]:
    """手机读本机相位；超时未心跳 → offline。"""
    path = _worker_status_path()
    if not os.path.isfile(path):
        return {
            "ok": True,
            "worker": {
                "phase": "offline",
                "title": "本机尚未上报状态",
                "message": "本机尚未上报状态（worker 可能未启动）",
                "phone_action": "请确认本机 worker 在跑",
                "hint": "",
                "task_id": "",
                "chain": 0,
                "updated_at": "",
                "stale": True,
            },
        }
    try:
        with open(path, encoding="utf-8") as f:
            row = json.load(f)
    except Exception:
        row = {}
    ts = float(row.get("updated_ts") or 0)
    stale = (time.time() - ts) > float(stale_sec or 120) if ts else True
    if stale and str(row.get("phase") or "") not in ("wait_user",):
        # wait_user 允许稍旧：用户可能隔很久才回；其它相位过期当 offline
        row = {
            **row,
            "phase": "offline",
            "title": "本机状态超时未更新",
            "message": "本机状态超时未更新（worker 可能卡住或已停）",
            "phone_action": "请检查本机 worker / Cursor",
            "stale": True,
        }
    else:
        row = {**row, "stale": bool(stale)}
    return {"ok": True, "worker": row}
