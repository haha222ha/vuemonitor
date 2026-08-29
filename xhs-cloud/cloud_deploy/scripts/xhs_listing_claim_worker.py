# -*- coding: utf-8 -*-
"""闲鱼上架主机：轮询云端领取人工筛选通过的商品。

用法（闲鱼机）:
  set XHS_CLOUD_API_URL=https://monitor.xhs365.cn
  set XHS_CLOUD_SYNC_KEY=与选品机相同
  set XHS_LISTING_WORKER_ID=xianyu-pc-01
  python xhs_listing_claim_worker.py                 # 领一批后打印 JSON 退出
  python xhs_listing_claim_worker.py --loop          # 持续轮询
  python xhs_listing_claim_worker.py --limit 5

领到的每条含:
  source_product_id  小红书商品 ID（主键，复制上架用这个）
  title / price / image_url / detail_url / batch_no

上架成功后务必回写:
  POST /api/v1/sync/listing-result
  { "item_id": "<source_product_id>", "ok": true, "xianyu_item_id": "...", "worker_id": "..." }

失败回写 ok=false 可重新被领。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request


def _api() -> str:
    return (os.environ.get("XHS_CLOUD_API_URL") or "https://monitor.xhs365.cn").rstrip("/")


def _key() -> str:
    return (os.environ.get("XHS_CLOUD_SYNC_KEY") or "").strip()


def _worker() -> str:
    return (os.environ.get("XHS_LISTING_WORKER_ID") or "xianyu-worker").strip()


def _req(method: str, path: str, body: dict | None = None) -> dict:
    key = _key()
    if not key:
        raise SystemExit("请设置 XHS_CLOUD_SYNC_KEY")
    data = None
    headers = {
        "X-Sync-Key": key,
        "User-Agent": "XHS-Listing-Worker/1.0",
    }
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(_api() + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {detail}") from e


def queue(limit: int = 20) -> dict:
    return _req("GET", f"/api/v1/sync/listing-queue?limit={int(limit)}")


def claim(limit: int = 10, ttl_sec: int = 1800) -> dict:
    return _req(
        "POST",
        "/api/v1/sync/listing-claim",
        {
            "worker_id": _worker(),
            "item_ids": [],
            "limit": int(limit),
            "ttl_sec": int(ttl_sec),
        },
    )


def result(item_id: str, *, ok: bool = True, xianyu_item_id: str = "", error: str = "") -> dict:
    return _req(
        "POST",
        "/api/v1/sync/listing-result",
        {
            "item_id": str(item_id),
            "worker_id": _worker(),
            "xianyu_item_id": xianyu_item_id,
            "ok": bool(ok),
            "error": error or "",
        },
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--interval", type=int, default=30, help="空队列休眠秒")
    ap.add_argument("--peek", action="store_true", help="只看队列不领取")
    ap.add_argument("--mark-ok", type=str, default="", help="回写成功：小红书商品ID")
    ap.add_argument("--mark-fail", type=str, default="", help="回写失败：小红书商品ID")
    args = ap.parse_args()

    if args.mark_ok:
        print(json.dumps(result(args.mark_ok, ok=True), ensure_ascii=False, indent=2))
        return 0
    if args.mark_fail:
        print(json.dumps(result(args.mark_fail, ok=False, error="manual"), ensure_ascii=False, indent=2))
        return 0

    while True:
        if args.peek:
            q = queue(args.limit)
            print(json.dumps(q, ensure_ascii=False, indent=2))
        else:
            r = claim(limit=args.limit)
            print(json.dumps(r, ensure_ascii=False, indent=2))
            # 给上架程序用：每行一个 source_product_id
            for it in r.get("items") or []:
                print(
                    f"# TASK\t{it.get('source_product_id')}\t{it.get('price')}\t{it.get('title')}",
                    flush=True,
                )
            if not args.loop:
                return 0
            if not (r.get("items") or []):
                time.sleep(max(5, args.interval))
                continue
            # 领到任务后退出一轮，由外层上架脚本处理；--loop 时空队列才继续
            if r.get("items"):
                return 0
        if not args.loop:
            return 0
        time.sleep(max(5, args.interval))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
