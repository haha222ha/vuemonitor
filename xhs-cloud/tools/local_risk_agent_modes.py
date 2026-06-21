# -*- coding: utf-8 -*-
"""本地 Agent 三种采集模式（可切换对比，互不删除）。"""
from __future__ import annotations

import os
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import Callable

MODE_MULTI_BROWSER = "multi_browser"       # A: 多进程，每进程一个 Chromium（原方案）
MODE_SINGLE_BROWSER = "single_browser"     # C: 单 Chromium，多标签并行
MODE_API_THEN_BROWSER = "api_then_browser"  # D: 本地 API 优先，失败再 Playwright

MODE_LABELS = {
    MODE_MULTI_BROWSER: "A 多浏览器并发（原方案，最快，内存高）",
    MODE_SINGLE_BROWSER: "C 单浏览器多标签（省内存）",
    MODE_API_THEN_BROWSER: "D API优先+浏览器兜底（最省资源）",
}

_shared_context = None
_shared_lock = threading.Lock()


def _setup_crawler(crawler: str, cloud_root: str) -> None:
    if cloud_root not in sys.path:
        sys.path.insert(0, cloud_root)
    if crawler and os.path.isdir(crawler) and crawler not in sys.path:
        sys.path.insert(0, crawler)
    os.environ["XHS_ENABLE_PLAYWRIGHT"] = "1"


def _row_from_fetch(gid: str, detail, status: str, meta: dict, t0: float) -> dict:
    from cloud_deploy.cloud_api.agent_service import slim_detail

    meta = dict(meta or {})
    sold = None
    detail_out = None
    if status == "ok" and detail:
        sold = int(detail.get("real_sales") or detail.get("product_sales") or 0)
        detail_out = slim_detail(detail)
    return {
        "goods_id": gid,
        "status": status,
        "sold": sold,
        "message": str(meta.get("message") or "")[:200],
        "engine": str(meta.get("won_engine") or meta.get("engine") or "")[:32],
        "ms": int((time.time() - t0) * 1000),
        "detail": detail_out or {},
    }


def _playwright_with_context(context, goods_id: str) -> tuple:
    from xhs_full_sold_fetch import (
        _check_api_payload,
        _normalize_for_sync,
        _parse_json_detail,
        _pw_capture_detail_json,
    )
    from xhs_shelf_time_module import _fetch_goods_detail_via_browser

    gid = str(goods_id)
    raw = _fetch_goods_detail_via_browser(context, gid)
    if raw is None:
        raw_json = _pw_capture_detail_json(context, gid)
        if isinstance(raw_json, dict):
            _, payload_st, payload_meta = _check_api_payload(raw_json, "playwright")
            if payload_st in ("frozen", "risk", "fail"):
                return None, payload_st, payload_meta
            detail = _parse_json_detail(raw_json, gid, "playwright")
            if detail and detail.get("shop_id"):
                return detail, "ok", {"engine": "playwright", "message": ""}
        return None, "fail", {"engine": "playwright", "message": "null response"}
    if isinstance(raw, dict) and raw.get("error"):
        err = str(raw.get("error") or "")
        if any(k in err for k in ("限制", "风控", "blocked", "验证码")):
            return None, "risk", {"engine": "playwright", "risk": True, "message": err}
        if "下架" in err or "不存在" in err:
            return None, "no_store", {"engine": "playwright", "message": err}
        return None, "fail", {"engine": "playwright", "message": err}
    detail = _normalize_for_sync(raw, gid, "playwright")
    if not detail or not detail.get("shop_id"):
        return None, "no_store", {"engine": "playwright", "message": "no shop_id"}
    return detail, "ok", {"engine": "playwright", "message": ""}


def _get_shared_context(crawler: str, cloud_root: str):
    global _shared_context
    with _shared_lock:
        if _shared_context is not None:
            return _shared_context
        _setup_crawler(crawler, cloud_root)
        from xhs_shelf_time_module import _ensure_browser, _new_context

        browser = _ensure_browser()
        if not browser:
            raise RuntimeError("Playwright 浏览器启动失败")
        _shared_context = _new_context(browser)
        return _shared_context


def _worker_init_multi(crawler: str, cloud_root: str) -> None:
    _setup_crawler(crawler, cloud_root)


def _fetch_timeout_sec() -> int:
    return max(20, int(os.environ.get("XHS_LOCAL_AGENT_FETCH_TIMEOUT", "60")))


def _call_with_timeout(fn, timeout_sec: int | None = None):
    from concurrent.futures import ThreadPoolExecutor
    from concurrent.futures import TimeoutError as FutTimeout

    timeout_sec = timeout_sec or _fetch_timeout_sec()
    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(fn)
        try:
            return fut.result(timeout=timeout_sec)
        except FutTimeout as exc:
            raise TimeoutError(f"采集超时>{timeout_sec}s") from exc


def _scan_wait_loop(futs: dict, log, item_timeout: int) -> list[dict]:
    """带心跳的 as_completed 等待。"""
    results: list[dict] = []
    total = len(futs)
    stop_hb = threading.Event()

    def heartbeat() -> None:
        while not stop_hb.wait(20):
            left = total - len(results)
            if left > 0:
                log(f"仍在等待 {left}/{total} 条（浏览器兜底较慢，超时会自动跳过）...")

    hb = threading.Thread(target=heartbeat, daemon=True)
    hb.start()
    try:
        for fut in as_completed(futs):
            gid = futs[fut]
            try:
                row = fut.result(timeout=item_timeout)
            except Exception as exc:
                row = {
                    "goods_id": gid,
                    "status": "fail",
                    "sold": None,
                    "message": str(exc)[:200],
                    "engine": "",
                    "ms": 0,
                    "detail": {},
                }
            results.append(row)
            ok_so_far = sum(1 for r in results if r.get("status") == "ok")
            log(f"采集进度 {len(results)}/{total} ok={ok_so_far}")
    finally:
        stop_hb.set()
    return results


def _worker_fetch_multi(payload: tuple[str, str, str]) -> dict:
    goods_id, crawler, cloud_root = payload
    os.environ["_RISK_AGENT_CLOUD_ROOT"] = cloud_root
    _worker_init_multi(crawler, cloud_root)
    from xhs_full_sold_fetch import fetch_sold_detail

    t0 = time.time()
    gid = str(goods_id)
    try:
        detail, status, meta = _call_with_timeout(
            lambda: fetch_sold_detail(
                gid,
                engine="playwright",
                fallback_chain=("playwright",),
                auto_fallback=False,
            )
        )
    except Exception as exc:
        return {
            "goods_id": gid,
            "status": "fail",
            "sold": None,
            "message": str(exc)[:200],
            "engine": "playwright",
            "ms": int((time.time() - t0) * 1000),
            "detail": {},
        }
    return _row_from_fetch(gid, detail, status, meta, t0)


def _fetch_single_tab(args: tuple) -> dict:
    goods_id, crawler, cloud_root = args
    t0 = time.time()
    gid = str(goods_id)
    try:
        context = _get_shared_context(crawler, cloud_root)
        detail, status, meta = _call_with_timeout(
            lambda: _playwright_with_context(context, gid)
        )
    except Exception as exc:
        return {
            "goods_id": gid,
            "status": "fail",
            "sold": None,
            "message": str(exc)[:200],
            "engine": "playwright",
            "ms": int((time.time() - t0) * 1000),
            "detail": {},
        }
    return _row_from_fetch(gid, detail, status, meta, t0)


def _fetch_api_then_browser(args: tuple) -> dict:
    goods_id, crawler, cloud_root = args
    _setup_crawler(crawler, cloud_root)
    from xhs_full_sold_fetch import fetch_sold_detail

    t0 = time.time()
    gid = str(goods_id)
    api_only = os.environ.get("XHS_LOCAL_AGENT_COMPARE_D_API_ONLY", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    try:
        if api_only:
            detail, status, meta = _call_with_timeout(
                lambda: fetch_sold_detail(
                    gid,
                    engine="api",
                    fallback_chain=("api",),
                    auto_fallback=False,
                )
            )
        else:
            detail, status, meta = _call_with_timeout(
                lambda: fetch_sold_detail(
                    gid,
                    engine="api",
                    fallback_chain=("api", "playwright"),
                    auto_fallback=True,
                )
            )
    except Exception as exc:
        return {
            "goods_id": gid,
            "status": "fail",
            "sold": None,
            "message": str(exc)[:200],
            "engine": "api",
            "ms": int((time.time() - t0) * 1000),
            "detail": {},
        }
    return _row_from_fetch(gid, detail, status, meta, t0)


def scan_batch(
    items: list[dict],
    concurrency: int,
    crawler: str,
    cloud_root: str,
    mode: str,
    log_fn: Callable[[str], None] | None = None,
) -> list[dict]:
    log = log_fn or (lambda _m: None)
    work_ids = [str(i["goods_id"]) for i in items]
    concurrency = max(1, min(10, int(concurrency)))
    results: list[dict] = []

    item_timeout = max(45, int(os.environ.get("XHS_LOCAL_AGENT_ITEM_TIMEOUT", "90")))

    if mode == MODE_MULTI_BROWSER:
        log(f"模式=A 多浏览器 并发={concurrency}")
        work = [(gid, crawler, cloud_root) for gid in work_ids]
        with ProcessPoolExecutor(
            max_workers=concurrency,
            initializer=_worker_init_multi,
            initargs=(crawler, cloud_root),
        ) as pool:
            futs = {pool.submit(_worker_fetch_multi, w): w[0] for w in work}
            results = _scan_wait_loop(futs, log, item_timeout)

    elif mode == MODE_SINGLE_BROWSER:
        log(f"模式=C 单浏览器多标签 并发={concurrency}")
        work = [(gid, crawler, cloud_root) for gid in work_ids]
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futs = {pool.submit(_fetch_single_tab, w): w[0] for w in work}
            results = _scan_wait_loop(futs, log, item_timeout)

    elif mode == MODE_API_THEN_BROWSER:
        log(f"模式=D API优先+浏览器 并发={concurrency}")
        work = [(gid, crawler, cloud_root) for gid in work_ids]
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futs = {pool.submit(_fetch_api_then_browser, w): w[0] for w in work}
            results = _scan_wait_loop(futs, log, item_timeout)
    else:
        raise ValueError(f"未知模式: {mode}")

    return results


def summarize_results(mode: str, results: list[dict], wall_s: float) -> dict:
    from collections import Counter

    st = Counter(r.get("status") for r in results)
    eng = Counter(r.get("engine") or "?" for r in results if r.get("status") == "ok")
    ok_ms = [r["ms"] for r in results if r.get("status") == "ok" and r.get("ms")]
    return {
        "mode": mode,
        "label": MODE_LABELS.get(mode, mode),
        "total": len(results),
        "ok": st.get("ok", 0),
        "risk": st.get("risk", 0),
        "fail": st.get("fail", 0) + st.get("no_store", 0),
        "frozen": st.get("frozen", 0),
        "ok_rate": round(st.get("ok", 0) / len(results) * 100, 1) if results else 0,
        "wall_s": round(wall_s, 1),
        "avg_ok_ms": int(sum(ok_ms) / len(ok_ms)) if ok_ms else 0,
        "engines_ok": dict(eng),
    }


def compare_modes(
    items: list[dict],
    concurrency: int,
    crawler: str,
    cloud_root: str,
    modes: list[str] | None = None,
    log_fn: Callable[[str], None] | None = None,
) -> list[dict]:
    """同一批商品用多种模式各跑一遍（仅测试，不上传）。"""
    log = log_fn or (lambda _m: None)
    modes = modes or [MODE_API_THEN_BROWSER, MODE_SINGLE_BROWSER, MODE_MULTI_BROWSER]
    compare_n = max(3, min(len(items), int(os.environ.get("XHS_LOCAL_AGENT_COMPARE_N", "9"))))
    subset = items[:compare_n]
    os.environ.setdefault("XHS_LOCAL_AGENT_FETCH_TIMEOUT", "45")
    os.environ.setdefault("XHS_LOCAL_AGENT_ITEM_TIMEOUT", "90")
    os.environ.setdefault("XHS_LOCAL_AGENT_COMPARE_D_API_ONLY", "1")
    log(f"对比测试: {compare_n} 条 × {len(modes)} 种模式（D模式对比时仅测API，正式跑含浏览器兜底）")

    reports: list[dict] = []
    for mode in modes:
        global _shared_context
        _shared_context = None
        log(f"--- 开始 {MODE_LABELS.get(mode, mode)} ---")
        t0 = time.time()
        rows = scan_batch(subset, concurrency, crawler, cloud_root, mode, log_fn=log)
        rep = summarize_results(mode, rows, time.time() - t0)
        reports.append(rep)
        log(
            f"--- 完成 {mode}: ok={rep['ok']}/{rep['total']} "
            f"{rep['ok_rate']}% 耗时={rep['wall_s']}s 引擎={rep.get('engines_ok')} ---"
        )
    return reports
