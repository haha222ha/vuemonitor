import sqlite3
import threading
import time
import queue
import os
import json
import random
import re
import atexit
import logging
import urllib.request
from datetime import datetime
from typing import Any, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crawl_data")
DB_PATH = os.path.join(DATA_DIR, "xhs_burst_monitor.db")
SHELF_TIME_DONE_FILE = os.path.join(DATA_DIR, "shelf_time_done.jsonl")

_is_shelf_running = False
_shelf_progress = {'success': 0, 'fail': 0, 'store_filled': 0, 'shelf_filled': 0, 'total': 0}
_shelf_progress_lock = threading.Lock()

_shelf_write_queue = queue.Queue(maxsize=5000)
_shelf_writer_running = False
_shelf_writer_thread = None

_shelf_done_set = set()
_shelf_done_lock = threading.Lock()
_shelf_done_loaded = False

_browser_lock = threading.Lock()
_playwright_instance = None
_browser_instance = None

_logger = logging.getLogger('xhs_shelf_time')
_logger.setLevel(logging.WARNING)
if not _logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter('%(message)s'))
    _logger.addHandler(_h)


def _db_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        conn.execute('PRAGMA synchronous=NORMAL')
    except Exception:
        pass
    return conn


def _extract_product_id_from_url(url):
    if not url:
        return ""
    m = re.search(r'goods-detail/([a-f0-9]{24})', url, re.I)
    return m.group(1) if m else ""


def _parse_chinese_number(text):
    if not text:
        return 0
    s = str(text).replace(",", "").replace("，", "").strip()
    m = re.search(r'([\d.]+)\s*万', s)
    if m:
        try:
            return int(float(m.group(1)) * 10000)
        except ValueError:
            return 0
    m = re.search(r'(\d+)', s)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return 0
    return 0


def _convert_timestamp(ts):
    try:
        ts = int(ts)
        if ts > 10000000000:
            ts = ts / 1000
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return ""


def _check_page_status(page):
    try:
        current_url = page.url.lower()
        if 'error' in current_url or '404' in current_url:
            return 'not_found'
        page_text = page.inner_text('body', timeout=3000)
        not_found_texts = ['商品不存在', '已下架', '页面不存在']
        for text in not_found_texts:
            if text in page_text:
                return 'not_found'
        blocked_texts = ['blocked', '错误']
        for text in blocked_texts:
            if text in page_text:
                return 'blocked'
        title = page.title()
        if '错误' in title:
            return 'blocked'
        return 'unknown'
    except Exception:
        return 'unknown'


def _ensure_browser():
    global _playwright_instance, _browser_instance
    with _browser_lock:
        if _browser_instance and _browser_instance.is_connected():
            return _browser_instance
        try:
            from playwright.sync_api import sync_playwright
            _playwright_instance = sync_playwright().start()
            _browser_instance = _playwright_instance.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
            )
            return _browser_instance
        except Exception as e:
            _logger.error('浏览器启动失败: %s', e)
            return None


def _close_browser():
    global _playwright_instance, _browser_instance
    with _browser_lock:
        try:
            if _browser_instance:
                _browser_instance.close()
        except Exception:
            pass
        try:
            if _playwright_instance:
                _playwright_instance.stop()
        except Exception:
            pass
        _browser_instance = None
        _playwright_instance = None


atexit.register(_close_browser)


def _new_context(browser):
    return browser.new_context(
        user_agent=(
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) '
            'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
        ),
        viewport={'width': 375, 'height': 812},
        locale='zh-CN',
        is_mobile=True,
    )


def _collect_sku_ids_from_variant_payload(response_data, primary_id=None):
    ids = set()
    if primary_id:
        ids.add(str(primary_id))
    if not isinstance(response_data, dict):
        return ids
    data = response_data.get("data") or {}
    template_data = data.get("template_data") or []
    if isinstance(template_data, list):
        for block in template_data:
            if not isinstance(block, dict):
                continue
            content = block.get("contentE1") or {}
            if isinstance(content, dict) and content.get("id"):
                ids.add(str(content.get("id")))
    try:
        raw_json = json.dumps(response_data, ensure_ascii=False)
        for m in re.finditer(r'"skuId"\s*:\s*"([a-f0-9]{24})"', raw_json):
            ids.add(m.group(1))
    except Exception:
        pass
    return ids


def _parse_edith_detail(response_data, item_id):
    try:
        data = response_data.get("data", {})
        template_data = data.get("template_data", [])
        if not template_data:
            return None
        t = template_data[0] if isinstance(template_data, list) else template_data
        if not isinstance(t, dict):
            return None

        seller = t.get("sellerH5") or {}
        store_id = str(seller.get("id") or "")

        related_ids = set()
        if item_id:
            related_ids.add(str(item_id))

        id_keys = (
            "id", "item_id", "sku_id", "goods_id", "product_id", "itemId", "skuId",
            "spu_id", "spuId", "saleSkuId", "displayItemId", "mainItemId",
        )

        def _walk_collect_ids(node, depth=0):
            if depth > 16:
                return
            if isinstance(node, dict):
                for key in id_keys:
                    val = node.get(key)
                    if val is not None:
                        s = str(val).strip()
                        if len(s) >= 16:
                            related_ids.add(s)
                for val in node.values():
                    _walk_collect_ids(val, depth + 1)
            elif isinstance(node, list):
                for val in node:
                    _walk_collect_ids(val, depth + 1)
            elif isinstance(node, str):
                for m in re.finditer(r"[a-f0-9]{24}", node):
                    related_ids.add(m.group(0))
                for m in re.finditer(r"goods-detail/([a-f0-9]{24})", node):
                    related_ids.add(m.group(1))

        _walk_collect_ids(response_data)
        _walk_collect_ids(t)
        try:
            raw_json = json.dumps(response_data, ensure_ascii=False)
            for m in re.finditer(r"[a-f0-9]{24}", raw_json):
                related_ids.add(m.group(0))
        except Exception:
            pass
        if store_id:
            related_ids.discard(store_id)

        store_name = seller.get("name") or ""
        fans = _parse_chinese_number(seller.get("fansAmount") or "0")
        store_sales = _parse_chinese_number(seller.get("salesVolume") or "0")

        if not store_id:
            link = seller.get("link") or ""
            match = re.search(r"/shop/([a-zA-Z0-9]+)", link)
            if match:
                store_id = match.group(1)

        desc_h5 = t.get("descriptionH5") or {}
        title = desc_h5.get("name") or desc_h5.get("desc") or ""

        price = 0.0
        price_h5 = t.get("priceH5") or {}
        highlight = price_h5.get("highlightPrice")
        if highlight is not None:
            try:
                price = float(highlight)
            except Exception:
                pass
        if price == 0:
            deal_price = price_h5.get("dealPrice") or {}
            dp = deal_price.get("price")
            if dp is not None:
                try:
                    price = float(dp)
                except Exception:
                    pass

        sales = 0
        iat = price_h5.get("itemAnalysisDataText") or desc_h5.get("itemAnalysisDataText") or ""
        if iat:
            sales = _parse_chinese_number(iat)

        location = ""
        for key_path in (
            ("goodsDistributeV4", "location"),
            ("deliveryInfo", "from"),
            ("freightInfo", "sendFrom"),
        ):
            block = t.get(key_path[0]) or {}
            if isinstance(block, dict) and block.get(key_path[1]):
                raw_location = block[key_path[1]]
                if isinstance(raw_location, str):
                    location = raw_location
                elif isinstance(raw_location, dict):
                    location = raw_location.get("name") or raw_location.get("text") or str(raw_location)
                else:
                    location = str(raw_location)
                break

        return {
            "store_id": store_id,
            "store_name": store_name,
            "product_name": title,
            "product_price": price,
            "product_sales": sales,
            "store_followers": fans,
            "store_sales": store_sales,
            "shipping_from": location,
            "related_item_ids": list(related_ids),
        }
    except Exception as e:
        _logger.error("解析edith/detail数据失败: %s", e)
        return None


def _fetch_goods_detail_via_browser(context, item_id):
    page = None
    detail_data = [None]
    variant_data = []

    def handle_response(response):
        try:
            url = response.url
            if response.status != 200:
                return
            if "edith/detail" in url and "variant" not in url:
                detail_data[0] = response.json()
            elif "/toc/variant" in url or "edith/detail/h5/toc/variant" in url:
                variant_data.append(response.json())
        except Exception:
            pass

    try:
        page = context.new_page()
        page.on("response", handle_response)

        url = "https://www.xiaohongshu.com/goods-detail/" + str(item_id)
        page.goto(url, wait_until="domcontentloaded", timeout=30000)

        for _ in range(10):
            if detail_data[0]:
                break
            page.wait_for_timeout(1000)

        if not detail_data[0]:
            page_status = _check_page_status(page)
            if page_status == 'not_found':
                return {"error": "商品不存在或已下架", "product_id": item_id}
            if page_status == 'blocked':
                return {"error": "访问被限制", "product_id": item_id}
            return {"error": "未捕获edith/detail响应", "product_id": item_id}

        detail = _parse_edith_detail(detail_data[0], item_id)
        if not detail:
            return None

        sku_ids = set(detail.get("related_item_ids") or [])
        if item_id:
            sku_ids.add(str(item_id))
        store_id = detail.get("store_id")

        variant_url = (
            "https://mall.xiaohongshu.com/api/store/jpd/edith/detail/h5/toc/variant"
            "?item_id=" + str(item_id)
            + "&variant_click_type=3&source=h5&version=0.0.5"
        )
        try:
            resp = context.request.get(variant_url, timeout=15000)
            if resp.ok:
                variant_data.append(resp.json())
        except Exception:
            pass

        for payload in variant_data:
            if isinstance(payload, dict):
                sku_ids.update(_collect_sku_ids_from_variant_payload(payload, item_id))

        if store_id:
            sku_ids.discard(str(store_id))

        sku_list = sorted(sku_ids)
        detail["related_item_ids"] = sku_list
        return detail
    except Exception as e:
        _logger.error("Playwright获取商品详情异常: %s", e)
        return None
    finally:
        try:
            if page:
                page.close()
        except Exception:
            pass


def _find_shelf_time_in_responses(responses, target_id, related_ids=None, target_name=""):
    def _norm_title(text):
        s = str(text or "").strip().lower()
        for ch in ("·", "•", "|", "丨", "/", "-", "_", " "):
            s = s.replace(ch, "")
        return s

    def _title_core(text):
        s = str(text or "").strip()
        for sep in ("·", "•", "丨"):
            if sep in s:
                s = s.split(sep, 1)[0]
                break
        return _norm_title(s)

    def _titles_match(a, b):
        if not a or not b:
            return False
        na, nb = _norm_title(a), _norm_title(b)
        if na and nb and na == nb:
            return True
        ca, cb = _title_core(a), _title_core(b)
        if ca and cb:
            if ca == cb:
                return True
            short, long_ = (ca, cb) if len(ca) <= len(cb) else (cb, ca)
            if len(short) >= 8 and (long_.startswith(short) or short in long_):
                return True
        return False

    def _pick_shelf_time(item):
        on_shelf_time = item.get("on_shelf_time")
        if not on_shelf_time:
            return None
        return _convert_timestamp(on_shelf_time)

    match_ids = {str(target_id)}
    if related_ids:
        for rid in related_ids:
            if rid:
                match_ids.add(str(rid))

    for resp in responses:
        items = resp.get("data", [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            candidates = []
            for key in (
                "id", "item_id", "sku_id", "goods_id", "product_id",
                "itemId", "skuId", "spu_id", "spuId", "saleSkuId",
            ):
                val = item.get(key)
                if val is not None and str(val).strip():
                    candidates.append(str(val).strip())
            if not any(c in match_ids for c in candidates):
                continue
            converted = _pick_shelf_time(item)
            if not converted:
                continue
            return converted

    if target_name:
        for resp in responses:
            items = resp.get("data", [])
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                name = item.get("name") or item.get("title") or item.get("card_title") or item.get("desc") or ""
                if not _titles_match(target_name, name):
                    continue
                converted = _pick_shelf_time(item)
                if converted:
                    return converted

    return None


def _fetch_store_goods_responses(context, store_id, item_id, related_ids=None, target_name=""):
    shop_responses = []
    api_url_base = f'https://www.xiaohongshu.com/api/store/vs/{store_id}/skus'
    referer = f'https://www.xiaohongshu.com/vendor/{store_id}'

    for page in range(30):
        try:
            api_url = f'{api_url_base}?page={page}'
            resp = context.request.get(
                api_url,
                headers={
                    'Referer': referer,
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-origin',
                    'Accept': 'application/json, text/plain, */*',
                },
                timeout=15000
            )
            if not resp.ok:
                break
            data = resp.json()
            if data.get('error_code') not in (0, None) and data.get('success') is not True:
                break

            raw_data = data.get('data', [])
            if raw_data is None:
                break
            if isinstance(raw_data, list):
                items = raw_data
                no_more = len(items) < 20
            elif isinstance(raw_data, dict):
                no_more = raw_data.get('no_more_items', False)
                items = raw_data.get('items', raw_data.get('skus', []))
                if not isinstance(items, list):
                    items = []
            else:
                break

            if not items:
                break

            shop_responses.append({'data': items})

            shelf_time = _find_shelf_time_in_responses(shop_responses, item_id, related_ids, target_name)
            if shelf_time:
                return shop_responses, shelf_time

            if no_more:
                break
        except Exception as e:
            _logger.warning("获取店铺商品列表第%d页异常: %s", page, e)
            break

    shelf_time = _find_shelf_time_in_responses(shop_responses, item_id, related_ids, target_name)
    return shop_responses, shelf_time


def _fetch_edith_detail_http(product_id):
    url = (
        "https://mall.xiaohongshu.com/api/store/jpd/edith/detail/h5/toc"
        f"?item_id={product_id}&source=h5&version=0.0.5"
    )
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
                "Mobile/15E148 Safari/604.1"
            ),
            "Referer": f"https://www.xiaohongshu.com/goods-detail/{product_id}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        return _parse_edith_detail_http(raw, product_id)
    except Exception:
        return None


def _parse_edith_detail_http(raw, product_id):
    try:
        data = raw.get("data", {}) if isinstance(raw, dict) else {}
        template_data = data.get("template_data")
        if isinstance(template_data, list) and template_data:
            t = template_data[0]
        elif isinstance(data, dict):
            t = data
        else:
            return None
        if not isinstance(t, dict):
            return None

        desc_h5 = t.get("descriptionH5") or {}
        title = (desc_h5.get("name") or t.get("title") or "").strip()
        price_h5 = t.get("priceH5") or {}
        price = 0.0
        dp = price_h5.get("highlightPrice") or price_h5.get("price")
        if dp is not None:
            try:
                price = float(dp)
            except (TypeError, ValueError):
                pass
        if price == 0:
            deal_price = price_h5.get("dealPrice") or {}
            dp2 = deal_price.get("price") if isinstance(deal_price, dict) else None
            if dp2 is not None:
                try:
                    price = float(dp2)
                except (TypeError, ValueError):
                    pass

        sales = 0
        iat = price_h5.get("itemAnalysisDataText") or desc_h5.get("itemAnalysisDataText") or ""
        if iat:
            sales = _parse_chinese_number(iat)

        return {
            "product_id": product_id,
            "product_name": title,
            "product_price": price,
            "product_sales": sales,
        }
    except Exception:
        return None


def _enrich_query_payload(payload):
    out = dict(payload or {})
    pid = out.get("product_id")
    if not pid:
        return out

    need_sales = not out.get("product_sales")
    if not need_sales:
        return out

    parsed = _fetch_edith_detail_http(str(pid))
    if not isinstance(parsed, dict):
        return out

    for key in ("product_name", "product_price", "product_sales"):
        val = parsed.get(key)
        if val in (None, "", 0):
            continue
        if not out.get(key):
            out[key] = val

    return out


def query_shelf_time(product_id, url=None, cached_shelf_time=None, browser=None):
    pid = product_id or _extract_product_id_from_url(url or "")
    if not pid:
        return {"error": "缺少有效商品ID"}

    own_browser = False
    if browser is None:
        browser = _ensure_browser()
        own_browser = True
    if not browser:
        return {"error": "浏览器启动失败"}

    context = None
    try:
        context = _new_context(browser)

        detail = _fetch_goods_detail_via_browser(context, pid)
        if not detail or detail.get("error"):
            return {"product_id": pid, "error": (detail or {}).get("error", "无法获取商品详情")}

        shelf_time = cached_shelf_time or ""
        if not shelf_time:
            store_id = detail.get("store_id", "")
            if store_id:
                related = detail.get("related_item_ids") or []
                target_name = detail.get("product_name") or ""
                _, shelf_time = _fetch_store_goods_responses(context, store_id, pid, related, target_name)

        result = {
            "product_id": pid,
            "product_name": detail.get("product_name"),
            "product_price": detail.get("product_price") or 0,
            "product_sales": detail.get("product_sales") or 0,
            "store_id": detail.get("store_id"),
            "store_name": detail.get("store_name"),
            "store_followers": detail.get("store_followers") or 0,
            "store_sales": detail.get("store_sales") or 0,
            "shipping_from": detail.get("shipping_from"),
            "on_shelf_time": shelf_time or "",
            "related_item_ids": detail.get("related_item_ids") or [],
        }

        result = _enrich_query_payload(result)

        if cached_shelf_time and not result.get("on_shelf_time"):
            result["on_shelf_time"] = cached_shelf_time
            result["shelf_time_source"] = "database"
        elif result.get("on_shelf_time"):
            result["shelf_time_source"] = "scraper"
        else:
            result["shelf_time_source"] = "unknown"

        return result
    except Exception as e:
        _logger.warning("query_shelf_time异常: %s", e)
        return {"error": f"查询异常: {e}"}
    finally:
        try:
            if context:
                context.close()
        except Exception:
            pass


def _load_shelf_done():
    global _shelf_done_loaded
    if _shelf_done_loaded:
        return
    with _shelf_done_lock:
        if _shelf_done_loaded:
            return
        if os.path.exists(SHELF_TIME_DONE_FILE):
            try:
                with open(SHELF_TIME_DONE_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                obj = json.loads(line)
                                gid = obj.get('gid') or obj.get('goods_id')
                                if gid:
                                    _shelf_done_set.add(gid)
                            except Exception:
                                pass
            except Exception:
                pass
        _shelf_done_loaded = True


def _mark_shelf_done(goods_id):
    with _shelf_done_lock:
        if goods_id in _shelf_done_set:
            return
        _shelf_done_set.add(goods_id)
    try:
        with open(SHELF_TIME_DONE_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps({'gid': goods_id, 'ts': time.time()}) + '\n')
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        pass


def _cleanup_shelf_done(max_age_days=7):
    if not os.path.exists(SHELF_TIME_DONE_FILE):
        return
    cutoff = time.time() - max_age_days * 86400
    kept = []
    seen = set()
    try:
        with open(SHELF_TIME_DONE_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    gid = obj.get('gid') or obj.get('goods_id')
                    ts = obj.get('ts', 0)
                    if gid and gid not in seen and ts >= cutoff:
                        kept.append(line)
                        seen.add(gid)
                except Exception:
                    pass
        with open(SHELF_TIME_DONE_FILE, 'w', encoding='utf-8') as f:
            for line in kept:
                f.write(line + '\n')
    except Exception:
        pass


def get_shelf_candidates(top_n=999999):
    _load_shelf_done()
    conn = None
    try:
        conn = _db_conn()
        c = conn.cursor()
        c.execute('''
            SELECT goods_id FROM goods
            WHERE is_virtual=1 AND lifecycle<3
              AND velocity_1d > 5
              AND (store_id IS NULL OR store_id=''
                   OR shop_fans IS NULL OR shop_fans=''
                   OR shop_sales IS NULL OR shop_sales=''
                   OR shelf_time IS NULL OR shelf_time='')
            ORDER BY velocity_1d DESC
            LIMIT ?
        ''', (top_n,))
        results = []
        skipped = 0
        for row in c.fetchall():
            gid = row[0]
            with _shelf_done_lock:
                if gid in _shelf_done_set:
                    skipped += 1
                    continue
            results.append(gid)
        return results, skipped
    finally:
        if conn:
            conn.close()


def _update_goods_shelf_with_conn(c, goods_id, info):
    updates = []
    params = []
    if info.get('store_id'):
        updates.append("store_id=?")
        params.append(info['store_id'])
    if info.get('store_name'):
        updates.append("store_name=?")
        params.append(info['store_name'])
    if info.get('shop_sales'):
        updates.append("shop_sales=?")
        params.append(info['shop_sales'])
    if info.get('shop_fans'):
        updates.append("shop_fans=?")
        params.append(info['shop_fans'])
    if info.get('shelf_time'):
        updates.append("shelf_time=?")
        params.append(info['shelf_time'])
    if not updates:
        return
    updates.append("detail_fetched=1")
    updates.append("detail_fetch_time=datetime('now','localtime')")
    params.append(goods_id)
    c.execute(f"UPDATE goods SET {','.join(updates)} WHERE goods_id=?", params)


def _get_cached_shelf_time(goods_id):
    conn = None
    try:
        conn = _db_conn()
        c = conn.cursor()
        c.execute('SELECT shelf_time FROM goods WHERE goods_id=?', (goods_id,))
        row = c.fetchone()
        if row and row[0]:
            return row[0]
    except Exception:
        pass
    finally:
        if conn:
            conn.close()
    return None


def _shelf_db_writer():
    global _shelf_writer_running
    _BATCH_SIZE = 5
    _BATCH_TIMEOUT = 0.5
    _draining = False
    while _shelf_writer_running or not _shelf_write_queue.empty():
        batch = []
        try:
            first_task = _shelf_write_queue.get(timeout=1)
            if first_task is None:
                _shelf_write_queue.task_done()
                _draining = True
            else:
                batch.append(first_task)
            if _draining:
                while True:
                    try:
                        task = _shelf_write_queue.get_nowait()
                        if task is not None:
                            batch.append(task)
                        else:
                            _shelf_write_queue.task_done()
                    except queue.Empty:
                        break
            elif batch:
                deadline = time.time() + _BATCH_TIMEOUT
                while len(batch) < _BATCH_SIZE:
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        break
                    try:
                        task = _shelf_write_queue.get(timeout=min(remaining, 0.5))
                        if task is None:
                            _shelf_write_queue.task_done()
                            _draining = True
                            break
                        batch.append(task)
                    except queue.Empty:
                        break
                if _draining:
                    while True:
                        try:
                            task = _shelf_write_queue.get_nowait()
                            if task is not None:
                                batch.append(task)
                            else:
                                _shelf_write_queue.task_done()
                        except queue.Empty:
                            break
        except queue.Empty:
            if _draining:
                break
            continue

        if not batch:
            if _draining:
                break
            continue

        conn = None
        try:
            conn = _db_conn()
            c = conn.cursor()
            for gid, info in batch:
                try:
                    _update_goods_shelf_with_conn(c, gid, info)
                except Exception:
                    pass
            conn.commit()
        except Exception:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
        finally:
            if conn:
                conn.close()

        for _ in batch:
            _shelf_write_queue.task_done()

        if _draining and _shelf_write_queue.empty():
            break
    _shelf_writer_running = False


def _start_shelf_writer():
    global _shelf_writer_running, _shelf_writer_thread
    if _shelf_writer_running:
        return
    _shelf_writer_running = True
    _shelf_writer_thread = threading.Thread(target=_shelf_db_writer, daemon=True)
    _shelf_writer_thread.start()


def _stop_shelf_writer(timeout=60):
    global _shelf_writer_running
    _shelf_writer_running = False
    try:
        _shelf_write_queue.put(None, block=False)
    except queue.Full:
        pass
    if _shelf_writer_thread and _shelf_writer_thread.is_alive():
        _shelf_writer_thread.join(timeout=timeout)


atexit.register(_stop_shelf_writer)


def _shelf_worker(task_queue, result_queue, stop_event, delay_range=(0.01, 0.1), worker_id=0):
    own_playwright = None
    own_browser = None
    try:
        try:
            from playwright.sync_api import sync_playwright
            own_playwright = sync_playwright().start()
            own_browser = own_playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
            )
        except Exception as e:
            _logger.error("[Worker-%d] 浏览器启动失败: %s", worker_id, e)
            while not stop_event.is_set():
                try:
                    goods_id = task_queue.get(timeout=1)
                    if goods_id is None:
                        task_queue.task_done()
                        break
                    result_queue.put(('fail', goods_id, f'browser_init_failed: {e}'))
                    task_queue.task_done()
                except queue.Empty:
                    continue
            return

        while not stop_event.is_set():
            try:
                goods_id = task_queue.get(timeout=1)
            except queue.Empty:
                continue
            if goods_id is None:
                task_queue.task_done()
                break

            try:
                if not own_browser.is_connected():
                    try:
                        own_browser = own_playwright.chromium.launch(
                            headless=True,
                            args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
                        )
                    except Exception as e:
                        result_queue.put(('fail', goods_id, f'browser_reconnect_failed: {e}'))
                        task_queue.task_done()
                        continue
            except Exception:
                pass

            cached_shelf_time = _get_cached_shelf_time(goods_id)
            info = query_shelf_time(goods_id, browser=own_browser, cached_shelf_time=cached_shelf_time)
            if info and not info.get('error') and (info.get('store_id') or info.get('on_shelf_time')):
                _mark_shelf_done(goods_id)
                db_info = {
                    'store_id': info.get('store_id') or '',
                    'store_name': info.get('store_name') or '',
                    'shop_sales': info.get('store_sales') or 0,
                    'shop_fans': info.get('store_followers') or 0,
                    'shelf_time': info.get('on_shelf_time') or '',
                }
                try:
                    _shelf_write_queue.put((goods_id, db_info), block=True, timeout=5)
                except queue.Full:
                    result_queue.put(('fail', goods_id, 'write_queue_full'))
                    task_queue.task_done()
                    continue
                store_filled = 1 if info.get('store_id') else 0
                shelf_filled = 1 if info.get('on_shelf_time') else 0
                result_queue.put(('success', goods_id, store_filled, shelf_filled))
            else:
                err_reason = (info or {}).get('error', 'no_data') if info else 'no_data'
                result_queue.put(('fail', goods_id, err_reason))

            task_queue.task_done()
            if delay_range[1] > 0:
                time.sleep(random.uniform(*delay_range))
    finally:
        try:
            if own_browser:
                own_browser.close()
        except Exception:
            pass
        try:
            if own_playwright:
                own_playwright.stop()
        except Exception:
            pass


def run_shelf_time_enrich(log_func=print, concurrency=3, delay_min=0.01, delay_max=0.1):
    global _is_shelf_running, _shelf_progress

    if _is_shelf_running:
        log_func("[Playwright] 已在运行中")
        return 0

    _is_shelf_running = True
    _shelf_progress = {'success': 0, 'fail': 0, 'store_filled': 0, 'shelf_filled': 0, 'total': 0}

    try:
        from playwright.sync_api import sync_playwright
        _test_pw = sync_playwright().start()
        _test_browser = _test_pw.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
        )
        _test_browser.close()
        _test_pw.stop()
    except Exception as e:
        log_func(f"[Playwright] 浏览器启动失败，请检查Chromium是否安装: {e}")
        _is_shelf_running = False
        return 0

    _load_shelf_done()
    _cleanup_shelf_done(max_age_days=7)

    candidates, skipped = get_shelf_candidates()
    if not candidates:
        log_func(f"[Playwright] 无待补全商品 (跳过已标记 {skipped} 个)")
        _is_shelf_running = False
        return 0

    _shelf_progress['total'] = len(candidates)
    log_func(f"[Playwright] {len(candidates)} 个商品待补全 (跳过已标记 {skipped} 个, 并发={concurrency})")

    _start_shelf_writer()

    task_queue = queue.Queue()
    result_queue = queue.Queue()
    stop_event = threading.Event()

    for gid in candidates:
        task_queue.put(gid)

    workers = []
    for i in range(concurrency):
        t = threading.Thread(
            target=_shelf_worker,
            args=(task_queue, result_queue, stop_event, (delay_min, delay_max), i + 1),
            daemon=True
        )
        t.start()
        workers.append(t)
        task_queue.put(None)

    processed = 0
    total = len(candidates)
    _fail_reason_counter = {}
    _first_fail_logged = 0
    while _is_shelf_running:
        try:
            result = result_queue.get(timeout=1)
            processed += 1
            status = result[0]
            gid = result[1]
            if status == 'success':
                with _shelf_progress_lock:
                    _shelf_progress['success'] += 1
                    _shelf_progress['store_filled'] += result[2] if len(result) > 2 else 0
                    _shelf_progress['shelf_filled'] += result[3] if len(result) > 3 else 0
                if processed % 50 == 0 or processed <= 5:
                    log_func(f"[Playwright] {processed}/{total} {gid[:12]}... 成功")
            else:
                reason = result[2] if len(result) > 2 else 'unknown'
                _fail_reason_counter[reason] = _fail_reason_counter.get(reason, 0) + 1
                with _shelf_progress_lock:
                    _shelf_progress['fail'] += 1
                if _first_fail_logged < 3:
                    log_func(f"[Playwright] {processed}/{total} {gid[:12]}... 失败原因: {reason}")
                    _first_fail_logged += 1
                if processed % 100 == 0:
                    top_reasons = sorted(_fail_reason_counter.items(), key=lambda x: -x[1])[:3]
                    reasons_str = ', '.join(f"{k}={v}" for k, v in top_reasons)
                    log_func(f"[Playwright] {processed}/{total} 进度中... (成功={_shelf_progress['success']}, 失败={_shelf_progress['fail']}, 失败原因[{reasons_str}])")
        except queue.Empty:
            alive = any(w.is_alive() for w in workers)
            if not alive and task_queue.empty():
                break
            if not _is_shelf_running:
                break
            continue

    stop_event.set()
    for w in workers:
        w.join(timeout=5)

    while True:
        try:
            result = result_queue.get_nowait()
            processed += 1
            if result[0] == 'success':
                with _shelf_progress_lock:
                    _shelf_progress['success'] += 1
                    _shelf_progress['store_filled'] += result[2] if len(result) > 2 else 0
                    _shelf_progress['shelf_filled'] += result[3] if len(result) > 3 else 0
            else:
                with _shelf_progress_lock:
                    _shelf_progress['fail'] += 1
        except queue.Empty:
            break

    _stop_shelf_writer(timeout=60)

    with _shelf_progress_lock:
        p = dict(_shelf_progress)

    log_func(f"[Playwright] 完成: 成功={p['success']}, 失败={p['fail']}, "
             f"店铺补全={p['store_filled']}, 上架时间补全={p['shelf_filled']}")

    _is_shelf_running = False
    return p['success']


def stop_shelf_time_enrich(log_func=print):
    global _is_shelf_running
    if not _is_shelf_running:
        return
    log_func("[Playwright] 用户停止")
    _is_shelf_running = False


def get_shelf_progress():
    with _shelf_progress_lock:
        return dict(_shelf_progress)


def is_shelf_running():
    return _is_shelf_running


def check_api_available():
    return _ensure_browser() is not None
