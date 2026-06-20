# -*- coding: utf-8 -*-
import os
import sqlite3
import threading
import time
import logging
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "crawl_data")
DB_PATH = os.path.join(DATA_DIR, "xhs_burst_monitor.db")

_logger = logging.getLogger(__name__)
_thread_local = threading.local()


def _db_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=30000')
    conn.execute('PRAGMA synchronous=NORMAL')
    return conn


def _get_collector():
    """每线程独立 session，避免全局锁把并发 HTTP 串行化。"""
    if getattr(_thread_local, "ready", False):
        return _thread_local.collector, _thread_local.session, _thread_local.headers
    try:
        from shop_collectors import GoodsDetailCollector, _generate_fingerprint, _create_session
        collector = GoodsDetailCollector(config={}, log_func=None)
        headers, fp_profile = _generate_fingerprint()
        impersonate = fp_profile.get('impersonate') if hasattr(fp_profile, 'get') else None
        session = _create_session(
            proxy_str=None, cookie_str='', impersonate=impersonate, fp_profile=fp_profile
        )
        _thread_local.collector = collector
        _thread_local.session = session
        _thread_local.headers = headers
        _thread_local.ready = True
        return collector, session, headers
    except Exception as e:
        _logger.warning("WebFallback初始化失败: %s", e)
        return None, None, None


def _upsert_store_scores(c, store_id, store_name, shop_fans, shop_sales, now_str):
    if not store_id:
        return
    try:
        fans_int = int(float(shop_fans)) if shop_fans and shop_fans not in ('0', '') else 0
    except (TypeError, ValueError):
        fans_int = 0
    c.execute(
        '''INSERT OR IGNORE INTO store_scores (store_id, store_name, last_scan, scan_count)
           VALUES (?, ?, ?, 1)''',
        (store_id, store_name, now_str),
    )
    c.execute(
        '''UPDATE store_scores SET
           store_name=COALESCE(NULLIF(store_name,''),?),
           fans_count=CASE WHEN ?>0 THEN ? ELSE COALESCE(fans_count,0) END,
           shop_sales=CASE WHEN ?!='0' AND ?!='' THEN ? ELSE COALESCE(NULLIF(shop_sales,''),'') END,
           last_scan=?
           WHERE store_id=?''',
        (
            store_name,
            fans_int, fans_int,
            shop_sales, shop_sales, shop_sales,
            now_str, store_id,
        ),
    )


def _save_goods_detail_web_snapshot(c, goods_id, detail, now_str):
    """写入 goods_detail_web 快照；跳过图片、价格、商品销量、上架时间。"""
    product_name = str(detail.get('product_name', '') or '')
    shop_name = str(detail.get('shop_name', '') or '')
    shop_id = str(detail.get('shop_id', '') or '')
    try:
        fans_count = int(detail.get('fans_count', 0) or 0)
    except (TypeError, ValueError):
        fans_count = 0
    shop_score = str(detail.get('shop_score', '') or '')
    try:
        shop_total_sales = int(detail.get('shop_total_sales', 0) or 0)
    except (TypeError, ValueError):
        shop_total_sales = 0
    ship_from = str(detail.get('ship_from', '') or '')
    category_tag = str(detail.get('category_tag', '') or '')
    data_source = str(detail.get('data_source', '') or 'product_detail')

    c.execute("SELECT goods_id FROM goods_detail_web WHERE goods_id = ?", (goods_id,))
    if c.fetchone():
        c.execute(
            '''UPDATE goods_detail_web SET
               web_product_name = COALESCE(NULLIF(?, ''), web_product_name),
               web_shop_name = COALESCE(NULLIF(?, ''), web_shop_name),
               web_shop_id = COALESCE(NULLIF(?, ''), web_shop_id),
               web_fans_count = CASE WHEN ?>0 THEN ? ELSE web_fans_count END,
               web_shop_score = COALESCE(NULLIF(?, ''), web_shop_score),
               web_shop_total_sales = CASE WHEN ?>0 THEN ? ELSE web_shop_total_sales END,
               web_ship_from = COALESCE(NULLIF(?, ''), web_ship_from),
               web_category_tag = COALESCE(NULLIF(?, ''), web_category_tag),
               web_data_source = ?,
               web_fetch_time = ?,
               updated_at = ?
               WHERE goods_id = ?''',
            (
                product_name,
                shop_name, shop_id,
                fans_count, fans_count,
                shop_score,
                shop_total_sales, shop_total_sales,
                ship_from,
                category_tag,
                data_source,
                now_str,
                now_str,
                goods_id,
            ),
        )
    else:
        c.execute(
            '''INSERT INTO goods_detail_web (
               goods_id, web_product_name, web_shop_name, web_shop_id,
               web_fans_count, web_shop_score, web_shop_total_sales,
               web_ship_from, web_category_tag,
               web_data_source, web_fetch_time
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                goods_id,
                product_name,
                shop_name,
                shop_id,
                fans_count,
                shop_score,
                shop_total_sales,
                ship_from,
                category_tag,
                data_source,
                now_str,
            ),
        )


def _apply_web_detail_to_goods(c, goods_id, detail, now_str):
    store_id = str(detail.get('shop_id', '') or '')
    store_name = str(detail.get('shop_name', '') or '')
    shop_fans = str(detail.get('fans_count', 0) or 0)
    shop_sales = str(detail.get('shop_total_sales', 0) or 0)
    title = str(detail.get('product_name', '') or '')
    shop_item_score = str(detail.get('shop_score', '') or '')
    region = str(detail.get('ship_from', '') or '')
    category_tag = str(detail.get('category_tag', '') or '')
    data_source = str(detail.get('data_source', '') or 'web_detail')

    c.execute(
        '''UPDATE goods SET
            title=COALESCE(NULLIF(title,''),?),
            store_id=COALESCE(NULLIF(store_id,''),?),
            store_name=COALESCE(NULLIF(store_name,''),?),
            shop_fans=CASE WHEN ?!='0' AND ?!='' THEN ? ELSE COALESCE(NULLIF(shop_fans,''),'') END,
            shop_sales=CASE WHEN ?!='0' AND ?!='' THEN ? ELSE COALESCE(NULLIF(shop_sales,''),'') END,
            shop_item_score=COALESCE(NULLIF(shop_item_score,''),?),
            region=COALESCE(NULLIF(region,''),?),
            goods_type_detail=COALESCE(NULLIF(goods_type_detail,''),?),
            data_source=COALESCE(NULLIF(data_source,''),?),
            detail_fetched=1,
            detail_fetch_time=?
        WHERE goods_id=?''',
        (
            title,
            store_id, store_name,
            shop_fans, shop_fans, shop_fans,
            shop_sales, shop_sales, shop_sales,
            shop_item_score,
            region,
            category_tag,
            data_source,
            now_str,
            goods_id,
        ),
    )
    _upsert_store_scores(c, store_id, store_name, shop_fans, shop_sales, now_str)
    _save_goods_detail_web_snapshot(c, goods_id, detail, now_str)


def save_store_fields_to_goods(goods_id, detail):
    """
    Web 详情写入 goods + store_scores + goods_detail_web。
    跳过：image_url、deal_price、origin_price、sold_num、shelf_time（详情接口不提供）。
    """
    conn = None
    try:
        conn = _db_conn()
        c = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _apply_web_detail_to_goods(c, goods_id, detail, now_str)
        conn.commit()
        return True
    except Exception as e:
        _logger.warning("WebDetail写入goods失败 %s: %s", goods_id, e)
        return False
    finally:
        if conn:
            conn.close()


def _save_to_goods_table(goods_id, detail):
    return save_store_fields_to_goods(goods_id, detail)


def fetch_store_fields_web(goods_id):
    """
    HTTP 商品详情 edith/detail/h5/toc（多引擎回退，对齐补缺挂机）。
    返回 (detail_dict|None, status) status: ok | no_store | fail
    """
    try:
        from xhs_full_sold_fetch import fetch_sold_detail
        detail, status, meta = fetch_sold_detail(goods_id, engine="api", auto_fallback=True)
        if status == "ok" and detail:
            if not detail.get("shop_id"):
                return None, "no_store"
            detail["data_source"] = "product_detail"
            return detail, "ok"
        if status == "no_store":
            return None, "no_store"
        return None, "fail"
    except Exception as e:
        _logger.warning("WebDetail获取失败 %s: %s", goods_id, e)
        return None, "fail"


def fetch_goods_detail_web(goods_id):
    detail, status = fetch_store_fields_web(goods_id)
    if status == "ok" and detail:
        _save_to_goods_table(goods_id, detail)
        return detail
    return None


def fetch_batch_web(goods_ids, log_func=None, max_workers=5):
    from concurrent.futures import ThreadPoolExecutor, as_completed

    success = 0
    fail = 0
    total = len(goods_ids)

    if log_func:
        log_func(f"[Web-Fallback] 开始批量补充 {total} 个商品 (并发={max_workers})")

    def _fetch_one(gid):
        return gid, fetch_goods_detail_web(gid)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_one, gid): gid for gid in goods_ids}
        for i, future in enumerate(as_completed(futures)):
            try:
                gid, detail = future.result()
                if detail:
                    success += 1
                else:
                    fail += 1
            except Exception:
                fail += 1

            if log_func and (i + 1) % 50 == 0:
                log_func(f"[Web-Fallback] 进度 {i+1}/{total} (成功={success} 失败={fail})")

    if log_func:
        log_func(f"[Web-Fallback] 完成: 成功={success} 失败={fail}")

    return success, fail
