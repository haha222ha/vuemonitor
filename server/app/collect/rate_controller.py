import asyncio
import random
import time
from datetime import datetime, timezone


class AdaptiveRateController:
    HUMAN_BEHAVIOR_PROFILES = {
        "fast": {"base": 0.5, "variance": 0.3, "pause_chance": 0.05, "pause_range": (1.0, 3.0)},
        "normal": {"base": 1.5, "variance": 0.8, "pause_chance": 0.1, "pause_range": (2.0, 6.0)},
        "slow": {"base": 3.0, "variance": 1.5, "pause_chance": 0.15, "pause_range": (5.0, 15.0)},
        "cautious": {"base": 5.0, "variance": 2.0, "pause_chance": 0.2, "pause_range": (10.0, 30.0)},
    }

    def __init__(
        self,
        base_interval: float = 1.0,
        min_interval: float = 0.2,
        max_interval: float = 10.0,
        profile: str = "normal",
    ):
        self.current_interval = base_interval
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.consecutive_success = 0
        self._last_request_time: float | None = None
        self._profile = profile
        self._request_count = 0
        self._session_start = time.monotonic()
        self._backoff_until: float | None = None

    @property
    def profile_config(self) -> dict:
        return self.HUMAN_BEHAVIOR_PROFILES.get(self._profile, self.HUMAN_BEHAVIOR_PROFILES["normal"])

    def set_profile(self, profile: str):
        if profile in self.HUMAN_BEHAVIOR_PROFILES:
            self._profile = profile
            config = self.profile_config
            self.current_interval = config["base"]

    async def acquire(self):
        if self._backoff_until is not None:
            now = time.monotonic()
            if now < self._backoff_until:
                wait = self._backoff_until - now
                await asyncio.sleep(wait)
            self._backoff_until = None

        if self._last_request_time is not None:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            config = self.profile_config

            base_wait = max(0, self.current_interval - elapsed)
            jitter = random.uniform(0, config["variance"])

            if random.random() < config["pause_chance"]:
                pause_duration = random.uniform(*config["pause_range"])
                jitter += pause_duration

            total_wait = base_wait + jitter
            if total_wait > 0:
                await asyncio.sleep(total_wait)

        self._last_request_time = asyncio.get_event_loop().time()
        self._request_count += 1

    def on_success(self):
        self.consecutive_success += 1
        if self.consecutive_success >= 10:
            self.current_interval = max(self.min_interval, self.current_interval * 0.9)
            self.consecutive_success = 0

    def on_risk_detected(self):
        self.consecutive_success = 0
        self.current_interval = min(self.max_interval, self.current_interval * 2.0)
        self._backoff_until = time.monotonic() + random.uniform(5.0, 15.0)

    def on_captcha_detected(self):
        self.consecutive_success = 0
        self.current_interval = min(self.max_interval, self.current_interval * 3.0)
        self._backoff_until = time.monotonic() + random.uniform(30.0, 60.0)

    def on_error(self):
        self.consecutive_success = 0
        self.current_interval = min(self.max_interval, self.current_interval * 1.5)

    def on_ip_blocked(self):
        self.consecutive_success = 0
        self.current_interval = self.max_interval
        self._backoff_until = time.monotonic() + random.uniform(60.0, 120.0)

    def reset(self):
        self.current_interval = 1.0
        self.consecutive_success = 0
        self._backoff_until = None

    @property
    def stats(self) -> dict:
        elapsed = time.monotonic() - self._session_start
        return {
            "request_count": self._request_count,
            "current_interval": round(self.current_interval, 2),
            "profile": self._profile,
            "consecutive_success": self.consecutive_success,
            "elapsed_seconds": round(elapsed, 1),
            "avg_rps": round(self._request_count / max(elapsed, 1), 3),
        }
