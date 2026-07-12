# -*- coding: utf-8 -*-
import os
import re
import sys
import time
import json
import sqlite3
import random
import hashlib
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

import requests
from requests.adapters import HTTPAdapter

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
DATA_DIR = os.path.join(APP_DIR, "crawl_data")
os.makedirs(DATA_DIR, exist_ok=True)

VIRTUAL_POSITIVE_KW = [
    "电子版", "电zi版", "数字版", "网盘发货", "自动发货", "无物流", "无需物流",
    "PDF", "Word", "PPT", "Excel", "PSD", "FBX", "Blender", "C4D",
    "模板", "素材", "资源", "资料", "预设", "笔刷", "插件",
    "源文件", "源码", "课程", "真题", "题库",
]

PHYSICAL_KW = [
    "鼠标垫", "键盘膜", "面包", "零食", "连衣裙", "T恤", "运动鞋",
    "手机壳", "数据线", "杯子", "收纳盒", "枕头", "毛巾",
]

_P_V_POS = re.compile("|".join(re.escape(k) for k in VIRTUAL_POSITIVE_KW), re.IGNORECASE)
_P_PHY = re.compile("|".join(re.escape(k) for k in PHYSICAL_KW))


def _classify_virtual(title):
    if not title:
        return -1
    if _P_V_POS.search(str(title)):
        return 1
    if _P_PHY.search(str(title)):
        return 0
    return -1


def _log(msg, log_func=None):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{ts}] {msg}"
    if log_func:
        try:
            log_func(line)
        except Exception:
            print(line)
    else:
        print(line)


def _convert_timestamp(ts):
    if not ts:
        return ''
    try:
        if isinstance(ts, (int, float)):
            if ts > 1e12:
                ts = ts / 1000
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        return str(ts)
    except Exception:
        return str(ts)


UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
]

SEC_CH_UA_POOL = [
    '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
    '"Google Chrome";v="146", "Not.A/Brand";v="8", "Chromium";v="146"',
    '"Google Chrome";v="145", "Not.A/Brand";v="8", "Chromium";v="145"',
    '"Google Chrome";v="144", "Not.A/Brand";v="8", "Chromium";v="144"',
]

_FP_GPU_CONFIGS = [
    {"vendor": "NVIDIA Corporation", "renderer": "NVIDIA GeForce GTX 1650/PCIe/SSE2", "mem": 8, "cores": 6},
    {"vendor": "NVIDIA Corporation", "renderer": "NVIDIA GeForce RTX 3060/PCIe/SSE2", "mem": 16, "cores": 12},
    {"vendor": "NVIDIA Corporation", "renderer": "NVIDIA GeForce RTX 4060/PCIe/SSE2", "mem": 16, "cores": 12},
    {"vendor": "NVIDIA Corporation", "renderer": "NVIDIA GeForce GTX 1060 6GB/PCIe/SSE2", "mem": 8, "cores": 6},
    {"vendor": "NVIDIA Corporation", "renderer": "NVIDIA GeForce RTX 3070/PCIe/SSE2", "mem": 16, "cores": 14},
    {"vendor": "Intel Inc.", "renderer": "Intel(R) UHD Graphics 630", "mem": 8, "cores": 8},
    {"vendor": "Intel Inc.", "renderer": "Intel Iris Xe Graphics", "mem": 8, "cores": 8},
    {"vendor": "X.Org", "renderer": "AMD Radeon RX 580 Series (polaris10, LLVM 15.0.7, DRM 3.49, 6.1.0)", "mem": 8, "cores": 8},
    {"vendor": "NVIDIA Corporation", "renderer": "NVIDIA GeForce RTX 2060/PCIe/SSE2", "mem": 8, "cores": 8},
    {"vendor": "NVIDIA Corporation", "renderer": "NVIDIA GeForce GTX 1660 SUPER/PCIe/SSE2", "mem": 8, "cores": 8},
]

_FP_RESOLUTIONS = [
    (1920, 1080), (1366, 768), (1536, 864), (1440, 900), (2560, 1440),
    (3840, 2160), (1680, 1050), (1280, 720), (1600, 900),
]

_FP_BROWSER_VERSIONS = [
    ("chrome120", 120), ("chrome123", 123), ("chrome124", 124),
    ("chrome131", 131),
]

_FP_OS_CONFIGS = [
    {"name": "win10", "platform": "Win32", "sec_ch_ua_platform": '"Windows"'},
    {"name": "win11", "platform": "Win32", "sec_ch_ua_platform": '"Windows"'},
    {"name": "mac", "platform": "MacIntel", "sec_ch_ua_platform": '"macOS"'},
]

_FP_LANG_POOL = [
    "zh-CN,zh;q=0.9,en;q=0.8", "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "zh-CN,zh;q=0.9,ja;q=0.7", "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7",
    "zh-CN,zh;q=1.0,en;q=0.9",
]

_FP_NOT_A_BRAND = [
    '"Not_A Brand";v="24"', '"Not_A Brand";v="99"', '"Not;A=Brand";v="99"',
    '"Not/A)Brand";v="8"', '"Not)A;Brand";v="24"',
]

_FP_VIEWPORT_OFFSETS = [72, 80, 85, 90, 100, 110, 120, 132]

_FP_MAC_GPUS = [
    {"vendor": "Apple Inc.", "renderer": "Apple GPU", "mem": 8, "cores": 8},
    {"vendor": "Apple Inc.", "renderer": "Apple M1", "mem": 8, "cores": 8},
    {"vendor": "Apple Inc.", "renderer": "Apple M2", "mem": 16, "cores": 8},
]

_FP_MAC_RES = [(1440, 900), (1680, 1050), (2560, 1600), (1920, 1080)]

_API_DEVICE_PROFILES = [
    {'platform': 'Windows', 'screen': (1920, 1080), 'dpr': 1.0, 'color_depth': 24, 'mem': 8, 'cores': 8},
    {'platform': 'Windows', 'screen': (2560, 1440), 'dpr': 1.0, 'color_depth': 24, 'mem': 16, 'cores': 12},
    {'platform': 'Windows', 'screen': (1366, 768), 'dpr': 1.0, 'color_depth': 24, 'mem': 4, 'cores': 4},
    {'platform': 'Windows', 'screen': (1536, 864), 'dpr': 1.25, 'color_depth': 24, 'mem': 8, 'cores': 6},
    {'platform': 'Windows', 'screen': (1440, 900), 'dpr': 1.0, 'color_depth': 24, 'mem': 16, 'cores': 8},
    {'platform': 'Windows', 'screen': (3840, 2160), 'dpr': 2.0, 'color_depth': 24, 'mem': 32, 'cores': 16},
    {'platform': 'Windows', 'screen': (1280, 720), 'dpr': 1.0, 'color_depth': 24, 'mem': 4, 'cores': 2},
    {'platform': 'Windows', 'screen': (1600, 900), 'dpr': 1.0, 'color_depth': 24, 'mem': 8, 'cores': 6},
    {'platform': 'macOS', 'screen': (2560, 1600), 'dpr': 2.0, 'color_depth': 30, 'mem': 16, 'cores': 8},
    {'platform': 'macOS', 'screen': (1440, 900), 'dpr': 2.0, 'color_depth': 30, 'mem': 8, 'cores': 6},
    {'platform': 'macOS', 'screen': (1680, 1050), 'dpr': 2.0, 'color_depth': 30, 'mem': 16, 'cores': 10},
    {'platform': 'macOS', 'screen': (2880, 1800), 'dpr': 2.0, 'color_depth': 30, 'mem': 16, 'cores': 12},
    {'platform': 'macOS', 'screen': (1920, 1200), 'dpr': 2.0, 'color_depth': 30, 'mem': 8, 'cores': 8},
]

_API_LANG_VARIANTS = [
    'zh-CN,zh;q=0.9,en;q=0.8',
    'zh-CN,zh;q=0.9',
    'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7',
    'zh-CN,zh;q=0.9,ja;q=0.7,en;q=0.6',
    'zh-TW,zh;q=0.9,en;q=0.8',
    'zh-CN,zh;q=1.0,en;q=0.9',
    'zh-CN,zh;q=0.9,ko;q=0.7,en;q=0.6',
]

_API_SEC_FETCH_MODES = {
    'navigate': {
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
    },
    'ajax': {
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
    },
}

_API_RISK_CONTROL_KEYWORDS = [
    'captcha', 'verify', 'blocked', 'forbidden', 'rate limit',
    'access denied', '安全验证', '请求过于频繁',
]

_FP_POOL = None
_FP_POOL_LOCK = threading.Lock()


def _generate_fp_pool(count=5000):
    pool = []
    seen = set()
    for i in range(count):
        r = random.Random(i * 31337 + 7)
        gpu = r.choice(_FP_GPU_CONFIGS)
        res = r.choice(_FP_RESOLUTIONS)
        browser = r.choice(_FP_BROWSER_VERSIONS)
        os_cfg = r.choice(_FP_OS_CONFIGS)
        lang = r.choice(_FP_LANG_POOL)
        color_depth = r.choice([24, 30, 32])
        pixel_ratio = r.choice([1.0, 1.25, 1.5, 2.0])
        vp_off = r.choice(_FP_VIEWPORT_OFFSETS)
        not_brand = r.choice(_FP_NOT_A_BRAND)
        is_mac = os_cfg["name"] == "mac"

        actual_vendor = gpu["vendor"]
        actual_renderer = gpu["renderer"]
        dev_mem = gpu["mem"]
        hw_conc = gpu["cores"]

        if is_mac:
            mg = r.choice(_FP_MAC_GPUS)
            actual_vendor = mg["vendor"]
            actual_renderer = mg["renderer"]
            dev_mem = mg["mem"]
            hw_conc = mg["cores"]
            res = r.choice(_FP_MAC_RES)

        w, h = res
        vp_h = h - vp_off
        imp, ver = browser

        if is_mac:
            ua = f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36"
        else:
            ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36"

        nb = not_brand.replace("{ver}", str(ver))
        sec_ch_ua = f'"Chromium";v="{ver}", "Google Chrome";v="{ver}", {nb}'
        platform = "MacIntel" if is_mac else "Win32"

        fp_str = f"{actual_vendor}|{actual_renderer}|{w}x{h}|{ua}|{lang}|{color_depth}|{pixel_ratio}|{imp}"
        fp_hash = hashlib.md5(fp_str.encode()).hexdigest()[:12]
        if fp_hash in seen:
            fp_hash = hashlib.md5(f"{fp_str}_{i}_{r.random()}".encode()).hexdigest()[:12]
        seen.add(fp_hash)

        pool.append({
            "fp_id": f"fp_{i:05d}_{fp_hash}",
            "ua": ua,
            "platform": platform,
            "sec_ch_ua": sec_ch_ua,
            "sec_ch_ua_platform": os_cfg["sec_ch_ua_platform"],
            "viewport_width": w,
            "viewport_height": vp_h,
            "screen_width": w,
            "screen_height": h,
            "webgl_vendor": actual_vendor,
            "webgl_renderer": actual_renderer,
            "device_memory": dev_mem,
            "hardware_concurrency": hw_conc,
            "color_depth": color_depth,
            "pixel_ratio": pixel_ratio,
            "impersonate": imp,
            "lang": lang,
            "os": os_cfg["name"],
        })
    return pool


def _get_fp_pool():
    global _FP_POOL
    if _FP_POOL is None:
        _FP_POOL = _generate_fp_pool()
    return _FP_POOL


def _generate_fingerprint():
    pool = _get_fp_pool()
    with _FP_POOL_LOCK:
        idx = random.randint(0, len(pool) - 1)
    fp = pool[idx]
    is_mac = fp.get('os') == 'mac'
    ver_match = re.search(r'Chrome/(\d+)', fp['ua'])
    ver = ver_match.group(1) if ver_match else '124'
    not_a_brand = random.choice(_FP_NOT_A_BRAND)
    sec_ch_ua = f'"Chromium";v="{ver}", "Google Chrome";v="{ver}", {not_a_brand}'
    device = random.choice([d for d in _API_DEVICE_PROFILES if d['platform'] == ('macOS' if is_mac else 'Windows')] or _API_DEVICE_PROFILES)
    sw, sh = device['screen']
    dpr = device['dpr']
    vw = int(sw / dpr)
    vh = int(sh / dpr)
    headers = {
        'User-Agent': fp['ua'],
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': random.choice(_API_LANG_VARIANTS),
        'Accept-Encoding': 'gzip, deflate, br',
        'sec-ch-ua': sec_ch_ua,
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': fp['sec_ch_ua_platform'],
        'sec-ch-ua-full-version-list': f'"Chromium";v="{ver}.0.0.0", "Google Chrome";v="{ver}.0.0.0", {not_a_brand.replace(str(ver), f"{ver}.0.0.0")}',
        'sec-ch-ua-arch': '"x86"',
        'sec-ch-ua-bitness': '"64"',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform-version': '"15.0.0"',
        'sec-ch-viewport-width': str(vw),
        'sec-ch-viewport-height': str(vh),
        'sec-ch-dpr': str(dpr),
        'sec-ch-device-memory': str(device['mem']),
        'sec-ch-hardware-concurrency': str(device['cores']),
        'sec-ch-color-depth': str(device['color_depth']),
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'Connection': 'keep-alive',
        'Priority': random.choice(['u=3, i', 'u=4, i', 'u=2, i']),
    }
    fp_enhanced = dict(fp)
    fp_enhanced['sec_ch_ua'] = sec_ch_ua
    fp_enhanced['device_profile'] = device
    fp_enhanced['viewport_width'] = vw
    fp_enhanced['viewport_height'] = vh
    fp_enhanced['dpr'] = dpr
    return headers, fp_enhanced


def _generate_fingerprint_headers_only():
    headers, _ = _generate_fingerprint()
    return headers


def _api_check_risk_control(response_text, status_code):
    if status_code == 403:
        return True, "HTTP 403 Forbidden - 疑似风控拦截"
    if status_code == 429:
        return True, "HTTP 429 Too Many Requests - 请求频率限制"
    if status_code == 461:
        return True, "HTTP 461 - 小红书风控验证码"
    if status_code >= 500:
        return True, f"HTTP {status_code} - 服务端异常"
    try:
        data = json.loads(response_text)
        ec = data.get('error_code', -1)
        if ec == 461:
            return True, "API error_code=461 - 风控验证码"
        if ec == 300:
            return True, "API error_code=300 - 请求被拦截"
        msg = str(data.get('msg', '')).lower()
        for kw in _API_RISK_CONTROL_KEYWORDS:
            if kw.lower() in msg:
                return True, f"API msg含风控关键词: {kw}"
    except Exception:
        pass
    return False, ""


_PERSONALITIES = [
    (0.3, 0.8, "快速"),
    (0.5, 1.2, "普通"),
    (0.8, 1.8, "仔细"),
    (1.2, 2.5, "慢速"),
    (0.4, 1.0, "随意"),
]


def _warmup_session(session, fp_headers, shop_id=None, log_func=None):
    try:
        nav_headers = dict(fp_headers)
        nav_headers.update(_API_SEC_FETCH_MODES['navigate'])
        nav_headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
        nav_headers.pop('Origin', None)
        nav_headers['Referer'] = 'https://www.xiaohongshu.com/'

        try:
            session.get('https://www.xiaohongshu.com/', headers=nav_headers, timeout=15, allow_redirects=True)
            time.sleep(random.uniform(0.3, 0.6))
        except Exception:
            pass
        try:
            nav_headers['Referer'] = 'https://www.xiaohongshu.com/'
            session.get('https://www.xiaohongshu.com/explore', headers=nav_headers, timeout=15, allow_redirects=True)
            time.sleep(random.uniform(0.2, 0.5))
        except Exception:
            pass
        if shop_id:
            try:
                nav_headers['Referer'] = 'https://www.xiaohongshu.com/'
                session.get(f'https://www.xiaohongshu.com/vendor/{shop_id}', headers=nav_headers, timeout=15, allow_redirects=True)
                time.sleep(random.uniform(0.2, 0.5))
            except Exception:
                pass
        return True
    except Exception:
        return True


def _create_session(proxy_str=None, cookie_str=None, impersonate=None, fp_profile=None):
    if HAS_CURL_CFFI and impersonate:
        session = cffi_requests.Session(impersonate=impersonate)
        if proxy_str:
            if not proxy_str.startswith('http'):
                proxy_str = f'http://{proxy_str}'
            session.proxies = {'http': proxy_str, 'https': proxy_str}
        if cookie_str:
            for item in cookie_str.split(';'):
                item = item.strip()
                if '=' in item:
                    k, v = item.split('=', 1)
                    session.cookies.set(k.strip(), v.strip())
        return session

    session = requests.Session()
    session.cookies = requests.cookies.RequestsCookieJar()
    if fp_profile and fp_profile.get('ua'):
        session.headers.update({
            'User-Agent': fp_profile['ua'],
        })
    session.headers.update({
        'Connection': 'close',
        'Accept-Encoding': 'gzip, deflate, br',
    })
    adapter = HTTPAdapter(
        pool_connections=1,
        pool_maxsize=1,
        max_retries=0,
        pool_block=False,
    )
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    if proxy_str:
        if not proxy_str.startswith('http'):
            proxy_str = f'http://{proxy_str}'
        session.proxies = {'http': proxy_str, 'https': proxy_str}
    if cookie_str:
        for item in cookie_str.split(';'):
            item = item.strip()
            if '=' in item:
                k, v = item.split('=', 1)
                session.cookies.set(k.strip(), v.strip())
    return session


def _fetch_shop_goods_page(session, fingerprint_headers, shop_id, page=0, log_func=None):
    url = f"https://www.xiaohongshu.com/api/store/vs/{shop_id}/skus?page={page}"
    headers = dict(fingerprint_headers)
    headers.update(_API_SEC_FETCH_MODES['ajax'])
    headers['Referer'] = f'https://www.xiaohongshu.com/vendor/{shop_id}'

    for retry in range(2):
        try:
            r = session.get(url, headers=headers, timeout=(5, 8))
            is_risk, risk_msg = _api_check_risk_control(r.text, r.status_code)
            if is_risk:
                return [], False, True, risk_msg
            if r.status_code != 200:
                continue
            data = r.json()
            if data.get('error_code') == 0 or data.get('success') is True:
                raw_data = data.get('data', [])
                if raw_data is None:
                    return [], False, False, ''
                elif isinstance(raw_data, list):
                    items = raw_data
                    no_more = (len(items) < 20)
                elif isinstance(raw_data, dict):
                    no_more = raw_data.get('no_more_items', False)
                    items = raw_data.get('items', raw_data.get('skus', []))
                    if not isinstance(items, list):
                        items = []
                else:
                    return [], False, False, ''

                next_last_id = ''
                if items and isinstance(items, list):
                    next_last_id = str(items[-1].get('id', ''))

                goods_list = []
                for p in items:
                    if not isinstance(p, dict):
                        continue
                    item_id = str(p.get('item_id', '') or p.get('id', ''))
                    if len(item_id) < 10:
                        continue
                    price_info = p.get('price_info', {})
                    expected_price = price_info.get('expected_price', {})
                    sku_price = price_info.get('sku_price', {})
                    price_val = expected_price.get('price', 0)
                    if price_val is None:
                        price_val = 0
                    original_price = sku_price.get('price', 0)
                    if original_price is None:
                        original_price = 0
                    goods_list.append({
                        'goods_id': item_id,
                        'shop_id': str(p.get('seller_id', shop_id)),
                        'store_name': p.get('seller_name', p.get('store_name', '')),
                        'title': p.get('card_title', '') or p.get('desc', ''),
                        'deal_price': price_val,
                        'original_price': original_price,
                        'shelf_time': _convert_timestamp(p.get('on_shelf_time', 0)),
                        'stock_status': p.get('stock_status', 0),
                        'buyable': bool(p.get('buyable', False)),
                        'data_source': 'api_shop_list',
                    })
                has_more = not no_more and len(items) > 0
                return goods_list, has_more, False, next_last_id
            else:
                return [], False, False, ''
        except requests.exceptions.Timeout:
            continue
        except requests.exceptions.ProxyError:
            return [], False, False, ''
        except Exception as e:
            err_str = str(e).lower()
            if 'proxy' in err_str or 'connect' in err_str or 'recv failure' in err_str or 'connection was reset' in err_str or 'connection refused' in err_str:
                return [], False, False, ''
            if 'timeout' in err_str or 'timed out' in err_str:
                continue
            if 'curl' in err_str and ('28' in err_str or '7' in err_str or '6' in err_str):
                return [], False, False, ''
            continue
    return [], False, False, ''


def _fetch_shop_goods_page_raw(session, fingerprint_headers, shop_id, page=0, log_func=None):
    url = f"https://www.xiaohongshu.com/api/store/vs/{shop_id}/skus?page={page}"
    headers = dict(fingerprint_headers)
    headers.update(_API_SEC_FETCH_MODES['ajax'])
    headers['Referer'] = f'https://www.xiaohongshu.com/vendor/{shop_id}'

    for retry in range(2):
        try:
            r = session.get(url, headers=headers, timeout=(5, 8))
            is_risk, risk_msg = _api_check_risk_control(r.text, r.status_code)
            if is_risk:
                return None, False, True
            if r.status_code != 200:
                continue
            data = r.json()
            if data.get('error_code') == 0 or data.get('success') is True:
                raw_data = data.get('data', [])
                if raw_data is None:
                    return [], False, False
                elif isinstance(raw_data, list):
                    items = raw_data
                    no_more = (len(items) < 20)
                elif isinstance(raw_data, dict):
                    no_more = raw_data.get('no_more_items', False)
                    items = raw_data.get('items', raw_data.get('skus', []))
                    if not isinstance(items, list):
                        items = []
                else:
                    return [], False, False
                has_more = not no_more and len(items) > 0
                return items, has_more, False
            else:
                return [], False, False
        except requests.exceptions.Timeout:
            continue
        except requests.exceptions.ProxyError:
            return None, False, False
        except Exception as e:
            err_str = str(e).lower()
            if 'proxy' in err_str or 'connect' in err_str or 'recv failure' in err_str or 'connection was reset' in err_str or 'connection refused' in err_str:
                return None, False, False
            if 'timeout' in err_str or 'timed out' in err_str:
                continue
            continue
    return None, False, False


def _fetch_store_name_from_page(session, fingerprint_headers, shop_id, log_func=None):
    try:
        page_url = f'https://www.xiaohongshu.com/vendor/{shop_id}'
        headers = dict(fingerprint_headers)
        headers['Referer'] = 'https://www.xiaohongshu.com/'
        r = session.get(page_url, headers=headers, timeout=(5, 8), allow_redirects=True)
        if r.status_code != 200:
            return ''
        html = r.text
        m = re.search(r'window\.__INITIAL_SSR_STATE__\s*=\s*({.*?})\s*</script>', html, re.DOTALL)
        if not m:
            return ''
        state = json.loads(m.group(1))
        store_index = state.get('StoreIndex', {})
        brand = store_index.get('brand', {})
        store_name = brand.get('name', '')
        if store_name:
            return store_name.strip()
        seller_info = store_index.get('sellerInfo', {})
        if isinstance(seller_info, dict):
            sn = seller_info.get('shopname', '') or seller_info.get('name', '')
            if sn:
                return sn.strip()
        popup = store_index.get('popupShopInfo', {})
        if isinstance(popup, dict):
            sn = popup.get('shopName', '')
            if sn:
                return sn.replace('的店', '').strip()
        return ''
    except Exception:
        return ''


def _fetch_shop_fans_and_sales(session, fingerprint_headers, shop_id, log_func=None):
    """从 /shop/ 页面获取店铺粉丝数和总销量"""
    try:
        page_url = f'https://www.xiaohongshu.com/shop/{shop_id}'
        headers = dict(fingerprint_headers)
        headers['Referer'] = 'https://www.xiaohongshu.com/'
        r = session.get(page_url, headers=headers, timeout=(5, 8), allow_redirects=True)
        if r.status_code != 200:
            return None
        html = r.text
        m = re.search(r'window\.__INITIAL_SSR_STATE__\s*=\s*({.*?})\s*</script>', html, re.DOTALL)
        if not m:
            return None
        state = json.loads(m.group(1))
        store_index = state.get('StoreIndex', state.get('ShopIndex', {}))

        result = {'store_name': '', 'fans_count': 0, 'shop_sales': 0}

        # 店铺名称
        brand = store_index.get('brand', {})
        store_name = brand.get('name', '')
        if not store_name:
            seller_info = store_index.get('sellerInfo', {})
            if isinstance(seller_info, dict):
                store_name = seller_info.get('shopname', '') or seller_info.get('name', '')
        if not store_name:
            popup = store_index.get('popupShopInfo', {})
            if isinstance(popup, dict):
                sn = popup.get('shopName', '')
                if sn:
                    store_name = sn.replace('的店', '')
        result['store_name'] = store_name.strip()

        # 粉丝数 - 从sellerInfo中获取
        seller_info = store_index.get('sellerInfo', {})
        if isinstance(seller_info, dict):
            fans_text = seller_info.get('fansAmount', '') or seller_info.get('fans', '')
            if fans_text:
                result['fans_count'] = _parse_chinese_number(str(fans_text))
            sales_text = seller_info.get('salesVolume', '') or seller_info.get('sales', '')
            if sales_text:
                result['shop_sales'] = _parse_chinese_number(str(sales_text))

        # 如果sellerInfo没有，尝试从brand获取
        if result['fans_count'] == 0:
            fans_text = brand.get('fansAmount', '') or brand.get('fans', '')
            if fans_text:
                result['fans_count'] = _parse_chinese_number(str(fans_text))
        if result['shop_sales'] == 0:
            sales_text = brand.get('salesVolume', '') or brand.get('sales', '')
            if sales_text:
                result['shop_sales'] = _parse_chinese_number(str(sales_text))

        # 尝试从popupShopInfo获取
        if result['fans_count'] == 0 or result['shop_sales'] == 0:
            popup = store_index.get('popupShopInfo', {})
            if isinstance(popup, dict):
                if result['fans_count'] == 0:
                    fans_text = popup.get('fansAmount', '') or popup.get('fansCount', '')
                    if fans_text:
                        result['fans_count'] = _parse_chinese_number(str(fans_text))
                if result['shop_sales'] == 0:
                    sales_text = popup.get('salesVolume', '') or popup.get('salesCount', '')
                    if sales_text:
                        result['shop_sales'] = _parse_chinese_number(str(sales_text))

        # 如果SSR中没有数据，尝试从HTML中正则提取
        if result['fans_count'] == 0:
            fans_match = re.search(r'class="[^"]*fans[^"]*"[^>]*>([^<]*[\d.]+[^<]*)<', html, re.IGNORECASE)
            if not fans_match:
                fans_match = re.search(r'(\d[\d.]*(?:万|w)?)\s*粉丝', html, re.IGNORECASE)
            if fans_match:
                result['fans_count'] = _parse_chinese_number(fans_match.group(1))

        if result['shop_sales'] == 0:
            sales_match = re.search(r'class="[^"]*sales[^"]*"[^>]*>([^<]*[\d.]+[^<]*)<', html, re.IGNORECASE)
            if not sales_match:
                sales_match = re.search(r'(\d[\d.]*(?:万|w)?)\s*(?:总销量|全部商品|已售)', html, re.IGNORECASE)
            if sales_match:
                result['shop_sales'] = _parse_chinese_number(sales_match.group(1))

        if result['fans_count'] > 0 or result['shop_sales'] > 0 or result['store_name']:
            return result
        return None
    except Exception:
        return None


def _save_to_db(db_path, shop_id, goods_list, log_func=None, db_write_lock=None):
    shelf_time_updated = 0
    new_goods_count = 0
    lock = db_write_lock or threading.Lock()
    with lock:
        for attempt in range(3):
            try:
                conn = sqlite3.connect(db_path, timeout=30)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")
                conn.execute("PRAGMA synchronous=NORMAL")
                c = conn.cursor()
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                for g in goods_list:
                    goods_id = g.get('goods_id', '')
                    if not goods_id:
                        continue

                    title = g.get('title', '')
                    iv = _classify_virtual(title)

                    if iv == 0:
                        continue

                    g_shelf = g.get('shelf_time', '')
                    if g_shelf:
                        g_shelf = g_shelf.strip()

                    c.execute('''SELECT goods_id, shelf_time FROM goods WHERE goods_id = ?''', (goods_id,))
                    existing = c.fetchone()

                    if existing:
                        old_shelf = existing[1] or ''
                        old_shelf = old_shelf.strip()
                        update_fields = []
                        update_values = []
                        if g_shelf and not old_shelf:
                            update_fields.append("shelf_time = ?")
                            update_values.append(g_shelf)
                            shelf_time_updated += 1
                        if g.get('shop_id'):
                            update_fields.append("store_id = ?")
                            update_values.append(g['shop_id'])
                        if g.get('store_name'):
                            update_fields.append("store_name = COALESCE(NULLIF(store_name,''), ?)")
                            update_values.append(g['store_name'])
                        if title:
                            update_fields.append("title = ?")
                            update_values.append(title)
                            update_fields.append("is_virtual = ?")
                            update_values.append(iv)
                        if g.get('deal_price') and g['deal_price'] > 0:
                            update_fields.append("deal_price = ?")
                            update_values.append(g['deal_price'])

                        if update_fields:
                            update_fields.append("last_seen = ?")
                            update_values.append(now)
                            update_fields.append("scan_count = scan_count + 1")
                            c.execute(f"UPDATE goods SET {', '.join(update_fields)} WHERE goods_id = ?", update_values + [goods_id])
                    else:
                        c.execute('''INSERT OR IGNORE INTO goods
                            (goods_id, title, deal_price, store_id, store_name, keyword, shelf_time, first_seen, last_seen, scan_count, data_source, is_virtual)
                            VALUES (?, ?, ?, ?, ?, 'web_store', ?, ?, ?, 1, ?, ?)''',
                            (goods_id, title, g.get('deal_price', 0),
                             g.get('shop_id', ''), g.get('store_name', ''),
                             g_shelf or None,
                             now, now, g.get('data_source', 'api_shop_list'), iv))
                        if c.rowcount > 0:
                            new_goods_count += 1
                            if g_shelf:
                                shelf_time_updated += 1

                c.execute('''INSERT OR REPLACE INTO store_scores (store_id, last_scan, scan_count)
                    VALUES (?, ?, COALESCE((SELECT scan_count FROM store_scores WHERE store_id = ?), 0) + 1)''',
                    (shop_id, now, shop_id))

                store_names_seen = set()
                for g in goods_list:
                    sn = g.get('store_name', '')
                    if sn:
                        store_names_seen.add(sn)
                ss_store_name = next(iter(store_names_seen), '')
                if ss_store_name:
                    c.execute(
                        'UPDATE store_scores SET store_name=? WHERE store_id=? AND (store_name IS NULL OR store_name="")',
                        (ss_store_name, shop_id)
                    )

                c.execute("SELECT name FROM pragma_table_info('keyword_pool')")
                kp_cols = {row[0] for row in c.fetchall()}
                has_source = 'source' in kp_cols
                has_related_store_id = 'related_store_id' in kp_cols

                kw_injected = 0
                for sn in store_names_seen:
                    if not sn or len(sn) < 2 or len(sn) > 50:
                        continue
                    try:
                        if has_source and has_related_store_id:
                            c.execute('''
                                INSERT OR IGNORE INTO keyword_pool (keyword, category, is_active, priority, source, related_store_id)
                                VALUES (?, 'store_name', 1, 10, 'web_discover', ?)
                            ''', (sn, shop_id))
                        elif has_source:
                            c.execute('''
                                INSERT OR IGNORE INTO keyword_pool (keyword, category, is_active, priority, source)
                                VALUES (?, 'store_name', 1, 10, 'web_discover')
                            ''', (sn,))
                        else:
                            c.execute('''
                                INSERT OR IGNORE INTO keyword_pool (keyword, category, is_active, priority)
                                VALUES (?, 'store_name', 1, 10)
                            ''', (sn,))
                        if c.rowcount > 0:
                            kw_injected += 1
                    except Exception:
                        pass
                if kw_injected > 0:
                    _log(f"[Web采集] 注入{kw_injected}个新关键词到APP搜索队列: {ss_store_name}", log_func)

                conn.commit()
                conn.close()
                return shelf_time_updated, new_goods_count
            except sqlite3.OperationalError as e:
                try:
                    conn.close()
                except Exception:
                    pass
                if 'locked' in str(e).lower() and attempt < 2:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                _log(f"写入数据库失败(锁定): {e}", log_func)
                return shelf_time_updated, new_goods_count
            except Exception as e:
                try:
                    conn.close()
                except Exception:
                    pass
                _log(f"写入数据库失败: {e}", log_func)
                return shelf_time_updated, new_goods_count
    return shelf_time_updated, new_goods_count


def _save_abnormal_shop_db(db_path, shop_id, reason="optimizing", log_func=None, db_write_lock=None):
    lock = db_write_lock or threading.Lock()
    with lock:
        try:
            conn = sqlite3.connect(db_path, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            c = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                c.execute("SELECT name FROM pragma_table_info('store_scores')")
                columns = {row[0] for row in c.fetchall()}
                if 'shop_status' not in columns:
                    c.execute("ALTER TABLE store_scores ADD COLUMN shop_status TEXT DEFAULT ''")
                if 'abnormal_reason' not in columns:
                    c.execute("ALTER TABLE store_scores ADD COLUMN abnormal_reason TEXT DEFAULT ''")
                if 'abnormal_time' not in columns:
                    c.execute("ALTER TABLE store_scores ADD COLUMN abnormal_time TEXT DEFAULT ''")
            except Exception:
                pass
            try:
                c.execute("SELECT name FROM pragma_table_info('goods')")
                g_columns = {row[0] for row in c.fetchall()}
                if 'goods_status' not in g_columns:
                    c.execute("ALTER TABLE goods ADD COLUMN goods_status TEXT DEFAULT ''")
            except Exception:
                pass
            c.execute('''INSERT OR REPLACE INTO store_scores (store_id, last_scan, scan_count, shop_status, abnormal_reason, abnormal_time)
                VALUES (?, ?, COALESCE((SELECT scan_count FROM store_scores WHERE store_id = ?), 0) + 1, ?, ?, ?)''',
                (shop_id, now, shop_id, 'abnormal', reason, now))
            c.execute('''UPDATE goods SET goods_status = 'abnormal' WHERE store_id = ? AND (goods_status IS NULL OR goods_status = '')''', (shop_id,))
            affected = c.rowcount
            conn.commit()
            conn.close()
            if affected > 0:
                _log(f"异常店铺 {shop_id}: 已标记 {affected} 个关联商品为异常", log_func)
        except Exception as e:
            try:
                conn.close()
            except Exception:
                pass
            _log(f"保存异常店铺状态失败: {e}", log_func)


# ============================================================
# APIShopCollector - 纯requests API采集 (增强版 - 整合xhs_pro方案)
# ============================================================
class APIShopCollector:
    RISK_COOLDOWNS = [1800, 3600, 5400, 7200]
    SESSION_MAX_REQUESTS = 50
    SESSION_MAX_AGE = 600

    def __init__(self, config=None, log_func=None):
        self.config = config or {}
        self.log_func = log_func
        self._running = False
        self._stop_event = threading.Event()
        self._db_write_lock = threading.Lock()
        self._stats = {
            "shops_success": 0,
            "shops_fail": 0,
            "goods_found": 0,
            "shelf_time_updated": 0,
            "new_goods_found": 0,
        }
        self._risk_level = 0
        self._risk_until = 0
        self._thread_sessions = {}
        self._thread_fingerprints = {}
        self._thread_session_meta = {}
        self._session_lock = threading.Lock()

    def stop(self):
        self._stop_event.set()
        self._running = False

    def is_running(self):
        return self._running

    def get_stats(self):
        return dict(self._stats)

    def _get_thread_session(self, worker_id):
        with self._session_lock:
            if worker_id in self._thread_sessions:
                meta = self._thread_session_meta.get(worker_id, {})
                req_count = meta.get('request_count', 0)
                created_at = meta.get('created_at', 0)
                if req_count >= self.SESSION_MAX_REQUESTS:
                    _log(f"[API] Worker#{worker_id}: Session已达{req_count}次请求上限, 轮换", self.log_func)
                    self._rotate_thread_session(worker_id)
                    return self._thread_sessions[worker_id], self._thread_fingerprints[worker_id]
                if time.time() - created_at > self.SESSION_MAX_AGE:
                    _log(f"[API] Worker#{worker_id}: Session已存活{int(time.time()-created_at)}秒, 轮换", self.log_func)
                    self._rotate_thread_session(worker_id)
                    return self._thread_sessions[worker_id], self._thread_fingerprints[worker_id]
                return self._thread_sessions[worker_id], self._thread_fingerprints[worker_id]

        fp_headers, fp_profile = _generate_fingerprint()
        impersonate = fp_profile.get('impersonate') if HAS_CURL_CFFI else None
        session = _create_session(impersonate=impersonate, fp_profile=fp_profile)
        _warmup_session(session, fp_headers, log_func=self.log_func)

        with self._session_lock:
            self._thread_sessions[worker_id] = session
            self._thread_fingerprints[worker_id] = fp_headers
            self._thread_session_meta[worker_id] = {
                'request_count': 0,
                'created_at': time.time(),
                'fp_profile': fp_profile,
            }
        _log(f"[API] Worker#{worker_id}: 新Session创建 GPU={fp_profile.get('webgl_renderer','?')[:30]}... UA=Chrome/{fp_profile.get('impersonate','?')}", self.log_func)
        return session, fp_headers

    def _rotate_thread_session(self, worker_id):
        with self._session_lock:
            old_session = self._thread_sessions.pop(worker_id, None)
            self._thread_fingerprints.pop(worker_id, None)
            self._thread_session_meta.pop(worker_id, None)
        if old_session:
            try:
                old_session.cookies.clear()
                old_session.close()
            except Exception:
                pass

        fp_headers, fp_profile = _generate_fingerprint()
        impersonate = fp_profile.get('impersonate') if HAS_CURL_CFFI else None
        session = _create_session(impersonate=impersonate, fp_profile=fp_profile)
        _warmup_session(session, fp_headers, log_func=self.log_func)

        with self._session_lock:
            self._thread_sessions[worker_id] = session
            self._thread_fingerprints[worker_id] = fp_headers
            self._thread_session_meta[worker_id] = {
                'request_count': 0,
                'created_at': time.time(),
                'fp_profile': fp_profile,
            }
        _log(f"[API] Worker#{worker_id}: Session轮换完成 GPU={fp_profile.get('webgl_renderer','?')[:30]}...", self.log_func)

    def _increment_request_count(self, worker_id):
        with self._session_lock:
            if worker_id in self._thread_session_meta:
                self._thread_session_meta[worker_id]['request_count'] += 1

    def _cleanup_all_sessions(self):
        with self._session_lock:
            for wid, session in self._thread_sessions.items():
                try:
                    session.cookies.clear()
                    session.close()
                except Exception:
                    pass
            self._thread_sessions.clear()
            self._thread_fingerprints.clear()
            self._thread_session_meta.clear()

    def _wait_risk_cooldown(self):
        if self._risk_level >= len(self.RISK_COOLDOWNS):
            self._risk_level = 0
        cooldown_sec = self.RISK_COOLDOWNS[self._risk_level]
        self._risk_level += 1
        self._risk_until = time.time() + cooldown_sec
        mins = cooldown_sec // 60
        _log(f"[API] 风控冷却 {mins} 分钟 (等级{self._risk_level})", self.log_func)
        last_test_time = 0
        while time.time() < self._risk_until:
            if self._stop_event.is_set():
                return False
            remaining = int(self._risk_until - time.time())
            now_ts = time.time()
            if remaining > 0 and now_ts - last_test_time >= 60:
                last_test_time = now_ts
                _log(f"[API] 冷却剩余 {remaining // 60} 分钟, 测试连接...", self.log_func)
                try:
                    test_headers, _ = _generate_fingerprint()
                    test_headers.update(_API_SEC_FETCH_MODES['navigate'])
                    test_headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                    r = requests.get('https://www.xiaohongshu.com/', headers=test_headers, timeout=10)
                    is_risk, _ = _api_check_risk_control(r.text, r.status_code)
                    if not is_risk and r.status_code == 200:
                        _log("[API] 连接测试通过, 提前恢复采集", self.log_func)
                        self._risk_level = max(0, self._risk_level - 1)
                        return True
                except Exception:
                    pass
            time.sleep(1)
        return True

    def _record_risk_free_max(self, engine_name, shops_count, db_path):
        if not db_path:
            return
        try:
            conn = sqlite3.connect(db_path, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            c = conn.cursor()
            c.execute("""CREATE TABLE IF NOT EXISTS risk_free_max (
                engine TEXT PRIMARY KEY,
                max_shops INTEGER DEFAULT 0,
                updated_at TEXT
            )""")
            c.execute("SELECT max_shops FROM risk_free_max WHERE engine=?", (engine_name,))
            row = c.fetchone()
            if row is None or shops_count > row[0]:
                c.execute("""INSERT OR REPLACE INTO risk_free_max (engine, max_shops, updated_at)
                    VALUES (?, ?, datetime('now'))""", (engine_name, shops_count))
                conn.commit()
            conn.close()
        except Exception as e:
            _log(f"[API] 记录风控安全阈值失败: {e}", self.log_func)
            try:
                conn.close()
            except Exception:
                pass

    def _collect_one_shop(self, session, fingerprint_headers, shop_id, worker_id):
        all_goods = []
        seen_ids = set()
        is_risk = False
        risk_msg = ''

        store_name = _fetch_store_name_from_page(session, fingerprint_headers, shop_id, log_func=self.log_func)
        self._increment_request_count(worker_id)

        try:
            for page_num in range(100):
                if self._stop_event.is_set():
                    break

                goods_list, has_more, risk, msg = _fetch_shop_goods_page(
                    session, fingerprint_headers, shop_id, page_num, log_func=self.log_func)
                self._increment_request_count(worker_id)

                if risk:
                    is_risk = True
                    risk_msg = msg
                    break

                new_in_page = 0
                for g in goods_list:
                    gid = g.get('goods_id', '')
                    if gid and gid not in seen_ids:
                        seen_ids.add(gid)
                        all_goods.append(g)
                        new_in_page += 1

                if not has_more or new_in_page == 0:
                    break

                time.sleep(random.uniform(0.3, 0.8))

        except Exception as e:
            _log(f"[API] 采集单店铺异常: {e}", self.log_func)

        if store_name:
            for g in all_goods:
                if not g.get('store_name'):
                    g['store_name'] = store_name

        return all_goods, is_risk, risk_msg

    def collect_shop_list(self, shop_ids, db_path, virtual_filter_fn=None, skip_store_fn=None):
        self._running = True
        self._stop_event.clear()
        self._stats = {"shops_success": 0, "shops_fail": 0, "goods_found": 0, "shelf_time_updated": 0, "new_goods_found": 0}

        _log(f"[API] 串行模式 开始采集 {len(shop_ids)} 个商铺", self.log_func)

        all_goods = []
        stats = {"shops_success": 0, "shops_fail": 0, "goods_found": 0, "shelf_time_updated": 0, "new_goods_found": 0}
        risk_triggered = False

        session, fp_headers = self._get_thread_session(0)
        time.sleep(random.uniform(1.0, 2.5))

        consecutive_fails = 0
        risk_retries = 0

        try:
            for current_idx, shop_id in enumerate(shop_ids):
                if self._stop_event.is_set() or risk_triggered:
                    break

                if skip_store_fn and skip_store_fn(shop_id):
                    continue

                shop_page_goods, is_risk, risk_msg = self._collect_one_shop(
                    session, fp_headers, shop_id, 0)

                if is_risk:
                    risk_retries += 1
                    _log(f"[API] 风控! 商铺={shop_id} 原因={risk_msg}", self.log_func)

                    self._rotate_thread_session(0)
                    session, fp_headers = self._get_thread_session(0)

                    if risk_retries <= 2:
                        _log(f"[API] 风控后重建Session, 重试商铺={shop_id} (第{risk_retries}次)", self.log_func)
                        time.sleep(random.uniform(5.0, 15.0))
                        continue
                    else:
                        risk_triggered = True
                        _log(f"[API] 连续{risk_retries}次风控, 停止采集", self.log_func)
                        break

                risk_retries = 0

                if not shop_page_goods:
                    consecutive_fails += 1
                    stats["shops_fail"] += 1
                    if consecutive_fails >= 3:
                        self._rotate_thread_session(0)
                        session, fp_headers = self._get_thread_session(0)
                        _log(f"[API] 连续{consecutive_fails}次空结果, 轮换Session+指纹", self.log_func)
                        consecutive_fails = 0
                    continue

                consecutive_fails = 0
                if virtual_filter_fn:
                    filtered = [g for g in shop_page_goods if virtual_filter_fn(g.get('title', ''))]
                else:
                    filtered = [g for g in shop_page_goods if _classify_virtual(g.get('title', '')) != 0]
                all_goods.extend(filtered)
                stats["goods_found"] += len(filtered)
                stats["shops_success"] += 1
                if db_path:
                    db_result = _save_to_db(db_path, shop_id, filtered, self.log_func, self._db_write_lock)
                    if db_result:
                        st_updated, new_goods = db_result
                        stats["shelf_time_updated"] += st_updated
                        stats["new_goods_found"] += new_goods

                time.sleep(random.uniform(0.5, 1.5))

                done = stats["shops_success"] + stats["shops_fail"]
                if done > 0 and done % 10 == 0:
                    s = stats
                    _log(f"[API] {done}/{len(shop_ids)} | 成功={s['shops_success']} 失败={s['shops_fail']} 商品={s['goods_found']}", self.log_func)

        finally:
            self._cleanup_all_sessions()

        if risk_triggered:
            _log(f"[API] 风控触发! 本轮成功采集 {stats['shops_success']} 个商铺", self.log_func)
            self._record_risk_free_max("api", stats["shops_success"], db_path)
            self._wait_risk_cooldown()

        _log(f"[API] 串行模式完成: {stats['shops_success']}个商铺, {len(all_goods)}个商品, shelf_time更新={stats['shelf_time_updated']}, 新商品={stats['new_goods_found']}", self.log_func)

        self._stats = dict(stats)
        self._running = False
        return all_goods


# ============================================================
# ApiV2ShopCollector - 极简API采集（零预热/无Cookie/最小指纹）
# ============================================================
_APIV2_IMPERSONATE_POOL = [
    'chrome124', 'chrome123', 'chrome120',
    'chrome131', 'chrome136',
] if HAS_CURL_CFFI else []

_APIV2_MINIMAL_HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
}


def _apiv2_fetch_shop_page(proxy_str, shop_id, page=0, use_tls=True, log_func=None):
    url = f"https://www.xiaohongshu.com/api/store/vs/{shop_id}/skus?page={page}"
    headers = dict(_APIV2_MINIMAL_HEADERS)
    headers['Referer'] = f'https://www.xiaohongshu.com/vendor/{shop_id}'

    if proxy_str and not proxy_str.startswith('http'):
        proxy_str = f'http://{proxy_str}'
    proxies = {'http': proxy_str, 'https': proxy_str} if proxy_str else None

    for retry in range(2):
        try:
            if use_tls and HAS_CURL_CFFI:
                imp = random.choice(_APIV2_IMPERSONATE_POOL) if _APIV2_IMPERSONATE_POOL else None
                sess = cffi_requests.Session(impersonate=imp)
                if proxies:
                    sess.proxies = proxies
                r = sess.get(url, headers=headers, timeout=(5, 8))
                try:
                    sess.close()
                except Exception:
                    pass
            else:
                r = requests.get(url, headers=headers, proxies=proxies, timeout=(5, 8))

            if r.status_code in (403, 429, 461):
                return [], False, True, False
            if r.status_code != 200:
                continue
            data = r.json()
            if data.get('error_code') == 461:
                return [], False, True, False
            if data.get('error_code') == 0 or data.get('success') is True:
                raw_data = data.get('data', [])
                if raw_data is None:
                    return [], False, False, False
                elif isinstance(raw_data, list):
                    items = raw_data
                    no_more = (len(items) < 20)
                elif isinstance(raw_data, dict):
                    no_more = raw_data.get('no_more_items', False)
                    items = raw_data.get('items', raw_data.get('skus', []))
                    if not isinstance(items, list):
                        items = []
                else:
                    return [], False, False, False

                goods_list = []
                for p in items:
                    if not isinstance(p, dict):
                        continue
                    item_id = str(p.get('item_id', '') or p.get('id', ''))
                    if len(item_id) < 10:
                        continue
                    price_info = p.get('price_info', {})
                    expected_price = price_info.get('expected_price', {})
                    sku_price = price_info.get('sku_price', {})
                    price_val = expected_price.get('price', 0)
                    if price_val is None:
                        price_val = 0
                    original_price = sku_price.get('price', 0)
                    if original_price is None:
                        original_price = 0
                    goods_list.append({
                        'goods_id': item_id,
                        'shop_id': str(p.get('seller_id', shop_id)),
                        'store_name': p.get('seller_name', p.get('store_name', '')),
                        'title': p.get('card_title', '') or p.get('desc', ''),
                        'deal_price': price_val,
                        'original_price': original_price,
                        'shelf_time': _convert_timestamp(p.get('on_shelf_time', 0)),
                        'stock_status': p.get('stock_status', 0),
                        'buyable': bool(p.get('buyable', False)),
                        'data_source': 'apiv2_shop_list',
                    })
                has_more = not no_more and len(items) > 0
                return goods_list, has_more, False, False
            else:
                return [], False, False, False
        except requests.exceptions.ProxyError:
            return [], False, False, True
        except requests.exceptions.Timeout:
            return [], False, False, True
        except requests.exceptions.ConnectionError:
            return [], False, False, True
        except Exception:
            continue
    return [], False, False, False


class ApiV2ShopCollector:
    RISK_COOLDOWNS = [1800, 3600, 5400, 7200]

    def __init__(self, config=None, log_func=None):
        self.config = config or {}
        self.log_func = log_func
        self._running = False
        self._stop_event = threading.Event()
        self._db_write_lock = threading.Lock()
        self._stats = {
            "shops_success": 0,
            "shops_fail": 0,
            "goods_found": 0,
            "shelf_time_updated": 0,
            "new_goods_found": 0,
            "delisted_marked": 0,
        }
        self._risk_level = 0
        self._risk_until = 0
        self._use_tls = False

    def stop(self):
        self._stop_event.set()
        self._running = False

    def is_running(self):
        return self._running

    def get_stats(self):
        return dict(self._stats)

    def _wait_risk_cooldown(self):
        if self._risk_level >= len(self.RISK_COOLDOWNS):
            self._risk_level = 0
        cooldown_sec = self.RISK_COOLDOWNS[self._risk_level]
        self._risk_level += 1
        self._risk_until = time.time() + cooldown_sec
        mins = cooldown_sec // 60
        _log(f"[API-2] 风控冷却 {mins} 分钟 (等级{self._risk_level})", self.log_func)

        last_test_time = 0
        while time.time() < self._risk_until:
            if self._stop_event.is_set():
                return False
            remaining = int(self._risk_until - time.time())
            now_ts = time.time()
            if remaining > 0 and now_ts - last_test_time >= 60:
                last_test_time = now_ts
                _log(f"[API-2] 冷却剩余 {remaining // 60} 分钟, 测试连接...", self.log_func)
                test_goods, _, test_risk, _ = _apiv2_fetch_shop_page(
                    None, "586e100ba8e2910ebe6c9a73", page=0,
                    use_tls=False, log_func=None)
                if not test_risk and test_goods:
                    _log("[API-2] 连接测试通过, 提前恢复采集", self.log_func)
                    self._risk_level = max(0, self._risk_level - 1)
                    return True
            time.sleep(1)
        return True

    def _collect_one_shop(self, shop_id, use_tls=False):
        shop_goods = []
        is_risk = False
        try:
            for page_num in range(100):
                if self._stop_event.is_set():
                    break
                page_goods, has_more, risk, proxy_err = _apiv2_fetch_shop_page(
                    None, shop_id, page_num,
                    use_tls=use_tls, log_func=self.log_func)
                if risk:
                    is_risk = True
                    break
                shop_goods.extend(page_goods)
                if not has_more or not page_goods:
                    break
                time.sleep(random.uniform(0.3, 0.8))
        except Exception:
            pass
        return shop_goods, is_risk

    def collect_shop_list(self, shop_ids, db_path, virtual_filter_fn=None, skip_store_fn=None):
        self._running = True
        self._stop_event.clear()
        self._stats = {"shops_success": 0, "shops_fail": 0, "goods_found": 0, "shelf_time_updated": 0, "new_goods_found": 0, "delisted_marked": 0}

        _log(f"[API-2] 开始并发采集 {len(shop_ids)} 个商铺 (并发=10, 直连)", self.log_func)

        all_goods = []
        stats = {"shops_success": 0, "shops_fail": 0, "goods_found": 0, "shelf_time_updated": 0, "new_goods_found": 0, "delisted_marked": 0}
        results_lock = threading.Lock()
        idx = 0
        idx_lock = threading.Lock()
        risk_event = threading.Event()
        use_tls = self._use_tls if hasattr(self, '_use_tls') else False

        def shop_worker(worker_id):
            nonlocal idx
            local_goods = []

            # 错开Worker启动，避免同时请求触发风控
            time.sleep(worker_id * random.uniform(1.5, 3.0))

            while not self._stop_event.is_set() and not risk_event.is_set():
                with idx_lock:
                    if idx >= len(shop_ids):
                        break
                    shop_id = shop_ids[idx]
                    idx += 1

                if skip_store_fn and skip_store_fn(shop_id):
                    continue

                shop_goods, is_risk = self._collect_one_shop(shop_id, use_tls=use_tls)

                if is_risk:
                    risk_event.set()
                    _log(f"[API-2] Worker#{worker_id}: 风控! 商铺={shop_id}", self.log_func)
                    with idx_lock:
                        idx -= 1
                    return local_goods

                if not shop_goods:
                    with results_lock:
                        stats["shops_fail"] += 1
                    continue

                if virtual_filter_fn:
                    filtered = [g for g in shop_goods if virtual_filter_fn(g.get('title', ''))]
                else:
                    filtered = [g for g in shop_goods if _classify_virtual(g.get('title', '')) != 0]
                local_goods.extend(filtered)
                with results_lock:
                    stats["goods_found"] += len(filtered)
                    stats["shops_success"] += 1
                if db_path:
                    db_result = _save_to_db(db_path, shop_id, filtered, self.log_func, self._db_write_lock)
                    if db_result:
                        st_updated, new_goods = db_result
                        with results_lock:
                            stats["shelf_time_updated"] += st_updated
                            stats["new_goods_found"] += new_goods

                with results_lock:
                    done = stats["shops_success"] + stats["shops_fail"]
                    if done > 0 and done % 10 == 0:
                        _log(f"[API-2] {done}/{len(shop_ids)} | 成功={stats['shops_success']} 失败={stats['shops_fail']} 商品={stats['goods_found']}", self.log_func)

                time.sleep(random.uniform(0.3, 0.8))

            return local_goods

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(shop_worker, i) for i in range(3)]
            for f in as_completed(futures):
                try:
                    with results_lock:
                        all_goods.extend(f.result())
                except Exception:
                    pass

        if risk_event.is_set():
            _log("[API-2] 检测到风控, 进入冷却", self.log_func)
            self._wait_risk_cooldown()

        _log(f"[API-2] 完成: {stats['shops_success']}个商铺, {len(all_goods)}个商品, shelf_time更新={stats['shelf_time_updated']}, 新商品={stats['new_goods_found']}", self.log_func)

        self._stats = dict(stats)
        self._running = False
        return all_goods

    def fill_missing_store_names(self, shop_ids, db_path=None):
        _log(f"[补店铺名] API-2模式开始补充 {len(shop_ids)} 个商铺名称 (并发=10)", self.log_func)

        self._running = True
        self._stop_event.clear()

        filled_count = 0
        filled_lock = threading.Lock()
        idx = 0
        idx_lock = threading.Lock()
        risk_event = threading.Event()
        use_tls = self._use_tls if hasattr(self, '_use_tls') else False

        def name_worker(worker_id):
            nonlocal idx, filled_count
            while not self._stop_event.is_set() and not risk_event.is_set():
                with idx_lock:
                    if idx >= len(shop_ids):
                        break
                    i = idx
                    shop_id = shop_ids[idx]
                    idx += 1

                store_name = ""
                try:
                    page_goods, has_more, risk, proxy_err = _apiv2_fetch_shop_page(
                        None, shop_id, page=0,
                        use_tls=use_tls, log_func=self.log_func)
                    if risk:
                        risk_event.set()
                        return
                    if page_goods:
                        store_name = page_goods[0].get('store_name', '')
                except Exception:
                    pass

                if store_name and db_path:
                    try:
                        conn = sqlite3.connect(db_path, timeout=30)
                        conn.execute("PRAGMA journal_mode=WAL")
                        conn.execute("PRAGMA busy_timeout=30000")
                        c = conn.cursor()
                        c.execute(
                            'UPDATE store_scores SET store_name=? WHERE store_id=? AND (store_name IS NULL OR store_name="")',
                            (store_name, shop_id)
                        )
                        if c.rowcount > 0:
                            c.execute(
                                'UPDATE goods SET store_name=? WHERE store_id=? AND (store_name IS NULL OR store_name="")',
                                (store_name, shop_id)
                            )
                            with filled_lock:
                                filled_count += 1
                        c.execute("SELECT name FROM pragma_table_info('keyword_pool')")
                        kp_cols = {row[0] for row in c.fetchall()}
                        if 'source' in kp_cols:
                            c.execute('''
                                INSERT OR IGNORE INTO keyword_pool (keyword, category, is_active, priority, source)
                                VALUES (?, 'store_name', 1, 10, 'web_fill_name')
                            ''', (store_name,))
                        else:
                            c.execute('''
                                INSERT OR IGNORE INTO keyword_pool (keyword, category, is_active, priority)
                                VALUES (?, 'store_name', 1, 10)
                            ''', (store_name,))
                        conn.commit()
                        conn.close()
                    except Exception:
                        try:
                            conn.close()
                        except Exception:
                            pass

                if (i + 1) % 50 == 0:
                    _log(f"[补店铺名] 进度 {i+1}/{len(shop_ids)}", self.log_func)

                time.sleep(random.uniform(0.3, 0.8))

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(name_worker, i) for i in range(3)]
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception:
                    pass

        if risk_event.is_set():
            _log("[补店铺名] 检测到风控, 进入冷却", self.log_func)
            self._wait_risk_cooldown()

        _log(f"[补店铺名] 完成: 补充{filled_count}/{len(shop_ids)}个商铺名称", self.log_func)
        self._running = False
        return filled_count

    def rescan_for_new_and_delisted(self, shop_ids, db_path):
        _log(f"[API-2] 第二轮: 重新扫描 {len(shop_ids)} 个商铺 (新品+下架标注, 并发=10)", self.log_func)

        self._running = True
        self._stop_event.clear()
        self._stats = {"shops_success": 0, "shops_fail": 0, "goods_found": 0, "shelf_time_updated": 0, "new_goods_found": 0, "delisted_marked": 0}

        stats = {"shops_success": 0, "shops_fail": 0, "goods_found": 0, "shelf_time_updated": 0, "new_goods_found": 0, "delisted_marked": 0}
        results_lock = threading.Lock()
        idx = 0
        idx_lock = threading.Lock()
        risk_event = threading.Event()
        use_tls = self._use_tls if hasattr(self, '_use_tls') else False

        def rescan_worker(worker_id):
            nonlocal idx
            while not self._stop_event.is_set() and not risk_event.is_set():
                with idx_lock:
                    if idx >= len(shop_ids):
                        break
                    shop_id = shop_ids[idx]
                    idx += 1

                shop_goods, is_risk = self._collect_one_shop(shop_id, use_tls=use_tls)

                if is_risk:
                    risk_event.set()
                    with idx_lock:
                        idx -= 1
                    return

                if not shop_goods:
                    with results_lock:
                        stats["shops_fail"] += 1
                    continue

                online_ids = set()
                for g in shop_goods:
                    gid = g.get('goods_id', '')
                    if gid:
                        online_ids.add(gid)

                filtered = [g for g in shop_goods if _classify_virtual(g.get('title', '')) != 0]

                with results_lock:
                    stats["shops_success"] += 1
                    stats["goods_found"] += len(filtered)

                if db_path and filtered:
                    db_result = _save_to_db(db_path, shop_id, filtered, self.log_func, self._db_write_lock)
                    if db_result:
                        st_updated, new_goods = db_result
                        with results_lock:
                            stats["shelf_time_updated"] += st_updated
                            stats["new_goods_found"] += new_goods

                if db_path and online_ids:
                    try:
                        conn = sqlite3.connect(db_path, timeout=30)
                        conn.execute("PRAGMA journal_mode=WAL")
                        conn.execute("PRAGMA busy_timeout=30000")
                        c = conn.cursor()
                        placeholders = ','.join(['?'] * len(online_ids))
                        c.execute(f'''
                            UPDATE goods SET delisted = 1
                            WHERE store_id = ?
                              AND delisted = 0
                              AND goods_id NOT IN ({placeholders})
                        ''', [shop_id] + list(online_ids))
                        delisted_count = c.rowcount
                        if delisted_count > 0:
                            with results_lock:
                                stats["delisted_marked"] += delisted_count
                            _log(f"[API-2] 商铺{shop_id}: 标记{delisted_count}个已下架商品", self.log_func)
                        conn.commit()
                        conn.close()
                    except Exception:
                        try:
                            conn.close()
                        except Exception:
                            pass

                with results_lock:
                    done = stats["shops_success"] + stats["shops_fail"]
                    if done > 0 and done % 10 == 0:
                        _log(f"[API-2] 第二轮 {done}/{len(shop_ids)} | 成功={stats['shops_success']} 新品={stats['new_goods_found']} 下架={stats['delisted_marked']}", self.log_func)

                time.sleep(random.uniform(0.3, 0.8))

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(rescan_worker, i) for i in range(3)]
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception:
                    pass

        if risk_event.is_set():
            _log("[API-2] 第二轮检测到风控, 进入冷却", self.log_func)
            self._wait_risk_cooldown()

        _log(f"[API-2] 第二轮完成: 新品={stats['new_goods_found']} 下架标注={stats['delisted_marked']}", self.log_func)
        self._stats = dict(stats)
        self._running = False


def _parse_chinese_number(text):
    if not text:
        return 0
    text = str(text).strip()
    if "万" in text:
        nums = re.findall(r"[\d.]+", text)
        if nums:
            try:
                return int(float(nums[0]) * 10000)
            except ValueError:
                return 0
    nums = re.findall(r"\d+", text)
    if nums:
        try:
            return int(nums[0])
        except ValueError:
            return 0
    return 0


def _infer_category(title, location=""):
    if not title:
        return ""
    categories = {
        "饰品": ["耳环", "项链", "手链", "戒指", "发夹", "胸针", "手镯", "脚链"],
        "服装": ["连衣裙", "T恤", "衬衫", "外套", "裤子", "半裙", "卫衣", "毛衣", "风衣", "棉服", "羽绒服", "背心"],
        "美妆": ["口红", "粉底", "眼影", "面膜", "精华", "防晒", "卸妆", "眉笔", "睫毛膏", "腮红", "遮瑕"],
        "护肤": ["面霜", "乳液", "爽肤水", "精华液", "眼霜", "洗面奶", "润唇膏"],
        "包包": ["手提包", "单肩包", "双肩包", "斜挎包", "钱包", "手拿包", "托特包"],
        "鞋子": ["运动鞋", "高跟鞋", "平底鞋", "凉鞋", "靴子", "拖鞋", "老爹鞋", "帆布鞋"],
        "家居": ["抱枕", "地毯", "窗帘", "收纳", "花瓶", "台灯", "挂画", "四件套"],
        "食品": ["零食", "茶叶", "咖啡", "蜂蜜", "坚果", "果干", "糕点"],
        "数码": ["手机壳", "耳机", "充电宝", "键盘", "鼠标", "音箱", "数据线"],
        "母婴": ["奶瓶", "纸尿裤", "婴儿车", "玩具", "辅食", "童装"],
    }
    for cat, keywords in categories.items():
        for kw in keywords:
            if kw in title:
                return cat
    return ""


class GoodsDetailCollector:
    def __init__(self, config=None, log_func=None):
        self.config = config or {}
        self.log_func = log_func
        self._running = False
        self._stop_event = threading.Event()
        self._db_write_lock = threading.Lock()
        self._stats = {
            "details_success": 0,
            "details_fail": 0,
        }

    def stop(self):
        self._stop_event.set()
        self._running = False

    def get_stats(self):
        return dict(self._stats)

    def _fetch_goods_detail(self, session, fingerprint_headers, goods_id):
        url = f"https://mall.xiaohongshu.com/api/store/jpd/edith/detail/h5/toc?version=0.0.5&item_id={goods_id}"
        headers = dict(fingerprint_headers)

        for retry in range(3):
            try:
                r = session.get(url, headers=headers, timeout=(10, 20))
                r.raise_for_status()
                data = r.json()
                if data.get('error_code') == 0:
                    template_data = data.get('data', {}).get('template_data', [{}])
                    if not template_data:
                        template_data = [{}]
                    t = template_data[0]

                    sales = 0
                    iat = t.get('priceH5', {}).get('itemAnalysisDataText')
                    if iat:
                        sales = _parse_chinese_number(iat)
                    if sales == 0:
                        sv = t.get('sellerH5', {}).get('salesVolume', '')
                        if sv:
                            sales = _parse_chinese_number(sv)

                    seller_h5 = t.get('sellerH5', {})
                    shop_name = seller_h5.get('name', '') or ''
                    fans = _parse_chinese_number(seller_h5.get('fansAmount', '0') or '0')
                    shop_id = str(seller_h5.get('id', '') or '')
                    shop_score = seller_h5.get('sellerScore', '')
                    shop_total_sales = _parse_chinese_number(seller_h5.get('salesVolume', '') or '0')

                    location = ''
                    for path in [
                        t.get('goodsDistributeV4', {}).get('location'),
                        t.get('deliveryInfo', {}).get('from'),
                        t.get('freightInfo', {}).get('sendFrom'),
                        t.get('logisticsInfo', {}).get('sendCity'),
                    ]:
                        if path:
                            location = path
                            break

                    title = ''
                    for kp in [('descriptionH5', 'name'), ('descriptionMain', 'name'),
                               ('goodsH5', 'name'), ('goodsInfo', 'name'), ('itemInfo', 'name')]:
                        obj = t
                        found = True
                        for k in kp:
                            if isinstance(obj, dict):
                                obj = obj.get(k)
                            else:
                                found = False
                                break
                        if found and obj and isinstance(obj, str):
                            title = obj
                            break
                    if not title:
                        title = t.get('cardTitle', '') or t.get('desc', '')

                    shelf_time = ''
                    for tp in [('goodsH5', 'onShelfTime'), ('itemInfo', 'onShelfTime'),
                               ('goodsInfo', 'listTime'), ('onShelfTime',), ('descriptionH5', 'createTime')]:
                        obj = t
                        val = None
                        for k in tp:
                            if isinstance(obj, dict):
                                val = obj.get(k)
                                obj = val if isinstance(val, dict) else {}
                            else:
                                val = None
                                break
                        if val and not isinstance(val, dict):
                            shelf_time = _convert_timestamp(val)
                            break

                    original_price = 0
                    deal_price = 0
                    ph5 = t.get('priceH5', {})
                    highlight = ph5.get('highlightPrice')
                    if highlight is not None:
                        try:
                            original_price = float(highlight)
                        except (ValueError, TypeError):
                            pass
                    dp = ph5.get('dealPrice', {})
                    if isinstance(dp, dict) and dp.get('price'):
                        try:
                            deal_price = float(dp['price'])
                        except (ValueError, TypeError):
                            pass
                    if deal_price == 0 and original_price > 0:
                        deal_price = original_price
                    if original_price == 0 and deal_price > 0:
                        original_price = deal_price

                    bottom_bar = t.get('bottomBarMainH5', {})
                    if original_price == 0 and bottom_bar.get('price'):
                        try:
                            original_price = float(bottom_bar['price'])
                        except (ValueError, TypeError):
                            pass
                    if deal_price == 0 and bottom_bar.get('dealPrice', {}).get('price'):
                        try:
                            deal_price = float(bottom_bar['dealPrice']['price'])
                        except (ValueError, TypeError):
                            pass

                    main_image = ''
                    carousel = t.get('carouselH5', {})
                    imgs = carousel.get('images', [])
                    if imgs and isinstance(imgs, list):
                        first = imgs[0]
                        if isinstance(first, dict):
                            img_url = first.get('url', '')
                            if img_url:
                                main_image = f"https:{img_url}" if img_url.startswith('//') else img_url

                    return {
                        'goods_id': goods_id,
                        'real_sales': sales,
                        'shop_name': shop_name,
                        'shop_id': shop_id,
                        'fans_count': fans,
                        'shop_score': shop_score,
                        'shop_total_sales': shop_total_sales,
                        'ship_from': location,
                        'original_price': original_price,
                        'deal_price': deal_price,
                        'product_name': title,
                        'shelf_time': shelf_time,
                        'product_image_url': main_image,
                        'category_tag': _infer_category(title, location),
                        'data_source': 'product_detail',
                    }
                else:
                    return None
            except Exception:
                time.sleep(1)
                continue
        return None

    def collect_details(self, goods_ids, db_path=None):
        self._running = True
        self._stop_event.clear()
        self._stats = {"details_success": 0, "details_fail": 0}

        proxy_pool = self.config.get('_proxy_pool')
        is_unlimited = hasattr(proxy_pool, '_api_type') and getattr(proxy_pool, '_api_type', '') == 'unlimited'

        _log(f"[商品详情] 串行模式 开始采集 {len(goods_ids)} 个商品详情", self.log_func)

        all_details = []
        stats = {"details_success": 0, "details_fail": 0}

        def _get_new_proxy():
            if proxy_pool:
                for _attempt in range(3):
                    try:
                        if is_unlimited:
                            p = proxy_pool.get_fresh_proxy()
                        else:
                            p = proxy_pool.get_proxy()
                        if p:
                            return p
                    except Exception:
                        pass
                    time.sleep(1)
            p = self.config.get('proxy_str')
            if p:
                return p
            return None

        proxy_str = _get_new_proxy()
        fingerprint_headers, fp_profile = _generate_fingerprint()
        impersonate = fp_profile.get('impersonate') if HAS_CURL_CFFI else None
        session = _create_session(proxy_str=proxy_str, cookie_str=self.config.get('cookie_str', ''), impersonate=impersonate, fp_profile=fp_profile)

        def _rebuild_session(reason=""):
            nonlocal session, fingerprint_headers, proxy_str
            old_session = session
            try:
                old_session.cookies.clear()
                old_session.close()
            except Exception:
                pass
            new_proxy = None
            if proxy_pool and is_unlimited:
                for _retry in range(5):
                    try:
                        p = proxy_pool.get_fresh_proxy()
                        if p:
                            new_proxy = p
                            break
                    except Exception:
                        pass
                    time.sleep(2)
                if not new_proxy:
                    time.sleep(10)
                    try:
                        p = proxy_pool.get_fresh_proxy()
                        if p:
                            new_proxy = p
                    except Exception:
                        pass
            else:
                new_proxy = _get_new_proxy()
            if new_proxy:
                proxy_str = new_proxy
            fingerprint_headers, fp_profile = _generate_fingerprint()
            impersonate = fp_profile.get('impersonate') if HAS_CURL_CFFI else None
            session = _create_session(proxy_str=proxy_str, cookie_str=self.config.get('cookie_str', ''), impersonate=impersonate, fp_profile=fp_profile)
            _warmup_session(session, fingerprint_headers, log_func=self.log_func)
            if reason:
                proxy_display = proxy_str.split('@')[-1] if proxy_str and '@' in proxy_str else '无代理'
                _log(f"[Detail-Engine] {reason} (新代理={proxy_display})", self.log_func)

        for current_idx, goods_id in enumerate(goods_ids):
            if self._stop_event.is_set():
                break

            if is_unlimited:
                _rebuild_session("不限量模式: 商品切换获取新IP")

            detail = self._fetch_goods_detail(session, fingerprint_headers, goods_id)

            if detail:
                all_details.append(detail)
                stats["details_success"] += 1
                if db_path:
                    self._save_detail_to_db(detail, db_path)
            else:
                stats["details_fail"] += 1

            if (current_idx + 1) % 20 == 0:
                _log(f"[商品详情] 进度 {current_idx+1}/{len(goods_ids)} | 成功={stats['details_success']} 失败={stats['details_fail']}", self.log_func)

            time.sleep(0.3)

        _log(f"[商品详情] 串行采集完成: 成功={stats['details_success']}, 失败={stats['details_fail']}", self.log_func)

        self._stats = dict(stats)
        self._running = False
        return all_details

    def _save_detail_to_db(self, detail, db_path):
        try:
            with self._db_write_lock:
                conn = sqlite3.connect(db_path, timeout=15)
                try:
                    c = conn.cursor()
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    goods_id = detail.get("goods_id", "")

                    c.execute("SELECT goods_id FROM goods_detail_web WHERE goods_id = ?", (goods_id,))
                    if c.fetchone():
                        c.execute('''
                            UPDATE goods_detail_web SET
                                web_product_name = COALESCE(NULLIF(?, ''), web_product_name),
                                web_deal_price = CASE WHEN ? > 0 THEN ? ELSE web_deal_price END,
                                web_original_price = CASE WHEN ? > 0 THEN ? ELSE web_original_price END,
                                web_real_sales = CASE WHEN ? > 0 THEN ? ELSE web_real_sales END,
                                web_shop_name = COALESCE(NULLIF(?, ''), web_shop_name),
                                web_shop_id = COALESCE(NULLIF(?, ''), web_shop_id),
                                web_fans_count = CASE WHEN ? > 0 THEN ? ELSE web_fans_count END,
                                web_shop_score = COALESCE(NULLIF(?, ''), web_shop_score),
                                web_shop_total_sales = CASE WHEN ? > 0 THEN ? ELSE web_shop_total_sales END,
                                web_ship_from = COALESCE(NULLIF(?, ''), web_ship_from),
                                web_shelf_time = COALESCE(NULLIF(?, ''), web_shelf_time),
                                web_product_image_url = COALESCE(NULLIF(?, ''), web_product_image_url),
                                web_category_tag = COALESCE(NULLIF(?, ''), web_category_tag),
                                web_data_source = ?,
                                web_fetch_time = ?,
                                updated_at = ?
                            WHERE goods_id = ?
                        ''', (
                            detail.get("product_name", ""),
                            detail.get("deal_price", 0), detail.get("deal_price", 0),
                            detail.get("original_price", 0), detail.get("original_price", 0),
                            detail.get("real_sales", 0), detail.get("real_sales", 0),
                            detail.get("shop_name", ""),
                            detail.get("shop_id", ""),
                            detail.get("fans_count", 0), detail.get("fans_count", 0),
                            detail.get("shop_score", ""),
                            detail.get("shop_total_sales", 0), detail.get("shop_total_sales", 0),
                            detail.get("ship_from", ""),
                            detail.get("shelf_time", ""),
                            detail.get("product_image_url", ""),
                            detail.get("category_tag", ""),
                            detail.get("data_source", "product_detail"),
                            now,
                            now,
                            goods_id,
                        ))
                    else:
                        c.execute('''
                            INSERT INTO goods_detail_web (
                                goods_id, web_product_name, web_deal_price, web_original_price,
                                web_real_sales, web_shop_name, web_shop_id, web_fans_count,
                                web_shop_score, web_shop_total_sales, web_ship_from, web_shelf_time,
                                web_product_image_url, web_category_tag, web_data_source, web_fetch_time
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            goods_id,
                            detail.get("product_name", ""),
                            detail.get("deal_price", 0),
                            detail.get("original_price", 0),
                            detail.get("real_sales", 0),
                            detail.get("shop_name", ""),
                            detail.get("shop_id", ""),
                            detail.get("fans_count", 0),
                            detail.get("shop_score", ""),
                            detail.get("shop_total_sales", 0),
                            detail.get("ship_from", ""),
                            detail.get("shelf_time", ""),
                            detail.get("product_image_url", ""),
                            detail.get("category_tag", ""),
                            detail.get("data_source", "product_detail"),
                            now,
                        ))

                    c.execute('''
                        UPDATE unified_goods SET
                            product_name = COALESCE(NULLIF(?, ''), product_name),
                            deal_price = CASE WHEN ? > 0 THEN ? ELSE deal_price END,
                            original_price = CASE WHEN ? > 0 THEN ? ELSE original_price END,
                            sold_num = CASE WHEN ? > 0 THEN ? ELSE sold_num END,
                            store_name = COALESCE(NULLIF(?, ''), store_name),
                            store_id = COALESCE(NULLIF(?, ''), store_id),
                            shelf_time = COALESCE(NULLIF(?, ''), shelf_time),
                            updated_at = ?
                        WHERE goods_id = ?
                    ''', (
                        detail.get("product_name", ""),
                        detail.get("deal_price", 0), detail.get("deal_price", 0),
                        detail.get("original_price", 0), detail.get("original_price", 0),
                        detail.get("real_sales", 0), detail.get("real_sales", 0),
                        detail.get("shop_name", ""),
                        detail.get("shop_id", ""),
                        detail.get("shelf_time", ""),
                        now,
                        goods_id,
                    ))

                    conn.commit()
                finally:
                    conn.close()
        except Exception as e:
            _log(f"[商品详情] DB写入失败: {e}", self.log_func)

    def fill_missing_store_names(self, shop_ids, db_path=None):
        _log(f"[补店铺名] API串行模式开始补充 {len(shop_ids)} 个商铺名称", self.log_func)

        self._running = True
        self._stop_event.clear()

        filled_count = 0
        proxy_pool = self.config.get('_proxy_pool')
        is_unlimited = hasattr(proxy_pool, '_api_type') and getattr(proxy_pool, '_api_type', '') == 'unlimited'

        def _get_name_proxy():
            if proxy_pool:
                for _attempt in range(3):
                    try:
                        if is_unlimited:
                            p = proxy_pool.get_fresh_proxy()
                        else:
                            p = proxy_pool.get_proxy()
                        if p:
                            return p
                    except Exception:
                        pass
                    time.sleep(1)
            return self.config.get('proxy_str')

        fp_headers, fp_prof = _generate_fingerprint()
        imp = fp_prof.get('impersonate') if HAS_CURL_CFFI else None
        sess = _create_session(
            proxy_str=_get_name_proxy(),
            cookie_str=self.config.get('cookie_str', ''),
            impersonate=imp,
            fp_profile=fp_prof,
        )
        p_min = self.config.get("page_interval_min", 0.5)
        p_max = self.config.get("page_interval_max", 2.0)

        for current_idx, shop_id in enumerate(shop_ids):
            if self._stop_event.is_set():
                break

            if is_unlimited:
                fp_headers, fp_prof = _generate_fingerprint()
                imp = fp_prof.get('impersonate') if HAS_CURL_CFFI else None
                sess = _create_session(
                    proxy_str=_get_name_proxy(),
                    cookie_str=self.config.get('cookie_str', ''),
                    impersonate=imp,
                    fp_profile=fp_prof,
                )

            store_name = _fetch_store_name_from_page(sess, fp_headers, shop_id)

            if store_name and db_path:
                try:
                    conn = sqlite3.connect(db_path, timeout=30)
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA busy_timeout=30000")
                    c = conn.cursor()
                    c.execute(
                        'UPDATE store_scores SET store_name=? WHERE store_id=? AND (store_name IS NULL OR store_name="")',
                        (store_name, shop_id)
                    )
                    if c.rowcount > 0:
                        c.execute(
                            'UPDATE goods SET store_name=? WHERE store_id=? AND (store_name IS NULL OR store_name="")',
                            (store_name, shop_id)
                        )
                        filled_count += 1
                    try:
                        c.execute('''
                            INSERT OR IGNORE INTO keyword_pool (keyword, category, is_active, priority, source)
                            VALUES (?, 'store_name', 1, 10, 'web_fill_name')
                        ''', (store_name,))
                        if c.rowcount > 0:
                            _log(f"[关键词池] 补店铺名发现新关键词: {store_name} (store_id={shop_id})", self.log_func)
                    except Exception:
                        pass
                    conn.commit()
                    conn.close()
                except Exception as e:
                    try:
                        conn.close()
                    except Exception:
                        pass
                    _log(f"[补店铺名] {shop_id} 写入失败: {e}", self.log_func)

            if (current_idx + 1) % 50 == 0:
                _log(f"[补店铺名] 进度 {current_idx+1}/{len(shop_ids)}", self.log_func)

            delay = random.uniform(p_min * 0.3, p_max * 0.3)
            time.sleep(delay)

        _log(f"[补店铺名] API串行模式完成: 成功补充 {filled_count}/{len(shop_ids)} 个商铺名称", self.log_func)

        self._running = False
        return filled_count


# ============================================================
# HighConcurrencyShopCollector - 高并发代理池模式采集
# 每个Worker每个店铺获取新IP，最大化IP利用率
# ============================================================
class HighConcurrencyShopCollector:
    def __init__(self, config=None, log_func=None):
        self.config = config or {}
        self.log_func = log_func
        self._running = False
        self._stop_event = threading.Event()
        self._db_write_lock = threading.Lock()
        self._stats = {
            "shops_success": 0,
            "shops_fail": 0,
            "goods_found": 0,
            "shelf_time_updated": 0,
            "new_goods_found": 0,
        }

    def stop(self):
        self._stop_event.set()
        self._running = False

    def is_running(self):
        return self._running

    def get_stats(self):
        return dict(self._stats)

    def _collect_one_shop(self, session, fingerprint_headers, shop_id, worker_id):
        all_goods = []
        seen_ids = set()
        proxy_error = False

        store_name = _fetch_store_name_from_page(session, fingerprint_headers, shop_id)

        try:
            for page_num in range(100):
                if self._stop_event.is_set():
                    break

                goods_list, has_more, is_risk, next_last_id = _fetch_shop_goods_page(
                    session, fingerprint_headers, shop_id, page_num, log_func=self.log_func)

                if is_risk:
                    proxy_error = True
                    break

                new_in_page = 0
                for g in goods_list:
                    gid = g.get('goods_id', '')
                    if gid and gid not in seen_ids:
                        seen_ids.add(gid)
                        all_goods.append(g)
                        new_in_page += 1

                if not has_more or new_in_page == 0:
                    break

        except requests.exceptions.ProxyError:
            _log(f"[HC-Engine] Worker#{worker_id}: {shop_id} 代理连接失败(非风控)", self.log_func)
        except Exception as e:
            err_str = str(e).lower()
            if 'proxy' in err_str or 'recv failure' in err_str or 'connection was reset' in err_str or 'curl' in err_str:
                _log(f"[HC-Engine] Worker#{worker_id}: {shop_id} 网络/代理错误(非风控): {str(e)[:60]}", self.log_func)
            else:
                _log(f"[HC-Engine] Worker#{worker_id}: {shop_id} 采集异常: {str(e)[:80]}", self.log_func)

        if store_name:
            for g in all_goods:
                if not g.get('store_name'):
                    g['store_name'] = store_name

        return all_goods, proxy_error

    def collect_shop_list(self, shop_ids, db_path, virtual_filter_fn=None, skip_store_fn=None):
        self._running = True
        self._stop_event.clear()
        self._stats = {"shops_success": 0, "shops_fail": 0, "goods_found": 0, "shelf_time_updated": 0, "new_goods_found": 0}

        proxy_pool = self.config.get('_proxy_pool')
        is_unlimited = hasattr(proxy_pool, '_api_type') and getattr(proxy_pool, '_api_type', '') == 'unlimited'

        _log(f"[高并发] 串行模式 开始采集 {len(shop_ids)} 个商铺", self.log_func)

        all_goods = []
        stats = {"shops_success": 0, "shops_fail": 0, "goods_found": 0, "shelf_time_updated": 0, "new_goods_found": 0}

        def _get_new_proxy():
            if proxy_pool:
                for _attempt in range(3):
                    try:
                        if is_unlimited:
                            p = proxy_pool.get_fresh_proxy()
                        else:
                            p = proxy_pool.get_proxy()
                        if p:
                            return p
                    except Exception:
                        pass
                    time.sleep(1)
            p = self.config.get('proxy_str')
            if p:
                return p
            return None

        fingerprint_headers, fp_profile = _generate_fingerprint()
        proxy_str = _get_new_proxy()
        impersonate = fp_profile.get('impersonate') if HAS_CURL_CFFI else None
        session = _create_session(
            proxy_str=proxy_str,
            cookie_str=self.config.get('cookie_str', ''),
            impersonate=impersonate,
            fp_profile=fp_profile,
        )
        _warmup_session(session, fingerprint_headers, log_func=self.log_func)

        consecutive_fails = 0

        try:
            for current_idx, shop_id in enumerate(shop_ids):
                if self._stop_event.is_set():
                    break

                if skip_store_fn and skip_store_fn(shop_id):
                    continue

                if is_unlimited:
                    old_proxy = proxy_str
                    try:
                        session.cookies.clear()
                        session.close()
                    except Exception:
                        pass
                    if proxy_pool and old_proxy:
                        try:
                            proxy_pool.release(old_proxy, success=True)
                        except Exception:
                            pass
                    fingerprint_headers, fp_profile = _generate_fingerprint()
                    proxy_str = _get_new_proxy()
                    impersonate = fp_profile.get('impersonate') if HAS_CURL_CFFI else None
                    session = _create_session(
                        proxy_str=proxy_str,
                        cookie_str=self.config.get('cookie_str', ''),
                        impersonate=impersonate,
                        fp_profile=fp_profile,
                    )
                    _warmup_session(session, fingerprint_headers, log_func=self.log_func)

                shop_page_goods, proxy_error, _network_error = self._collect_one_shop(
                    session, fingerprint_headers, shop_id, 0)

                if proxy_error:
                    _log(f"[高并发] 风控触发，停止采集", self.log_func)
                    break

                if not shop_page_goods:
                    consecutive_fails += 1
                    stats["shops_fail"] += 1
                    if consecutive_fails >= 3:
                        fingerprint_headers, fp_profile = _generate_fingerprint()
                        proxy_str = _get_new_proxy()
                        impersonate = fp_profile.get('impersonate') if HAS_CURL_CFFI else None
                        session = _create_session(
                            proxy_str=proxy_str,
                            cookie_str=self.config.get('cookie_str', ''),
                            impersonate=impersonate,
                            fp_profile=fp_profile,
                        )
                        _warmup_session(session, fingerprint_headers, log_func=self.log_func)
                        consecutive_fails = 0
                    continue

                consecutive_fails = 0
                if virtual_filter_fn:
                    filtered = [g for g in shop_page_goods if virtual_filter_fn(g.get('title', ''))]
                else:
                    filtered = [g for g in shop_page_goods if _classify_virtual(g.get('title', '')) != 0]
                all_goods.extend(filtered)
                stats["goods_found"] += len(filtered)
                stats["shops_success"] += 1
                if db_path:
                    db_result = _save_to_db(db_path, shop_id, filtered, self.log_func, self._db_write_lock)
                    if db_result:
                        st_updated, new_goods = db_result
                        stats["shelf_time_updated"] += st_updated
                        stats["new_goods_found"] += new_goods

                time.sleep(random.uniform(0.2, 0.5))

                done = stats["shops_success"] + stats["shops_fail"]
                if done > 0 and done % 10 == 0:
                    s = stats
                    _log(f"[高并发] {done}/{len(shop_ids)} | 成功={s['shops_success']} 失败={s['shops_fail']} 商品={s['goods_found']}", self.log_func)

        finally:
            try:
                session.cookies.clear()
                session.close()
            except Exception:
                pass
            if proxy_pool and proxy_str:
                try:
                    proxy_pool.release(proxy_str, success=True)
                except Exception:
                    pass

        _log(f"[高并发] 串行模式完成: {stats['shops_success']}个商铺, {len(all_goods)}个商品, shelf_time更新={stats['shelf_time_updated']}, 新商品={stats['new_goods_found']}", self.log_func)

        self._stats = dict(stats)
        self._running = False
        return all_goods

    def fill_missing_store_names(self, shop_ids, db_path=None):
        self._running = True
        self._stop_event.clear()

        proxy_pool = self.config.get('_proxy_pool')
        is_unlimited = hasattr(proxy_pool, '_api_type') and getattr(proxy_pool, '_api_type', '') == 'unlimited'

        _log(f"[高并发补名] 串行模式 开始补充 {len(shop_ids)} 个商铺名称", self.log_func)

        filled_count = 0

        def _get_name_proxy():
            if proxy_pool:
                for _attempt in range(3):
                    try:
                        if is_unlimited:
                            p = proxy_pool.get_fresh_proxy()
                        else:
                            p = proxy_pool.get_proxy()
                        if p:
                            return p
                    except Exception:
                        pass
                    time.sleep(1)
            return self.config.get('proxy_str')

        fp_headers, fp_prof = _generate_fingerprint()
        imp = fp_prof.get('impersonate') if HAS_CURL_CFFI else None
        sess = _create_session(
            proxy_str=_get_name_proxy(),
            cookie_str=self.config.get('cookie_str', ''),
            impersonate=imp,
            fp_profile=fp_prof,
        )
        p_min = self.config.get("page_interval_min", 0.5)
        p_max = self.config.get("page_interval_max", 2.0)

        for current_idx, shop_id in enumerate(shop_ids):
            if self._stop_event.is_set():
                break

            if is_unlimited:
                fp_headers, fp_prof = _generate_fingerprint()
                imp = fp_prof.get('impersonate') if HAS_CURL_CFFI else None
                sess = _create_session(
                    proxy_str=_get_name_proxy(),
                    cookie_str=self.config.get('cookie_str', ''),
                    impersonate=imp,
                    fp_profile=fp_prof,
                )

            store_name = _fetch_store_name_from_page(sess, fp_headers, shop_id)

            if store_name and db_path:
                try:
                    conn = sqlite3.connect(db_path, timeout=30)
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA busy_timeout=30000")
                    c = conn.cursor()
                    c.execute(
                        'UPDATE store_scores SET store_name=? WHERE store_id=? AND (store_name IS NULL OR store_name="")',
                        (store_name, shop_id)
                    )
                    if c.rowcount > 0:
                        c.execute(
                            'UPDATE goods SET store_name=? WHERE store_id=? AND (store_name IS NULL OR store_name="")',
                            (store_name, shop_id)
                        )
                        filled_count += 1
                    try:
                        c.execute('''
                            INSERT OR IGNORE INTO keyword_pool (keyword, category, is_active, priority, source, related_store_id)
                            VALUES (?, 'store_name', 1, 10, 'hc_fill_name', ?)
                        ''', (store_name, shop_id))
                    except Exception:
                        pass
                    conn.commit()
                    conn.close()
                except Exception as e:
                    try:
                        conn.close()
                    except Exception:
                        pass
                    _log(f"[高并发补名] {shop_id} 写入失败: {e}", self.log_func)

            if (current_idx + 1) % 50 == 0:
                _log(f"[高并发补名] 进度 {current_idx+1}/{len(shop_ids)}", self.log_func)

            delay = random.uniform(p_min * 0.3, p_max * 0.3)
            time.sleep(delay)

        _log(f"[高并发补名] 串行模式完成: 成功补充 {filled_count}/{len(shop_ids)} 个商铺名称", self.log_func)

        self._running = False
        return filled_count
# ============================================================
try:
    from DrissionPage import ChromiumPage, ChromiumOptions
    HAS_DRISSIONPAGE = True
except ImportError:
    HAS_DRISSIONPAGE = False

DP_FINGERPRINT_POOL = [
    {"webgl_vendor": "NVIDIA Corporation", "webgl_renderer": "NVIDIA GeForce GTX 1650/PCIe/SSE2", "device_memory": 8, "hardware_concurrency": 6, "screen_w": 1920, "screen_h": 1080, "ua_ver": 147, "color_depth": 24, "pixel_ratio": 1.0},
    {"webgl_vendor": "NVIDIA Corporation", "webgl_renderer": "NVIDIA GeForce RTX 3060/PCIe/SSE2", "device_memory": 16, "hardware_concurrency": 12, "screen_w": 2560, "screen_h": 1440, "ua_ver": 146, "color_depth": 24, "pixel_ratio": 1.0},
    {"webgl_vendor": "Intel Inc.", "webgl_renderer": "Intel(R) UHD Graphics 630", "device_memory": 8, "hardware_concurrency": 8, "screen_w": 1920, "screen_h": 1080, "ua_ver": 145, "color_depth": 24, "pixel_ratio": 1.0},
    {"webgl_vendor": "NVIDIA Corporation", "webgl_renderer": "NVIDIA GeForce RTX 4060/PCIe/SSE2", "device_memory": 16, "hardware_concurrency": 12, "screen_w": 1920, "screen_h": 1080, "ua_ver": 144, "color_depth": 24, "pixel_ratio": 1.25},
    {"webgl_vendor": "Intel Inc.", "webgl_renderer": "Intel(R) Iris Xe Graphics", "device_memory": 8, "hardware_concurrency": 8, "screen_w": 1366, "screen_h": 768, "ua_ver": 143, "color_depth": 24, "pixel_ratio": 1.0},
    {"webgl_vendor": "NVIDIA Corporation", "webgl_renderer": "NVIDIA GeForce GTX 1060 6GB/PCIe/SSE2", "device_memory": 8, "hardware_concurrency": 6, "screen_w": 1920, "screen_h": 1080, "ua_ver": 142, "color_depth": 24, "pixel_ratio": 1.0},
    {"webgl_vendor": "NVIDIA Corporation", "webgl_renderer": "NVIDIA GeForce RTX 3070/PCIe/SSE2", "device_memory": 16, "hardware_concurrency": 14, "screen_w": 2560, "screen_h": 1440, "ua_ver": 141, "color_depth": 30, "pixel_ratio": 1.0},
    {"webgl_vendor": "X.Org", "webgl_renderer": "AMD Radeon RX 580 Series (polaris10, LLVM 15.0.7, DRM 3.49, 6.1.0)", "device_memory": 8, "hardware_concurrency": 8, "screen_w": 1920, "screen_h": 1080, "ua_ver": 140, "color_depth": 24, "pixel_ratio": 1.0},
    {"webgl_vendor": "NVIDIA Corporation", "webgl_renderer": "NVIDIA GeForce RTX 2060/PCIe/SSE2", "device_memory": 8, "hardware_concurrency": 8, "screen_w": 1536, "screen_h": 864, "ua_ver": 139, "color_depth": 24, "pixel_ratio": 1.25},
    {"webgl_vendor": "NVIDIA Corporation", "webgl_renderer": "NVIDIA GeForce GTX 1660 SUPER/PCIe/SSE2", "device_memory": 8, "hardware_concurrency": 8, "screen_w": 1920, "screen_h": 1080, "ua_ver": 138, "color_depth": 24, "pixel_ratio": 1.0},
]

_DP_FP_IDX = 0
_DP_FP_LOCK = threading.Lock()


def _dp_assign_fingerprint():
    global _DP_FP_IDX
    with _DP_FP_LOCK:
        idx = _DP_FP_IDX % len(DP_FINGERPRINT_POOL)
        _DP_FP_IDX += 1
    fp = dict(DP_FINGERPRINT_POOL[idx])
    fp['canvas_noise'] = round(random.uniform(0.01, 0.05), 4)
    fp['audio_noise'] = round(random.uniform(0.0001, 0.0005), 6)
    fp['webgl2_vendor'] = fp['webgl_vendor']
    fp['webgl2_renderer'] = fp['webgl_renderer']
    return fp


def _dp_cache_fingerprint(profile_id, fp):
    cache_dir = os.path.join(DATA_DIR, "dp_fp_cache")
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"profile_{profile_id}.json")
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(fp, f, ensure_ascii=False)
    except Exception:
        pass


def _dp_load_cached_fingerprint(profile_id):
    cache_path = os.path.join(DATA_DIR, "dp_fp_cache", f"profile_{profile_id}.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                fp = json.load(f)
            if all(k in fp for k in ('webgl_vendor', 'webgl_renderer', 'ua_ver')):
                return fp
        except Exception:
            pass
    return None


def _dp_check_profile_health(page, profile_id):
    try:
        result = page.run_js("document.readyState")
        if result and result in ('loading', 'interactive', 'complete'):
            return True
    except Exception:
        pass
    _log(f"[DP] 主机#{profile_id}: Profile健康检查失败, 需要回收", None)
    return False


def _build_dp_stealth_js(fp):
    vendor = fp["webgl_vendor"]
    renderer = fp["webgl_renderer"]
    webgl2_vendor = fp.get("webgl2_vendor", vendor)
    webgl2_renderer = fp.get("webgl2_renderer", renderer)
    dev_mem = fp["device_memory"]
    hw_conc = fp["hardware_concurrency"]
    color_depth = fp["color_depth"]
    ver = fp["ua_ver"]
    canvas_noise = fp.get("canvas_noise", 0.02)
    audio_noise = fp.get("audio_noise", 0.0003)
    return f"""
() => {{
    Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});
    delete navigator.__proto__.webdriver;
    Object.defineProperty(navigator, 'languages', {{ get: () => ['zh-CN', 'zh', 'en'] }});
    Object.defineProperty(navigator, 'platform', {{ get: () => 'Win32' }});
    Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {hw_conc} }});
    Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {dev_mem} }});
    Object.defineProperty(navigator, 'maxTouchPoints', {{ get: () => 0 }});
    Object.defineProperty(screen, 'colorDepth', {{ get: () => {color_depth} }});
    Object.defineProperty(screen, 'pixelDepth', {{ get: () => {color_depth} }});
    Object.defineProperty(navigator, 'connection', {{ get: () => ({{ effectiveType: '4g', rtt: 50, downlink: 10, saveData: false }}) }});
    window.chrome = {{
        runtime: {{
            onConnect: {{ addListener: function(){{}}, removeListener: function(){{}} }},
            onMessage: {{ addListener: function(){{}}, removeListener: function(){{}} }},
            sendMessage: function(){{}},
            connect: function(){{ return {{ onMessage: {{ addListener: function(){{}} }}, postMessage: function(){{}} }}; }}
        }},
        csi: function(){{ return {{}}; }},
        loadTimes: function(){{ return {{}}; }},
        app: {{ isInstalled: false, InstallState: {{ DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' }}, RunningState: {{ CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' }} }}
    }};
    Object.defineProperty(navigator, 'plugins', {{
        get: () => {{
            const plugins = [
                {{ name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format', length: 1 }},
                {{ name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '', length: 1 }},
                {{ name: 'Native Client', filename: 'internal-nacl-plugin', description: '', length: 2 }}
            ];
            plugins.item = function(i) {{ return this[i] || null; }};
            plugins.namedItem = function(n) {{ for (let i=0;i<this.length;i++) if (this[i].name===n) return this[i]; return null; }};
            plugins.refresh = function() {{}};
            return plugins;
        }}
    }});
    Object.defineProperty(navigator, 'mimeTypes', {{
        get: () => {{
            const mimeTypes = [
                {{ type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format', enabledPlugin: navigator.plugins[0] }},
                {{ type: 'text/pdf', suffixes: 'pdf', description: 'Portable Document Format', enabledPlugin: navigator.plugins[0] }}
            ];
            mimeTypes.item = function(i) {{ return this[i] || null; }};
            mimeTypes.namedItem = function(n) {{ for (let i=0;i<this.length;i++) if (this[i].type===n) return this[i]; return null; }};
            return mimeTypes;
        }}
    }});
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {{
        if (parameter === 37445) return '{vendor}';
        if (parameter === 37446) return '{renderer}';
        return getParameter.call(this, parameter);
    }};
    if (typeof WebGL2RenderingContext !== 'undefined') {{
        const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
        WebGL2RenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) return '{webgl2_vendor}';
            if (parameter === 37446) return '{webgl2_renderer}';
            return getParameter2.call(this, parameter);
        }};
    }}
    const getExtension = WebGLRenderingContext.prototype.getExtension;
    WebGLRenderingContext.prototype.getExtension = function(name) {{
        const ext = getExtension.call(this, name);
        if (name === 'WEBGL_debug_renderer_info' && ext) {{
            return new Proxy(ext, {{
                get(target, prop) {{
                    if (prop === 'UNMASKED_VENDOR_WEBGL') return '{vendor}';
                    if (prop === 'UNMASKED_RENDERER_WEBGL') return '{renderer}';
                    return target[prop];
                }}
            }});
        }}
        return ext;
    }};
    if (typeof WebGL2RenderingContext !== 'undefined') {{
        const getExtension2 = WebGL2RenderingContext.prototype.getExtension;
        WebGL2RenderingContext.prototype.getExtension = function(name) {{
            const ext = getExtension2.call(this, name);
            if (name === 'WEBGL_debug_renderer_info' && ext) {{
                return new Proxy(ext, {{
                    get(target, prop) {{
                        if (prop === 'UNMASKED_VENDOR_WEBGL') return '{webgl2_vendor}';
                        if (prop === 'UNMASKED_RENDERER_WEBGL') return '{webgl2_renderer}';
                        return target[prop];
                    }}
                }});
            }}
            return ext;
        }};
    }}
    const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {{
        const ctx = this.getContext('2d');
        if (ctx) {{
            const imgData = ctx.getImageData(0, 0, this.width, this.height);
            for (let i = 0; i < imgData.data.length; i += 4) {{
                imgData.data[i] = Math.min(255, Math.max(0, imgData.data[i] + ({canvas_noise} * Math.random())));
            }}
            ctx.putImageData(imgData, 0, 0);
        }}
        return origToDataURL.apply(this, arguments);
    }};
    const origToBlob = HTMLCanvasElement.prototype.toBlob;
    HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {{
        const ctx = this.getContext('2d');
        if (ctx) {{
            const imgData = ctx.getImageData(0, 0, this.width, this.height);
            for (let i = 0; i < imgData.data.length; i += 4) {{
                imgData.data[i] = Math.min(255, Math.max(0, imgData.data[i] + ({canvas_noise} * Math.random())));
            }}
            ctx.putImageData(imgData, 0, 0);
        }}
        return origToBlob.apply(this, arguments);
    }};
    const origGetChannelData = AudioBuffer.prototype.getChannelData;
    AudioBuffer.prototype.getChannelData = function(channel) {{
        const data = origGetChannelData.call(this, channel);
        for (let i = 0; i < data.length; i += 100) {{
            data[i] += {audio_noise};
        }}
        return data;
    }};
    Object.defineProperty(navigator, 'userAgentData', {{
        get: () => ({{
            brands: [
                {{ brand: 'Google Chrome', version: '{ver}' }},
                {{ brand: 'Not.A/Brand', version: '8' }},
                {{ brand: 'Chromium', version: '{ver}' }}
            ],
            mobile: false,
            platform: 'Windows',
            getHighEntropyValues: function(hints) {{
                return Promise.resolve({{
                    architecture: 'x86',
                    bitness: '64',
                    model: '',
                    platformVersion: '15.0.0',
                    fullVersionList: [
                        {{ brand: 'Google Chrome', version: '{ver}.0.0.0' }},
                        {{ brand: 'Not.A/Brand', version: '8.0.0.0' }},
                        {{ brand: 'Chromium', version: '{ver}.0.0.0' }}
                    ]
                }});
            }}
        }})
    }});
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({{ state: Notification.permission }}) :
            originalQuery(parameters)
    );
}}
"""


# ============================================================
# ShopFansSalesCollector - /shop/页面补充粉丝数和店铺总销量
# ============================================================

class ShopFansSalesCollector:
    """从 /shop/{store_id} 页面采集粉丝数和店铺总销量，补充到 store_scores 表"""

    def __init__(self, config=None, log_func=None):
        self.config = config or {}
        self.log_func = log_func
        self._running = False
        self._stop_event = threading.Event()
        self._db_write_lock = threading.Lock()

    def stop(self):
        self._stop_event.set()
        self._running = False

    def is_running(self):
        return self._running

    def fill_fans_and_sales(self, shop_ids, db_path=None):
        """采集指定商铺的粉丝数和总销量，写入store_scores表"""
        self._running = True
        self._stop_event.clear()

        _log(f"[补粉丝销量] 串行模式 开始采集 {len(shop_ids)} 个商铺的粉丝数和总销量", self.log_func)

        filled_fans = 0
        filled_sales = 0
        filled_name = 0

        fp_headers, fp_profile = _generate_fingerprint()
        session = _create_session(impersonate=fp_profile)
        nav_headers = dict(fp_headers)
        nav_headers.update(_API_SEC_FETCH_MODES['navigate'])
        nav_headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
        nav_headers.pop('Origin', None)
        nav_headers['Referer'] = 'https://www.xiaohongshu.com/'

        for i, shop_id in enumerate(shop_ids):
            if self._stop_event.is_set():
                break

            result = _fetch_shop_fans_and_sales(session, nav_headers, shop_id, self.log_func)

            if result and db_path:
                try:
                    conn = sqlite3.connect(db_path, timeout=30)
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA busy_timeout=30000")
                    c = conn.cursor()

                    fans = result.get('fans_count', 0)
                    sales = result.get('shop_sales', 0)
                    store_name = result.get('store_name', '')

                    update_fields = []
                    update_values = []

                    if fans > 0:
                        update_fields.append("fans_count = ?")
                        update_values.append(fans)

                    if sales > 0:
                        update_fields.append("shop_sales = ?")
                        update_values.append(str(sales))

                    if store_name:
                        update_fields.append("store_name = COALESCE(NULLIF(store_name,''), ?)")
                        update_values.append(store_name)

                    if update_fields:
                        update_values.append(shop_id)
                        c.execute(
                            f"UPDATE store_scores SET {', '.join(update_fields)} WHERE store_id = ?",
                            update_values
                        )
                        if c.rowcount > 0:
                            if fans > 0:
                                filled_fans += 1
                            if sales > 0:
                                filled_sales += 1
                            if store_name:
                                filled_name += 1

                    conn.commit()
                    conn.close()
                except Exception:
                    try:
                        conn.close()
                    except Exception:
                        pass

            if (i + 1) % 50 == 0:
                _log(f"[补粉丝销量] 进度 {i+1}/{len(shop_ids)}", self.log_func)

            time.sleep(random.uniform(0.1, 0.3))

        _log(f"[补粉丝销量] 串行模式完成: 粉丝数{filled_fans} 销量{filled_sales} 店名{filled_name}/{len(shop_ids)}", self.log_func)
        self._running = False
        return filled_fans, filled_sales


ANTI_DETECT_JS = _build_dp_stealth_js(DP_FINGERPRINT_POOL[0])

SHOP_API_LISTEN_PREFIX = '/api/store/vs/'


class DrissionPageShopCollector:
    RISK_COOLDOWNS = [1800, 3600, 5400, 7200]

    def __init__(self, config=None, log_func=None):
        if not HAS_DRISSIONPAGE:
            raise ImportError("DrissionPage未安装, 请运行: pip install DrissionPage")
        self.config = config or {}
        self.log_func = log_func
        self._running = False
        self._stop_event = threading.Event()
        self._db_write_lock = threading.Lock()
        self._stats = {
            "shops_success": 0,
            "shops_fail": 0,
            "goods_found": 0,
            "shelf_time_updated": 0,
            "new_goods_found": 0,
        }
        self._risk_level = 0
        self._risk_until = 0

    def stop(self):
        self._stop_event.set()
        self._running = False

    def is_running(self):
        return self._running

    def get_stats(self):
        return dict(self._stats)

    def _wait_risk_cooldown(self):
        if self._risk_level >= len(self.RISK_COOLDOWNS):
            self._risk_level = 0
        cooldown_sec = self.RISK_COOLDOWNS[self._risk_level]
        self._risk_level += 1
        self._risk_until = time.time() + cooldown_sec
        mins = cooldown_sec // 60
        _log(f"[DP] 风控冷却 {mins} 分钟 (等级{self._risk_level})", self.log_func)
        while time.time() < self._risk_until:
            if self._stop_event.is_set():
                return False
            remaining = int(self._risk_until - time.time())
            if remaining > 0 and remaining % 300 == 0:
                _log(f"[DP] 冷却剩余 {remaining // 60} 分钟", self.log_func)
            time.sleep(1)
        return True

    def _record_risk_free_max(self, engine_name, shops_count, db_path):
        if not db_path:
            return
        try:
            conn = sqlite3.connect(db_path, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            c = conn.cursor()
            c.execute("""CREATE TABLE IF NOT EXISTS risk_free_max (
                engine TEXT PRIMARY KEY,
                max_shops INTEGER DEFAULT 0,
                updated_at TEXT
            )""")
            c.execute("SELECT max_shops FROM risk_free_max WHERE engine=?", (engine_name,))
            row = c.fetchone()
            if row is None or shops_count > row[0]:
                c.execute("""INSERT OR REPLACE INTO risk_free_max (engine, max_shops, updated_at)
                    VALUES (?, ?, datetime('now'))""", (engine_name, shops_count))
                conn.commit()
            conn.close()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass

    def _create_browser(self, profile_id, fp=None):
        cached_fp = _dp_load_cached_fingerprint(profile_id)
        if cached_fp:
            fp = cached_fp
            _log(f"[DP] 主机#{profile_id}: 复用缓存指纹 GPU={fp['webgl_renderer'][:30]}...", self.log_func)
        elif fp is None:
            fp = _dp_assign_fingerprint()
        _dp_cache_fingerprint(profile_id, fp)

        user_data_dir = os.path.join(DATA_DIR, f"dp_cafe_profile_{profile_id}")
        os.makedirs(user_data_dir, exist_ok=True)

        co = ChromiumOptions()
        co.headless(True)
        co.no_imgs(True)
        co.set_user_data_path(user_data_dir)
        co.set_argument(f'--window-size={fp["screen_w"]},{fp["screen_h"]}')
        co.set_argument('--disable-blink-features=AutomationControlled')
        co.set_argument('--disable-features=IsolateOrigins,site-per-process')
        co.set_argument('--disable-infobars')
        co.set_argument('--no-first-run')
        co.set_argument('--no-default-browser-check')
        co.set_argument('--no-sandbox')
        co.set_argument('--disable-gpu')
        co.set_argument('--disable-dev-shm-usage')

        ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{fp['ua_ver']}.0.0.0 Safari/537.36"
        co.set_user_agent(ua)

        # 手动分配可用端口，避免auto_port与set_user_data_path冲突
        import socket as _socket
        for _ in range(50):
            try:
                s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
                s.bind(('127.0.0.1', 0))
                port = s.getsockname()[1]
                s.close()
                break
            except Exception:
                if s:
                    s.close()
                continue
        else:
            port = 9222 + profile_id * 100

        co.set_local_port(port)

        page = ChromiumPage(co)
        time.sleep(1.0)
        page.set.load_mode.eager()
        page.set.timeouts(page_load=15)
        stealth_js = _build_dp_stealth_js(fp)
        page.add_init_js(stealth_js)
        _log(f"[DP] 主机#{profile_id} 浏览器上线 GPU={fp['webgl_renderer'][:30]}... UA=Chrome/{fp['ua_ver']} port={port}", self.log_func)
        return page

    def _warmup_browser(self, page, profile_id):
        _log(f"[DP] 主机#{profile_id}: 预热浏览器...", self.log_func)
        try:
            page.get('https://www.xiaohongshu.com/')
        except Exception:
            pass
        time.sleep(random.uniform(2.0, 3.5))
        for _ in range(random.randint(1, 3)):
            try:
                page.run_js(f'window.scrollBy(0, {random.randint(200, 500)})')
            except Exception:
                pass
            time.sleep(random.uniform(0.5, 1.0))
        _log(f"[DP] 主机#{profile_id}: 预热完成", self.log_func)

    def _collect_one_shop_in_tab(self, tab, shop_id, profile_id, tab_id):
        all_goods = []
        seen_ids = set()

        try:
            shop_url = f'https://www.xiaohongshu.com/vendor/{shop_id}'
            try:
                tab.get(shop_url)
            except Exception:
                pass
            time.sleep(random.uniform(1.0, 2.0))

            try:
                tab.run_js(f'window.scrollTo(0, document.body.scrollHeight / 4)')
                time.sleep(random.uniform(0.3, 0.6))
            except Exception:
                pass

            for page_num in range(100):
                if self._stop_event.is_set():
                    break

                api_url = f'https://www.xiaohongshu.com/api/store/vs/{shop_id}/skus?page={page_num}'

                result = None
                for retry in range(2):
                    try:
                        result = tab.run_js(f"""
                            async () => {{
                                const url = '{api_url}';
                                const resp = await fetch(url, {{
                                    credentials: 'include',
                                    headers: {{
                                        'Accept': 'application/json, text/plain, */*',
                                        'X-Requested-With': 'XMLHttpRequest'
                                    }}
                                }});
                                const text = await resp.text();
                                try {{
                                    const data = JSON.parse(text);
                                    data._http_status = resp.status;
                                    return data;
                                }} catch(e) {{
                                    return {{_parse_error: true, _text: text.substring(0, 200), _status: resp.status}};
                                }}
                            }}
                        """)
                        break
                    except Exception:
                        time.sleep(1)

                if result is None:
                    break

                if isinstance(result, dict) and result.get('_parse_error'):
                    break

                data = result if isinstance(result, dict) else {}
                if data.get('error_code') == 0 or data.get('success') is True:
                    raw_data = data.get('data', [])
                    if raw_data is None:
                        break
                    elif isinstance(raw_data, list):
                        items = raw_data
                        no_more = (len(items) < 20)
                    elif isinstance(raw_data, dict):
                        no_more = raw_data.get('no_more_items', False)
                        items = raw_data.get('items', raw_data.get('skus', []))
                        if not isinstance(items, list):
                            items = []
                    else:
                        break

                    goods_list = []
                    for p in items:
                        if not isinstance(p, dict):
                            continue
                        item_id = str(p.get('item_id', '') or p.get('id', ''))
                        if len(item_id) < 10:
                            continue
                        price_info = p.get('price_info', {})
                        expected_price = price_info.get('expected_price', {})
                        sku_price = price_info.get('sku_price', {})
                        price_val = expected_price.get('price', 0)
                        if price_val is None:
                            price_val = 0
                        original_price = sku_price.get('price', 0)
                        if original_price is None:
                            original_price = 0
                        goods_list.append({
                            'goods_id': item_id,
                            'shop_id': str(p.get('seller_id', shop_id)),
                            'store_name': p.get('seller_name', p.get('store_name', '')),
                            'title': p.get('card_title', '') or p.get('desc', ''),
                            'deal_price': price_val,
                            'original_price': original_price,
                            'shelf_time': _convert_timestamp(p.get('on_shelf_time', 0)),
                            'stock_status': p.get('stock_status', 0),
                            'buyable': bool(p.get('buyable', False)),
                            'data_source': 'dp_shop_list',
                        })

                    new_in_page = 0
                    for g in goods_list:
                        gid = g.get('goods_id', '')
                        if gid and gid not in seen_ids:
                            seen_ids.add(gid)
                            all_goods.append(g)
                            new_in_page += 1

                    has_more = not no_more and len(items) > 0
                    if not has_more or new_in_page == 0:
                        break
                else:
                    break

                time.sleep(0.3)

        except Exception as e:
            _log(f"[DP] 主机#{profile_id}-标签#{tab_id}: {shop_id} 采集异常: {str(e)[:80]}", self.log_func)

        return all_goods

    def collect_shop_list(self, shop_ids, db_path, virtual_filter_fn=None, skip_store_fn=None):
        self._running = True
        self._stop_event.clear()
        self._stats = {"shops_success": 0, "shops_fail": 0, "goods_found": 0, "shelf_time_updated": 0, "new_goods_found": 0}

        _log(f"[DP] 串行模式 开始采集 {len(shop_ids)} 个商铺", self.log_func)

        all_goods = []
        stats = {"shops_success": 0, "shops_fail": 0, "goods_found": 0, "shelf_time_updated": 0, "new_goods_found": 0}
        risk_triggered = False

        fp = _dp_assign_fingerprint()
        page = None
        try:
            page = self._create_browser(0, fp)
            self._warmup_browser(page, 0)

            if not _dp_check_profile_health(page, 0):
                _log(f"[DP] 初始健康检查失败, 重建浏览器", self.log_func)
                try:
                    page.quit()
                except Exception:
                    pass
                fp = _dp_assign_fingerprint()
                _dp_cache_fingerprint(0, fp)
                page = self._create_browser(0, fp)
                self._warmup_browser(page, 0)

            for current_idx, shop_id in enumerate(shop_ids):
                if self._stop_event.is_set() or risk_triggered:
                    break

                if skip_store_fn and skip_store_fn(shop_id):
                    continue

                if not _dp_check_profile_health(page, 0):
                    _log(f"[DP] 健康检查失败, 跳过", self.log_func)
                    stats["shops_fail"] += 1
                    time.sleep(1.0)
                    continue

                shop_page_goods = self._collect_one_shop_in_tab(page, shop_id, 0, 0)

                if shop_page_goods is not None and len(shop_page_goods) == 0:
                    try:
                        status = page.run_js("document.readyState")
                    except Exception:
                        status = "unknown"
                    if status in ("unknown",):
                        risk_triggered = True
                        _log(f"[DP] 风控!", self.log_func)
                        break

                if shop_page_goods:
                    if virtual_filter_fn:
                        filtered = [g for g in shop_page_goods if virtual_filter_fn(g.get('title', ''))]
                    else:
                        filtered = [g for g in shop_page_goods if _classify_virtual(g.get('title', '')) != 0]
                    all_goods.extend(filtered)
                    stats["goods_found"] += len(filtered)
                    stats["shops_success"] += 1
                    if db_path:
                        db_result = _save_to_db(db_path, shop_id, filtered, self.log_func, self._db_write_lock)
                        if db_result:
                            st_updated, new_goods = db_result
                            stats["shelf_time_updated"] += st_updated
                            stats["new_goods_found"] += new_goods
                else:
                    stats["shops_fail"] += 1

                done = stats["shops_success"] + stats["shops_fail"]
                if done > 0 and done % 10 == 0:
                    s = stats
                    _log(f"[DP] {done}/{len(shop_ids)} | 成功={s['shops_success']} 商品={s['goods_found']}", self.log_func)

                time.sleep(random.uniform(0.2, 0.5))

        except Exception as e:
            _log(f"[DP] 异常退出: {str(e)[:80]}", self.log_func)
        finally:
            if page:
                try:
                    page.quit()
                except Exception:
                    pass

        if risk_triggered:
            _log(f"[DP] 风控触发! 本轮成功采集 {stats['shops_success']} 个商铺", self.log_func)
            self._record_risk_free_max("drissionpage", stats["shops_success"], db_path)
            self._wait_risk_cooldown()

        _log(f"[DP] 串行模式完成: {stats['shops_success']}个商铺, {len(all_goods)}个商品, shelf_time更新={stats['shelf_time_updated']}, 新商品={stats['new_goods_found']}", self.log_func)

        self._stats = dict(stats)
        self._running = False
        return all_goods
