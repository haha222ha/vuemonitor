# -*- coding: utf-8 -*-
"""云端闲鱼选品审核台账（OCR 通过批次）。"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

from cloud_deploy.cloud_api.config import get_settings

_lock = threading.RLock()


def _root() -> str:
    return os.path.join(get_settings().xhs_data_dir, "listing_review")


def ledger_path() -> str:
    return os.path.join(_root(), "ledger.json")


def meta_path() -> str:
    return os.path.join(_root(), "meta.json")


def _empty_ledger() -> dict[str, Any]:
    return {
        "version": 1,
        "updated_at": "",
        "batches": [],
        "items": {},
    }


def load_ledger() -> dict[str, Any]:
    path = ledger_path()
    if not os.path.isfile(path):
        return _empty_ledger()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("batches", [])
    data.setdefault("items", {})
    return data


def save_ledger(data: dict[str, Any]) -> None:
    os.makedirs(_root(), exist_ok=True)
    data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    tmp = ledger_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, ledger_path())
    with open(meta_path(), "w", encoding="utf-8") as f:
        json.dump(
            {
                "updated_at": data["updated_at"],
                "batch_n": len(data.get("batches") or []),
                "item_n": len(data.get("items") or {}),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )


def merge_upload_slice(slice_data: dict[str, Any]) -> dict[str, Any]:
    """合并本地推送的 OCR 通过切片；保留云端已有人工 review。"""
    with _lock:
        led = load_ledger()
        items = led.setdefault("items", {})
        batches_by_no = {int(b.get("no") or 0): b for b in (led.get("batches") or [])}

        incoming_items = slice_data.get("items") or {}
        incoming_batches = slice_data.get("batches") or []
        merged_items = 0
        merged_batches = 0

        for gid, row in incoming_items.items():
            gid = str(gid or "").strip()
            if not gid or not isinstance(row, dict):
                continue
            prev = items.get(gid) or {}
            # 云端人工已删/已 keep 的不覆盖 review
            cloud_rev = str(prev.get("review") or "")
            new_row = dict(row)
            if cloud_rev in ("removed", "keep") and prev.get("cloud_reviewed"):
                new_row["review"] = cloud_rev
                new_row["review_reason"] = prev.get("review_reason") or new_row.get("review_reason")
                new_row["cloud_reviewed"] = True
            else:
                # 上云的都是 OCR 通过候选，默认 pending 供人工删选
                if str(new_row.get("review") or "") == "removed":
                    continue
                new_row["review"] = "pending"
                new_row["ocr_status"] = "pass"
            new_row["source_product_id"] = gid
            items[gid] = new_row
            merged_items += 1

        for b in incoming_batches:
            try:
                no = int(b.get("no") or 0)
            except (TypeError, ValueError):
                continue
            if no <= 0:
                continue
            gids = [str(g) for g in (b.get("items") or []) if str(g or "").strip()]
            # 只保留仍在 items 且未删的
            gids = [
                g
                for g in gids
                if g in items and str((items.get(g) or {}).get("review") or "") != "removed"
            ]
            if not gids:
                continue
            prev_b = batches_by_no.get(no) or {}
            status = str(prev_b.get("status") or "pending")
            if status not in ("pending", "approved", "listing", "done"):
                status = "pending"
            batches_by_no[no] = {
                "no": no,
                "status": status if status != "done" else "pending",
                "items": gids,
                "pushed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "source": slice_data.get("source") or "local_ocr",
            }
            merged_batches += 1

        led["batches"] = [batches_by_no[k] for k in sorted(batches_by_no.keys())]
        save_ledger(led)
        return {
            "ok": True,
            "merged_items": merged_items,
            "merged_batches": merged_batches,
            "total_items": len(led["items"]),
            "total_batches": len(led["batches"]),
            "updated_at": led.get("updated_at"),
        }


def list_batches() -> list[dict[str, Any]]:
    with _lock:
        led = load_ledger()
        items = led.get("items") or {}
        out = []
        for b in led.get("batches") or []:
            gids = b.get("items") or []
            n_pass = 0
            n_rm = 0
            n_pending = 0
            for g in gids:
                it = items.get(g) or {}
                rev = str(it.get("review") or "pending")
                if rev == "removed":
                    n_rm += 1
                elif rev == "keep":
                    n_pass += 1
                else:
                    n_pending += 1
            out.append(
                {
                    "no": b.get("no"),
                    "status": b.get("status") or "pending",
                    "count": len(gids),
                    "pending": n_pending,
                    "kept": n_pass,
                    "removed": n_rm,
                    "pushed_at": b.get("pushed_at") or "",
                }
            )
        return out


def get_batch(no: int) -> dict[str, Any] | None:
    with _lock:
        led = load_ledger()
        items = led.get("items") or {}
        for b in led.get("batches") or []:
            if int(b.get("no") or 0) != int(no):
                continue
            rows = []
            for g in b.get("items") or []:
                it = items.get(g)
                if it:
                    rows.append(it)
            return {
                "no": int(no),
                "status": b.get("status") or "pending",
                "items": rows,
            }
        return None


def apply_review(no: int, keep: list[str], remove: list[str]) -> dict[str, Any]:
    with _lock:
        led = load_ledger()
        items = led.get("items") or {}
        b = next((x for x in (led.get("batches") or []) if int(x.get("no") or 0) == int(no)), None)
        if not b:
            return {"ok": False, "error": "no batch"}
        keep_s = set(str(x) for x in (keep or []))
        remove_s = set(str(x) for x in (remove or []))
        n_keep = n_rm = 0
        for gid in b.get("items") or []:
            it = items.get(gid)
            if not it:
                continue
            if gid in remove_s:
                it["review"] = "removed"
                it["review_reason"] = it.get("review_reason") or "cloud_human"
                it["cloud_reviewed"] = True
                it["listing_status"] = "skip"
                n_rm += 1
            elif gid in keep_s:
                it["review"] = "keep"
                it["cloud_reviewed"] = True
                # 进入闲鱼主机领任务队列
                if _listing_status(it) not in ("listed", "listing"):
                    it["listing_status"] = "ready"
                n_keep += 1
        b["status"] = "approved"
        save_ledger(led)
        return {"ok": True, "kept": n_keep, "removed": n_rm, "queue_hint": "listing-claim"}


def export_decisions() -> dict[str, Any]:
    """供本地拉回人工筛选结果。"""
    with _lock:
        led = load_ledger()
        decisions = {}
        for gid, it in (led.get("items") or {}).items():
            if not it.get("cloud_reviewed"):
                continue
            decisions[gid] = {
                "review": it.get("review") or "pending",
                "review_reason": it.get("review_reason") or "",
                "batch_no": it.get("batch_no"),
            }
        return {
            "ok": True,
            "updated_at": led.get("updated_at") or "",
            "count": len(decisions),
            "decisions": decisions,
        }


def _listing_status(it: dict[str, Any]) -> str:
    return str(it.get("listing_status") or "").strip().lower()


def list_ready_for_listing(*, limit: int = 50, batch_no: int | None = None) -> dict[str, Any]:
    """人工 keep 且未上架/未占用的商品队列（给上架 worker 领任务）。"""
    with _lock:
        led = load_ledger()
        items = led.get("items") or {}
        now = time.time()
        out = []
        for gid, it in items.items():
            if str(it.get("review") or "") != "keep":
                continue
            if batch_no is not None and int(it.get("batch_no") or 0) != int(batch_no):
                continue
            st = _listing_status(it)
            if st in ("listed", "listing"):
                # listing 超时自动释放
                if st == "listing":
                    exp = float(it.get("claim_expires_at") or 0)
                    if exp and exp > now:
                        continue
                    it["listing_status"] = "ready"
                    it.pop("claimed_by", None)
                    it.pop("claim_expires_at", None)
                else:
                    continue
            row = {
                "source_product_id": gid,
                "title": it.get("title") or "",
                "price": it.get("price"),
                "image_url": it.get("image_url") or "",
                "detail_url": it.get("detail_url") or "",
                "sold": it.get("sold") or 0,
                "delta": it.get("delta") or 0,
                "batch_no": it.get("batch_no"),
                "category_tag": it.get("category_tag") or "",
                "ocr_status": it.get("ocr_status") or "pass",
                "listing_status": _listing_status(it) or "ready",
            }
            out.append(row)
            if len(out) >= max(1, int(limit)):
                break
        save_ledger(led)
        return {"ok": True, "count": len(out), "items": out}


def claim_for_listing(
    *,
    worker_id: str,
    item_ids: list[str] | None = None,
    limit: int = 10,
    ttl_sec: int = 1800,
) -> dict[str, Any]:
    """上架 worker 原子领取任务。"""
    worker_id = str(worker_id or "").strip() or "worker"
    ttl_sec = max(60, int(ttl_sec or 1800))
    with _lock:
        led = load_ledger()
        items = led.get("items") or {}
        now = time.time()
        expire = now + ttl_sec
        want = [str(x) for x in (item_ids or []) if str(x or "").strip()]
        claimed = []
        candidates = want or [
            gid
            for gid, it in items.items()
            if str(it.get("review") or "") == "keep"
            and _listing_status(it) not in ("listed",)
            and not (
                _listing_status(it) == "listing"
                and float(it.get("claim_expires_at") or 0) > now
            )
        ]
        for gid in candidates:
            it = items.get(gid)
            if not it or str(it.get("review") or "") != "keep":
                continue
            st = _listing_status(it)
            if st == "listed":
                continue
            if st == "listing" and float(it.get("claim_expires_at") or 0) > now:
                continue
            it["listing_status"] = "listing"
            it["claimed_by"] = worker_id
            it["claimed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            it["claim_expires_at"] = expire
            claimed.append(
                {
                    "source_product_id": gid,
                    "title": it.get("title") or "",
                    "price": it.get("price"),
                    "image_url": it.get("image_url") or "",
                    "detail_url": it.get("detail_url") or "",
                    "batch_no": it.get("batch_no"),
                    "claim_expires_at": expire,
                }
            )
            if len(claimed) >= max(1, int(limit)):
                break
        save_ledger(led)
        return {
            "ok": True,
            "worker_id": worker_id,
            "claimed": len(claimed),
            "ttl_sec": ttl_sec,
            "items": claimed,
        }


def mark_listed(
    *,
    item_id: str,
    worker_id: str = "",
    xianyu_item_id: str = "",
    ok: bool = True,
    error: str = "",
) -> dict[str, Any]:
    """上架结果回写。"""
    gid = str(item_id or "").strip()
    with _lock:
        led = load_ledger()
        it = (led.get("items") or {}).get(gid)
        if not it:
            return {"ok": False, "error": "no item"}
        if ok:
            it["listing_status"] = "listed"
            it["listed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            if xianyu_item_id:
                it["xianyu_item_id"] = str(xianyu_item_id)
            if worker_id:
                it["listed_by"] = str(worker_id)
            it.pop("claim_expires_at", None)
        else:
            it["listing_status"] = "ready"
            it["listing_error"] = str(error or "")[:500]
            it.pop("claimed_by", None)
            it.pop("claim_expires_at", None)
        save_ledger(led)
        return {"ok": True, "item_id": gid, "listing_status": it.get("listing_status")}
