# -*- coding: utf-8 -*-
"""
数据源⑥ 多引擎商品详情拉取 + 风控降级链。

云端默认链: api → drissionpage（XHS_ENABLE_PLAYWRIGHT=1 时追加 playwright）
- api: curl_cffi 指纹（shop_collectors）
- drissionpage: 单例 Chromium 页面内 fetch JSON（2G 推荐高爆品）
- playwright: 可选，默认关闭
"""
from __future__ import annotations

import json
import logging
import os
import random
import threading
import time
import urllib.request

_logger = logging.getLogger(__name__)

_pw_lock = threading.Lock()
_pw_context = None
_dp_lock = threading.Lock()
_dp_page = None
_DP_PROFILE_ID = 77


def cloud_engine_chain() -> tuple[str, ...]:
    base = ("api", "drissionpage")
    if os.environ.get("XHS_ENABLE_PLAYWRIGHT", "0").strip().lower() in ("1", "true", "yes"):
        return base + ("playwright",)
    return base


def get_engine_chain() -> tuple[str, ...]:
    return cloud_engine_chain()


ENGINE_CHAIN = cloud_engine_chain()


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
    url = _detail_url(goods_id)
    page = _ensure_dp_page_unlocked()
    if not page:
        return None, "fail", {
            "engine": "drissionpage",
            "risk": False,
            "message": "DrissionPage 未就绪",
        }
    referer = f"https://www.xiaohongshu.com/goods-detail/{goods_id}"
    try:
        js = """
        const url = arguments[0];
        const referer = arguments[1];
        return fetch(url, {
            credentials: 'include',
            headers: {
                'Accept': 'application/json, text/plain, */*',
                'Referer': referer
            }
        }).then(r => r.text());
        """
        body = page.run_js(js, url, referer)
        if not body:
            return None, "fail", {"engine": "drissionpage", "risk": False, "message": "empty"}
        if isinstance(body, dict):
            data = body
            body_text = json.dumps(body, ensure_ascii=False)
        else:
            body_text = str(body)
            data = json.loads(body_text)
        from shop_collectors import _api_check_risk_control

        is_risk, risk_msg = _api_check_risk_control(body_text, 200)
        if is_risk:
            return None, "risk", {"engine": "drissionpage", "risk": True, "message": risk_msg}
        _, payload_st, payload_meta = _check_api_payload(data, "drissionpage")
        if payload_st in ("frozen", "risk", "fail"):
            return None, payload_st, payload_meta
        detail = _parse_json_detail(data, goods_id, "drissionpage")
        if not detail or not detail.get("shop_id"):
            return None, "fail", {
                "engine": "drissionpage",
                "risk": False,
                "message": "parse_fail_or_no_store",
            }
        return detail, "ok", {"engine": "drissionpage", "risk": False, "message": ""}
    except Exception as exc:
        _logger.debug("drissionpage fetch %s: %s", goods_id, exc)
        return None, "fail", {"engine": "drissionpage", "risk": False, "message": str(exc)}


def _dp_user_data_dir() -> str:
    try:
        from xhs_paths import dp_user_data_dir

        return dp_user_data_dir(_DP_PROFILE_ID)
    except ImportError:
        root = os.environ.get("XHS_CRAWLER_ROOT", os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(root, "crawl_data", f"dp_profile_{_DP_PROFILE_ID}")
        os.makedirs(path, exist_ok=True)
        return path


def _ensure_dp_page_unlocked():
    global _dp_page
    if _dp_page is not None:
        return _dp_page
    try:
        from DrissionPage import ChromiumOptions, ChromiumPage
    except ImportError:
        _logger.warning("DrissionPage 未安装，drissionpage 引擎不可用")
        return None

    co = ChromiumOptions()
    co.set_user_data_path(_dp_user_data_dir())
    co.set_argument("--no-sandbox")
    co.set_argument("--disable-gpu")
    co.set_argument("--disable-dev-shm-usage")
    co.headless(True)
    for env_key in ("CHROME_PATH", "CHROMIUM_PATH"):
        bp = os.environ.get(env_key, "").strip()
        if bp and os.path.isfile(bp):
            co.set_browser_path(bp)
            break
    else:
        for candidate in (
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
            "/usr/bin/google-chrome",
        ):
            if os.path.isfile(candidate):
                co.set_browser_path(candidate)
                break
    try:
        _dp_page = ChromiumPage(co)
    except Exception as exc:
        _logger.warning("DrissionPage 启动失败: %s", exc)
        return None
    return _dp_page


def warmup_drissionpage(log_func=None) -> bool:
    log = log_func or _logger.info
    with _dp_lock:
        page = _ensure_dp_page_unlocked()
        if not page:
            log("[dp] DrissionPage 不可用（pip install DrissionPage / apt chromium）")
            return False
        try:
            page.get("https://www.xiaohongshu.com/", timeout=30)
            log("[dp] 预热完成")
            return True
        except Exception as exc:
            log(f"[dp] 预热失败: {exc}")
            return False


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
        chain = get_engine_chain()
        if engine and engine in chain:
            idx = chain.index(engine)
            chain = chain[idx:]
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

        def _call_engine():
            return fn(goods_id)

        if eng in ("drissionpage", "playwright"):
            lock = _dp_lock if eng == "drissionpage" else _pw_lock
            with lock:
                detail, status, meta = _call_engine()
        else:
            detail, status, meta = _call_engine()
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
    for eng in get_engine_chain():
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
    for eng in get_engine_chain():
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
