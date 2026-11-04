# -*- coding: utf-8 -*-
"""云端 Cursor 遥控任务队列（手机提交 → 多机 worker 按设备申领 → 回写结果）。"""
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
_DEVICE_STALE_SEC = 120.0


def _root() -> str:
    return os.path.join(get_settings().xhs_data_dir, "agent_tasks")


def _path() -> str:
    return os.path.join(_root(), "queue.json")


def _devices_path() -> str:
    return os.path.join(_root(), "devices.json")


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


def _norm_target(raw: str | None) -> str:
    t = str(raw or "").strip()
    if not t or t in ("*", "any", "ANY", "任意", "任意设备", "任意在线设备"):
        return ""
    return t[:80]


def _target_matches(row: dict[str, Any], worker_id: str) -> bool:
    target = _norm_target(row.get("target_device_id"))
    if not target:
        return True
    return target == worker_id


def submit(
    prompt: str,
    *,
    source: str = "web",
    target_device_id: str = "",
    target_label: str = "",
) -> dict[str, Any]:
    prompt = (prompt or "").strip()
    if not prompt:
        return {"ok": False, "error": "empty prompt"}
    if len(prompt) > 20000:
        return {"ok": False, "error": "prompt too long"}
    tid = uuid.uuid4().hex[:12]
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    target = _norm_target(target_device_id)
    label = str(target_label or "").strip()[:64]
    row = {
        "id": tid,
        "prompt": prompt,
        "status": "pending",
        "source": str(source or "web")[:40],
        "created_at": now,
        "target_device_id": target,
        "target_label": label,
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
                pass
            else:
                continue
            if not _target_matches(row, worker_id):
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
        "target_device_id": row.get("target_device_id") or "",
        "target_label": row.get("target_label") or "",
        "claimed_by": row.get("claimed_by") or "",
        "claimed_at": row.get("claimed_at") or "",
        "result": row.get("result") or "",
        "error": row.get("error") or "",
        "finished_at": row.get("finished_at") or "",
    }


def _worker_status_path() -> str:
    return os.path.join(_root(), "worker_status.json")


def _load_devices() -> dict[str, Any]:
    path = _devices_path()
    if not os.path.isfile(path):
        return {"version": 1, "devices": {}}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {"version": 1, "devices": {}}
    data.setdefault("devices", {})
    return data


def _save_devices(data: dict[str, Any]) -> None:
    os.makedirs(_root(), exist_ok=True)
    data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    tmp = _devices_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _devices_path())


def upsert_device(
    *,
    device_id: str,
    device_label: str = "",
    hostname: str = "",
    phase: str = "idle",
    task_id: str = "",
    hint: str = "",
    message: str = "",
    chain: int = 0,
) -> dict[str, Any]:
    did = str(device_id or "").strip()[:80]
    if not did:
        return {"ok": False, "error": "empty device_id"}
    now = time.time()
    with _lock:
        data = _load_devices()
        devices = data.setdefault("devices", {})
        prev = devices.get(did) or {}
        label = str(device_label or "").strip()[:64] or str(prev.get("label") or "") or did
        devices[did] = {
            "device_id": did,
            "label": label,
            "hostname": str(hostname or prev.get("hostname") or "")[:120],
            "phase": str(phase or "idle")[:40],
            "task_id": str(task_id or "")[:80],
            "hint": str(hint or "")[:500],
            "message": str(message or "")[:500],
            "chain": int(chain or 0),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_ts": now,
        }
        # 防止无限膨胀：只留最近 40 台
        if len(devices) > 40:
            ordered = sorted(
                devices.items(),
                key=lambda kv: float((kv[1] or {}).get("updated_ts") or 0),
                reverse=True,
            )
            data["devices"] = dict(ordered[:40])
        _save_devices(data)
        return {"ok": True, "device": data["devices"].get(did)}


def list_devices(*, stale_sec: float | None = None) -> dict[str, Any]:
    stale_sec = float(stale_sec if stale_sec is not None else _DEVICE_STALE_SEC)
    now = time.time()
    with _lock:
        data = _load_devices()
        items = []
        for did, row in (data.get("devices") or {}).items():
            ts = float((row or {}).get("updated_ts") or 0)
            online = bool(ts and (now - ts) <= stale_sec)
            items.append(
                {
                    "device_id": did,
                    "label": (row or {}).get("label") or did,
                    "hostname": (row or {}).get("hostname") or "",
                    "phase": (row or {}).get("phase") or "offline",
                    "task_id": (row or {}).get("task_id") or "",
                    "hint": (row or {}).get("hint") or "",
                    "message": (row or {}).get("message") or "",
                    "chain": int((row or {}).get("chain") or 0),
                    "updated_at": (row or {}).get("updated_at") or "",
                    "online": online,
                }
            )
        items.sort(key=lambda x: (not x["online"], str(x.get("label") or "")))
        online_n = sum(1 for x in items if x["online"])
        return {"ok": True, "devices": items, "online_n": online_n, "total_n": len(items)}


# 手机遥控页可见相位（写死）
# wait_user = 本方向收口(NEXT_STEP:no)；空闲队列会自动推下一刀，禁止再暗示「必须等人输入」
_PHASE_MSG = {
    "idle": "本机空闲，可以提交新任务",
    "task_running": "Cursor 正在执行当前任务，请稍等",
    "auto_running": "脚本自动续跑中（无需你点确认），请稍等",
    "wait_user": "本方向收口；约1～2分钟空闲队列自动推下一刀（无需你输入）",
    "error": "执行出错，请看任务详情或下达新指令",
}
_PHASE_PHONE_ACTION = {
    "idle": "可提交新任务",
    "task_running": "请等待，无需操作",
    "auto_running": "请等待，无需操作",
    "wait_user": "无需操作·不要发下一条·队列自动续",
    "error": "请查看错误并下新指令",
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
    device_label: str = "",
    hostname: str = "",
    phone_action: str = "",
) -> dict[str, Any]:
    """本机 worker 心跳/阶段状态 → 手机遥控页；并写入多机 devices 表。"""
    phase = str(phase or "idle").strip().lower()
    if phase not in _PHASE_MSG:
        phase = "idle"
    msg = (message or "").strip() or _PHASE_MSG[phase]
    # 纠偏：旧本机仍可能推「请下达下一步指令」；云端统一盖成无人值守口径
    if phase == "wait_user" and (
        "请下达下一步" in msg
        or "等待你输入" in msg
        or "等待你在遥控页" in msg
        or "等你输入" in msg
        or "输入下一条" in msg
        or "等待你在遥控器" in msg
        or msg.strip() in ("阶段完成", "本阶段完成")
    ):
        msg = _PHASE_MSG["wait_user"]
    wid = str(worker_id or "")[:80]
    pa = (phone_action or "").strip() or _PHASE_PHONE_ACTION.get(phase, "")
    # 「输入」字样一律盖掉，避免手机误以为要发下一条
    if phase == "wait_user" and (
        "下达" in pa or "输入" in pa or "请发" in pa or "下一条" in pa
    ):
        pa = _PHASE_PHONE_ACTION["wait_user"]
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
        "worker_id": wid,
        "phone_action": pa[:120],
    }
    with _lock:
        os.makedirs(_root(), exist_ok=True)
        path = _worker_status_path()
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(row, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    if wid:
        upsert_device(
            device_id=wid,
            device_label=device_label,
            hostname=hostname,
            phase=phase,
            task_id=task_id,
            hint=hint,
            message=msg,
            chain=chain,
        )
    devices = list_devices()
    return {"ok": True, "worker": row, "devices": devices.get("devices") or [], "online_n": devices.get("online_n")}


def get_worker_status(*, stale_sec: float = 120.0) -> dict[str, Any]:
    """手机读相位；附带多机设备列表。"""
    devices_payload = list_devices(stale_sec=stale_sec)
    path = _worker_status_path()
    if not os.path.isfile(path):
        online = devices_payload.get("online_n") or 0
        return {
            "ok": True,
            "worker": {
                "phase": "offline" if online <= 0 else "idle",
                "title": (
                    f"已有 {online} 台设备在线"
                    if online
                    else "尚无设备上报（请启动各机 worker）"
                ),
                "message": (
                    f"已有 {online} 台设备在线，可在下方选择设备发单"
                    if online
                    else "尚无设备上报（请启动各机 worker）"
                ),
                "phone_action": "可提交新任务" if online else "请在电脑上启动 worker 安装包",
                "hint": "",
                "task_id": "",
                "chain": 0,
                "updated_at": "",
                "stale": online <= 0,
                "worker_id": "",
            },
            "devices": devices_payload.get("devices") or [],
            "online_n": online,
        }
    try:
        with open(path, encoding="utf-8") as f:
            row = json.load(f)
    except Exception:
        row = {}
    ts = float(row.get("updated_ts") or 0)
    stale = (time.time() - ts) > float(stale_sec or 120) if ts else True
    online = int(devices_payload.get("online_n") or 0)
    if stale and str(row.get("phase") or "") not in ("wait_user",):
        if online > 0:
            row = {
                **row,
                "phase": "idle",
                "title": f"{online} 台设备在线，可指定设备发单",
                "message": f"{online} 台设备在线，可指定设备发单",
                "phone_action": "选择设备后提交任务",
                "stale": False,
            }
        else:
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
        if online > 1 and row.get("phase") == "idle":
            row["title"] = f"{online} 台在线 · " + str(row.get("title") or "")
    return {
        "ok": True,
        "worker": row,
        "devices": devices_payload.get("devices") or [],
        "online_n": online,
    }
