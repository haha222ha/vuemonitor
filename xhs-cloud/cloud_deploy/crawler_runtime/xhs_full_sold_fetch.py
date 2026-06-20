# -*- coding: utf-8 -*-
"""
数据源⑥ 多引擎商品详情拉取 + 风控降级链。

引擎顺序: api → api2 → mobile_http → playwright
- api: curl_cffi 指纹（原 xhs_web_fallback）
- api2: 极简指纹 / 直连（ApiV2 风格）
- mobile_http: urllib 移动端 UA（部分风控下仍可通）
- playwright: 浏览器拦截 edith/detail（DOM/H5 路径）
"""
from __future__ import annotations

import json
import logging
import random
import threading
import time
import urllib.request

_logger = logging.getLogger(__name__)

ENGINE_CHAIN = ("api", "api2", "mobile_http", "playwright")

_pw_lock = threading.Lock()
_pw_context = None


def _normalize_for_sync(raw, goods_id, engine):
    """统一为 sync_sold_to_main_db 所需字段。"""
    if not raw:
        return None
    if raw.get("real_sales") is not None and raw.get("shop_id") is not None:
        out = dict(raw)
        out["goods_id"] = goods_id
        out["data_source"] = out.get("data_source") or f"web_full_{engine}"
        return out
    sales = raw.get("product_sales")
    if sales is None:
        sales = raw.get("real_sales", 0)
    return {
        "goods_id": goods_id,
        "real_sales": int(sales or 0),
        "shop_id": str(raw.get("store_id") or raw.get("shop_id") or ""),
        "shop_name": str(raw.get("store_name") or raw.get("shop_name") or ""),
        "fans_count": int(raw.get("store_followers") or raw.get("fans_count") or 0),
        "shop_total_sales": int(raw.get("store_sales") or raw.get("shop_total_sales") or 0),
        "product_name": str(raw.get("product_name") or raw.get("title") or ""),
        "shop_score": str(raw.get("shop_score") or ""),
        "ship_from": str(raw.get("shipping_from") or raw.get("ship_from") or ""),
        "category_tag": str(raw.get("category_tag") or ""),
        "data_source": f"web_full_{engine}",
    }


def _detail_url(goods_id):
    return (
        "https://mall.xiaohongshu.com/api/store/jpd/edith/detail/h5/toc"
        f"?item_id={goods_id}&source=h5&version=0.0.5"
    )


def _check_api_payload(data, engine):
    """解析 error_code：600=frozen 商品级，461/300=风控。"""
    if not isinstance(data, dict):
        return None, "fail", {"engine": engine, "message": "invalid json"}
    ec = data.get("error_code", -1)
    msg = str(data.get("msg") or "")
    if ec == 600 or "freeze" in msg.lower() or "item freeze" in msg.lower():
        return None, "frozen", {"engine": engine, "risk": False, "message": msg or "item freeze"}
    if ec in (461, 300):
        return None, "risk", {"engine": engine, "risk": True, "message": f"error_code={ec} {msg}"}
    if ec != 0 and data.get("success") is False:
        return None, "fail", {"engine": engine, "risk": False, "message": f"error_code={ec} {msg}"}
    return data, "ok_payload", {}


def _parse_json_detail(data, goods_id, engine):
    from xhs_shelf_time_module import _parse_edith_detail

    parsed = _parse_edith_detail(data, goods_id)
    if not parsed:
        return None
    return _normalize_for_sync(parsed, goods_id, engine)


def _fetch_via_api(goods_id):
    from shop_collectors import _api_check_risk_control
    from xhs_web_fallback_module import _get_collector

    collector, session, headers = _get_collector()
    if not collector or not session or not headers:
        return None, "fail", {"engine": "api", "risk": False, "message": "collector未就绪"}

    url = _detail_url(goods_id)
    hdr = dict(headers)
    try:
        r = session.get(url, headers=hdr, timeout=(10, 20))
        is_risk, risk_msg = _api_check_risk_control(r.text, r.status_code)
        if is_risk:
            return None, "risk", {"engine": "api", "risk": True, "message": risk_msg}
        if r.status_code >= 400:
            return None, "fail", {"engine": "api", "risk": False, "message": f"HTTP {r.status_code}"}
        data = r.json()
        _, payload_st, payload_meta = _check_api_payload(data, "api")
        if payload_st == "frozen":
            return None, "frozen", payload_meta
        if payload_st == "risk":
            return None, "risk", payload_meta
        if payload_st != "ok_payload":
            return None, "fail", payload_meta

        detail = _parse_json_detail(data, goods_id, "api")
        if not detail:
            detail = collector._fetch_goods_detail(session, headers, goods_id)
            if detail:
                detail = _normalize_for_sync(detail, goods_id, "api")
        if not detail:
            return None, "fail", {"engine": "api", "risk": False, "message": "empty detail"}
        if not detail.get("shop_id"):
            return None, "no_store", {"engine": "api", "risk": False, "message": "no shop_id"}
        return detail, "ok", {"engine": "api", "risk": False, "message": ""}
    except Exception as e:
        _logger.debug("api fetch %s: %s", goods_id, e)
        return None, "fail", {"engine": "api", "risk": False, "message": str(e)}


def _fetch_via_api2(goods_id):
    from shop_collectors import (
        HAS_CURL_CFFI,
        _APIV2_IMPERSONATE_POOL,
        _APIV2_MINIMAL_HEADERS,
        _api_check_risk_control,
        cffi_requests,
    )
    import requests

    url = _detail_url(goods_id)
    headers = dict(_APIV2_MINIMAL_HEADERS)
    headers["Referer"] = f"https://www.xiaohongshu.com/goods-detail/{goods_id}"
    try:
        if HAS_CURL_CFFI and _APIV2_IMPERSONATE_POOL:
            imp = random.choice(_APIV2_IMPERSONATE_POOL)
            sess = cffi_requests.Session(impersonate=imp)
            r = sess.get(url, headers=headers, timeout=(8, 15))
            try:
                sess.close()
            except Exception:
                pass
        else:
            r = requests.get(url, headers=headers, timeout=(8, 15))

        is_risk, risk_msg = _api_check_risk_control(r.text, r.status_code)
        if is_risk:
            return None, "risk", {"engine": "api2", "risk": True, "message": risk_msg}
        if r.status_code >= 400:
            return None, "fail", {"engine": "api2", "risk": False, "message": f"HTTP {r.status_code}"}
        data = r.json()
        _, payload_st, payload_meta = _check_api_payload(data, "api2")
        if payload_st in ("frozen", "risk", "fail"):
            return None, payload_st, payload_meta

        detail = _parse_json_detail(data, goods_id, "api2")
        if not detail or not detail.get("shop_id"):
            return None, "no_store" if detail else "fail", {
                "engine": "api2",
                "risk": False,
                "message": "parse_fail_or_no_store",
            }
        return detail, "ok", {"engine": "api2", "risk": False, "message": ""}
    except Exception as e:
        return None, "fail", {"engine": "api2", "risk": False, "message": str(e)}


def _fetch_via_mobile_http(goods_id):
    """移动端 urllib — 部分 api 风控时仍可返回 JSON。"""
    from shop_collectors import _api_check_risk_control

    url = _detail_url(goods_id)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
                "Mobile/15E148 Safari/604.1"
            ),
            "Accept": "application/json, text/plain, */*",
            "Referer": f"https://www.xiaohongshu.com/goods-detail/{goods_id}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            status = getattr(resp, "status", 200) or 200
        is_risk, risk_msg = _api_check_risk_control(body, status)
        if is_risk:
            return None, "risk", {"engine": "mobile_http", "risk": True, "message": risk_msg}
        data = json.loads(body)
        _, payload_st, payload_meta = _check_api_payload(data, "mobile_http")
        if payload_st in ("frozen", "risk", "fail"):
            return None, payload_st, payload_meta
        detail = _parse_json_detail(data, goods_id, "mobile_http")
        if not detail or not detail.get("shop_id"):
            return None, "fail", {"engine": "mobile_http", "risk": False, "message": "parse_fail"}
        return detail, "ok", {"engine": "mobile_http", "risk": False, "message": ""}
    except Exception as e:
        return None, "fail", {"engine": "mobile_http", "risk": False, "message": str(e)}


def _get_pw_context():
    global _pw_context
    with _pw_lock:
        from xhs_shelf_time_module import _ensure_browser, _new_context

        browser = _ensure_browser()
        if not browser:
            return None
        if _pw_context is None:
            _pw_context = _new_context(browser)
        return _pw_context


def _pw_capture_detail_json(context, goods_id):
    """Playwright 直捕 edith/detail JSON（含 error_code 判断）。"""
    page = None
    captured = [None]
    try:
        page = context.new_page()

        def _on_resp(resp):
            try:
                if resp.status != 200:
                    return
                url = resp.url
                if "edith/detail" in url and "variant" not in url:
                    captured[0] = resp.json()
            except Exception:
                pass

        page.on("response", _on_resp)
        page.goto(
            f"https://www.xiaohongshu.com/goods-detail/{goods_id}",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        for _ in range(12):
            if captured[0]:
                break
            page.wait_for_timeout(1000)
        return captured[0]
    except Exception:
        return None
    finally:
        if page:
            try:
                page.close()
            except Exception:
                pass


def _fetch_via_playwright(goods_id):
    from xhs_shelf_time_module import _fetch_goods_detail_via_browser

    context = _get_pw_context()
    if not context:
        return None, "fail", {"engine": "playwright", "risk": False, "message": "browser未就绪"}

    try:
        raw = _fetch_goods_detail_via_browser(context, goods_id)
    except Exception as e:
        return None, "fail", {"engine": "playwright", "risk": False, "message": str(e)}

    if raw is None:
        raw_json = _pw_capture_detail_json(context, goods_id)
        if isinstance(raw_json, dict):
            _, payload_st, payload_meta = _check_api_payload(raw_json, "playwright")
            if payload_st in ("frozen", "risk", "fail"):
                return None, payload_st, payload_meta
            detail = _parse_json_detail(raw_json, goods_id, "playwright")
            if detail and detail.get("shop_id"):
                return detail, "ok", {"engine": "playwright", "risk": False, "message": ""}
        return None, "fail", {"engine": "playwright", "risk": False, "message": "null response"}
    if isinstance(raw, dict) and raw.get("error"):
        err = str(raw.get("error") or "")
        if any(k in err for k in ("限制", "风控", "blocked", "验证码")):
            return None, "risk", {"engine": "playwright", "risk": True, "message": err}
        if "下架" in err or "不存在" in err:
            return None, "no_store", {"engine": "playwright", "risk": False, "message": err}
        return None, "fail", {"engine": "playwright", "risk": False, "message": err}

    detail = _normalize_for_sync(raw, goods_id, "playwright")
    if not detail or not detail.get("shop_id"):
        return None, "no_store", {"engine": "playwright", "risk": False, "message": "no shop_id"}
    return detail, "ok", {"engine": "playwright", "risk": False, "message": ""}


def _fetch_via_drissionpage(goods_id):
    return _fetch_via_mobile_http(goods_id)


_ENGINE_FN = {
    "api": _fetch_via_api,
    "api2": _fetch_via_api2,
    "mobile_http": _fetch_via_mobile_http,
    "drissionpage": _fetch_via_drissionpage,
    "playwright": _fetch_via_playwright,
}


def fetch_sold_detail(goods_id, engine="api", fallback_chain=None, auto_fallback=True):
    """
    拉取商品详情。auto_fallback=True 时遇 risk/fail 自动尝试下一引擎。
    返回 (detail, status, meta)
    """
    if fallback_chain:
        chain = tuple(fallback_chain)
    elif auto_fallback:
        chain = ENGINE_CHAIN
        if engine and engine in ENGINE_CHAIN:
            idx = ENGINE_CHAIN.index(engine)
            chain = ENGINE_CHAIN[idx:]
    else:
        chain = (engine or "api",)

    tried = []
    last_meta = {"engine": chain[0] if chain else "api", "risk": False, "message": ""}
    any_risk = False

    for eng in chain:
        fn = _ENGINE_FN.get(eng)
        if not fn:
            continue
        tried.append(eng)
        detail, status, meta = fn(goods_id)
        meta = dict(meta or {})
        meta["engine"] = eng
        meta["tried"] = list(tried)
        last_meta = meta

        if status == "ok":
            meta["won_engine"] = eng
            return detail, status, meta
        if status == "no_store":
            meta["won_engine"] = eng
            return None, status, meta
        if status == "frozen":
            meta["won_engine"] = eng
            return None, status, meta
        if status == "risk":
            any_risk = True
            continue
        continue

    if any_risk:
        last_meta["risk"] = True
        return None, "risk", last_meta
    return None, "fail", last_meta


def probe_engines(goods_id, log_func=None, min_ok=1):
    """多引擎探测，返回可用引擎列表。"""
    log = log_func or (lambda _m: None)
    alive = []
    for eng in ENGINE_CHAIN:
        t0 = time.time()
        detail, status, meta = fetch_sold_detail(
            goods_id, engine=eng, fallback_chain=(eng,), auto_fallback=False
        )
        elapsed = time.time() - t0
        sales = (detail or {}).get("real_sales", 0) if status == "ok" else 0
        ok = status == "ok" and int(sales or 0) > 0
        if ok:
            alive.append(eng)
        log(
            f"[⑥探测] {eng}: {'OK' if ok else status} "
            f"sales={sales} ({elapsed:.1f}s) {meta.get('message', '')}"
        )
    return alive


def probe_engines_multi(goods_ids, log_func=None, need_consecutive=2):
    """多样本探活：连续 need_consecutive 个商品在同一引擎上成功才认定恢复。"""
    ids = [g for g in (goods_ids or []) if g][:5]
    if not ids:
        return []
    log = log_func or (lambda _m: None)
    for eng in ENGINE_CHAIN:
        wins = 0
        for gid in ids:
            detail, status, meta = fetch_sold_detail(
                gid, engine=eng, fallback_chain=(eng,), auto_fallback=False
            )
            sales = (detail or {}).get("real_sales", 0) if status == "ok" else 0
            if status == "ok" and int(sales or 0) > 0:
                wins += 1
                if wins >= need_consecutive:
                    log(f"[⑥探活] 引擎 {eng} 连续 {wins} 次成功，认定可恢复")
                    return [eng]
            else:
                wins = 0
    log("[⑥探活] 无引擎通过多样本探活")
    return []
