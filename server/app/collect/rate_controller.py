import asyncio
import random
from datetime import datetime, timezone


class AdaptiveRateController:
    def __init__(
        self,
        base_interval: float = 1.0,
        min_interval: float = 0.2,
        max_interval: float = 10.0,
    ):
        self.current_interval = base_interval
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.consecutive_success = 0
        self._last_request_time: float | None = None

    async def acquire(self):
        if self._last_request_time is not None:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            wait = max(0, self.current_interval - elapsed)
            jitter = random.uniform(0, wait * 0.2)
            if wait + jitter > 0:
                await asyncio.sleep(wait + jitter)
        self._last_request_time = asyncio.get_event_loop().time()

    def on_success(self):
        self.consecutive_success += 1
        if self.consecutive_success >= 10:
            self.current_interval = max(self.min_interval, self.current_interval * 0.9)
            self.consecutive_success = 0

    def on_risk_detected(self):
        self.consecutive_success = 0
        self.current_interval = min(self.max_interval, self.current_interval * 2.0)

    def on_error(self):
        self.consecutive_success = 0
        self.current_interval = min(self.max_interval, self.current_interval * 1.5)

    def reset(self):
        self.current_interval = 1.0
        self.consecutive_success = 0
