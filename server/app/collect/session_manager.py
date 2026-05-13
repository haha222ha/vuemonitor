import asyncio
import hashlib
import json
import logging
import random
import time
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)


class SessionManager:
    UA_TEMPLATES = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{ver}.0) Gecko/20100101 Firefox/{ver}.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.{ver} Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36 Edg/{ver}.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36 OPR/{ver}.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36 Brave/{ver}.0.0.0",
    ]

    PLATFORMS = ["Win32", "MacIntel", "Linux x86_64"]
    PLATFORM_SEC_MAP = {
        "Win32": '"Windows"',
        "MacIntel": '"macOS"',
        "Linux x86_64": '"Linux"',
    }

    WARMUP_URLS = {
        "xhs": [
            "https://www.xiaohongshu.com/",
            "https://www.xiaohongshu.com/explore",
        ],
        "douyin": [
            "https://www.douyin.com/",
        ],
        "taobao": [
            "https://www.taobao.com/",
        ],
        "jd": [
            "https://www.jd.com/",
        ],
        "pdd": [
            "https://www.pinduoduo.com/",
        ],
    }

    COOKIE_DIR = Path("data/cookies")

    def __init__(self):
        self._sessions: dict[str, aiohttp.ClientSession] = {}
        self._session_fingerprints: dict[str, dict] = {}
        self._request_counts: dict[str, int] = {}
        self._rotate_threshold = random.randint(30, 60)
        self.COOKIE_DIR.mkdir(parents=True, exist_ok=True)

    def generate_fingerprint(self) -> dict:
        chrome_ver = random.randint(120, 136)
        ua = random.choice(self.UA_TEMPLATES).format(ver=chrome_ver)
        platform = random.choice(self.PLATFORMS)
        sec_ch_ua_platform = self.PLATFORM_SEC_MAP.get(platform, '"Windows"')

        is_mobile = random.random() < 0.1
        sec_ch_ua_mobile = "?1" if is_mobile else "?0"

        sec_ch_ua = (
            f'"Chromium";v="{chrome_ver}", '
            f'"Google Chrome";v="{chrome_ver}", '
            f'"Not-A.Brand";v="{random.randint(8, 99)}"'
        )

        accept_langs = [
            "zh-CN,zh;q=0.9,en;q=0.8",
            "zh-CN,zh;q=0.9",
            "zh-CN,zh;q=0.8,en-US;q=0.6,en;q=0.4",
            "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        ]

        return {
            "User-Agent": ua,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": random.choice(accept_langs),
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Ch-Ua": sec_ch_ua,
            "Sec-Ch-Ua-Mobile": sec_ch_ua_mobile,
            "Sec-Ch-Ua-Platform": sec_ch_ua_platform,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Platform-Hint": platform,
        }

    def generate_session_id(self) -> str:
        raw = f"{time.time()}-{random.randint(100000, 999999)}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def _cookie_path(self, platform: str) -> Path:
        return self.COOKIE_DIR / f"{platform}_cookies.json"

    async def _load_cookies(self, platform: str) -> list[dict]:
        path = self._cookie_path(platform)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
            except Exception:
                pass
        return []

    async def _save_cookies(self, platform: str, cookie_jar: aiohttp.CookieJar):
        cookies = []
        for cookie in cookie_jar:
            cookies.append({
                "name": cookie.key,
                "value": cookie.value,
                "domain": cookie.get("domain", ""),
                "path": cookie.get("path", "/"),
            })
        path = self._cookie_path(platform)
        try:
            path.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            logger.warning(f"Failed to save cookies for {platform}")

    async def get_session(self, platform: str, proxy_url: str | None = None) -> tuple[aiohttp.ClientSession, dict]:
        session_key = f"{platform}:{proxy_url or 'direct'}"

        req_count = self._request_counts.get(session_key, 0)
        if req_count >= self._rotate_threshold:
            await self._rotate_session(session_key, platform, proxy_url)
            self._request_counts[session_key] = 0
            self._rotate_threshold = random.randint(30, 60)

        if session_key in self._sessions:
            session = self._sessions[session_key]
            if not session.closed:
                fingerprint = self._session_fingerprints.get(session_key, self.generate_fingerprint())
                self._request_counts[session_key] = self._request_counts.get(session_key, 0) + 1
                return session, fingerprint

        cookie_jar = aiohttp.CookieJar(unsafe=True)
        saved_cookies = await self._load_cookies(platform)
        for c in saved_cookies:
            try:
                cookie_jar.update_cookies(
                    {c["name"]: c["value"]},
                    response_url=None,
                )
            except Exception:
                pass

        connector = aiohttp.TCPConnector(
            limit=20,
            limit_per_host=8,
            ssl=False,
            enable_cleanup_closed=True,
        )
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30, connect=10, sock_read=20),
            cookie_jar=cookie_jar,
        )

        if proxy_url:
            session._default_proxy = proxy_url

        fingerprint = self.generate_fingerprint()
        self._sessions[session_key] = session
        self._session_fingerprints[session_key] = fingerprint
        self._request_counts[session_key] = 1

        await self._warmup(session, platform, fingerprint)

        return session, fingerprint

    async def _rotate_session(self, session_key: str, platform: str, proxy_url: str | None = None):
        old_session = self._sessions.pop(session_key, None)
        if old_session and not old_session.closed:
            try:
                await self._save_cookies(platform, old_session.cookie_jar)
            except Exception:
                pass
            try:
                await old_session.close()
            except Exception:
                pass
        self._session_fingerprints[session_key] = self.generate_fingerprint()

    async def _warmup(self, session: aiohttp.ClientSession, platform: str, fingerprint: dict):
        warmup_urls = self.WARMUP_URLS.get(platform, ["https://www.baidu.com/"])
        warmup_headers = dict(fingerprint)
        warmup_headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        warmup_headers["Sec-Fetch-Dest"] = "document"
        warmup_headers["Sec-Fetch-Mode"] = "navigate"

        for url in warmup_urls:
            try:
                async with session.get(
                    url,
                    headers=warmup_headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                    allow_redirects=True,
                    ssl=False,
                ) as resp:
                    pass
                await asyncio.sleep(random.uniform(0.5, 1.5))
            except Exception:
                pass

    async def close_all(self):
        for key, session in self._sessions.items():
            if not session.closed:
                platform = key.split(":")[0]
                try:
                    await self._save_cookies(platform, session.cookie_jar)
                except Exception:
                    pass
                try:
                    await session.close()
                except Exception:
                    pass
        self._sessions.clear()
        self._session_fingerprints.clear()
        self._request_counts.clear()

    async def rotate_fingerprint(self, platform: str, proxy_url: str | None = None):
        session_key = f"{platform}:{proxy_url or 'direct'}"
        self._session_fingerprints[session_key] = self.generate_fingerprint()
        self._request_counts[session_key] = 0
