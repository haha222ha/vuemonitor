import asyncio
import hashlib
import random
import time
import logging

import aiohttp

logger = logging.getLogger(__name__)


class SessionManager:
    UA_TEMPLATES = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{ver}.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{ver}.0) Gecko/20100101 Firefox/{ver}.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.{ver} Safari/605.1.15",
    ]

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

    def __init__(self):
        self._sessions: dict[str, aiohttp.ClientSession] = {}
        self._session_fingerprints: dict[str, dict] = {}

    def generate_fingerprint(self) -> dict:
        chrome_ver = random.randint(115, 131)
        ua = random.choice(self.UA_TEMPLATES).format(ver=chrome_ver)
        sec_ch_ua = (
            f'"Chromium";v="{chrome_ver}", '
            f'"Google Chrome";v="{chrome_ver}", '
            f'"Not-A.Brand";v="99"'
        )
        return {
            "User-Agent": ua,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Ch-Ua": sec_ch_ua,
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

    def generate_session_id(self) -> str:
        raw = f"{time.time()}-{random.randint(100000, 999999)}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    async def get_session(self, platform: str, proxy_url: str | None = None) -> tuple[aiohttp.ClientSession, dict]:
        session_key = f"{platform}:{proxy_url or 'direct'}"

        if session_key in self._sessions:
            session = self._sessions[session_key]
            if not session.closed:
                fingerprint = self._session_fingerprints.get(session_key, self.generate_fingerprint())
                return session, fingerprint

        connector = aiohttp.TCPConnector(
            limit=20,
            limit_per_host=8,
            ssl=False,
            enable_cleanup_closed=True,
        )
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30, connect=10, sock_read=20),
        )

        if proxy_url:
            session._default_proxy = proxy_url

        fingerprint = self.generate_fingerprint()
        self._sessions[session_key] = session
        self._session_fingerprints[session_key] = fingerprint

        await self._warmup(session, platform, fingerprint)

        return session, fingerprint

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
                await asyncio.sleep(random.uniform(0.3, 0.8))
            except Exception:
                pass

    async def close_all(self):
        for key, session in self._sessions.items():
            if not session.closed:
                try:
                    await session.close()
                except Exception:
                    pass
        self._sessions.clear()
        self._session_fingerprints.clear()

    async def rotate_fingerprint(self, platform: str, proxy_url: str | None = None):
        session_key = f"{platform}:{proxy_url or 'direct'}"
        self._session_fingerprints[session_key] = self.generate_fingerprint()
