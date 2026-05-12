import json
import logging
from typing import Any

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

FEATURE_FLAGS_KEY = "feature_flags"
FLAG_CACHE_TTL = 300

_DEFAULT_FLAGS: dict[str, dict] = {
    "new_dashboard": {"enabled": True, "rollout_pct": 100, "allowed_plans": None, "description": "新版数据看板"},
    "ai_report_v2": {"enabled": True, "rollout_pct": 100, "allowed_plans": ["pro", "premium", "enterprise"], "description": "AI报告V2"},
    "team_collaboration": {"enabled": True, "rollout_pct": 100, "allowed_plans": ["premium", "enterprise"], "description": "团队协作"},
    "advanced_analytics": {"enabled": False, "rollout_pct": 0, "allowed_plans": ["enterprise"], "description": "高级分析"},
    "mobile_app": {"enabled": False, "rollout_pct": 10, "allowed_plans": None, "description": "移动端适配"},
    "export_csv": {"enabled": True, "rollout_pct": 100, "allowed_plans": ["pro", "premium", "enterprise"], "description": "CSV导出"},
    "export_pdf": {"enabled": True, "rollout_pct": 100, "allowed_plans": ["premium", "enterprise"], "description": "PDF导出"},
    "batch_collect": {"enabled": True, "rollout_pct": 100, "allowed_plans": ["pro", "premium", "enterprise"], "description": "批量采集"},
    "risk_alert": {"enabled": True, "rollout_pct": 100, "allowed_plans": ["premium", "enterprise"], "description": "风险预警"},
    "custom_template": {"enabled": False, "rollout_pct": 0, "allowed_plans": ["enterprise"], "description": "自定义模板"},
}


class FeatureFlagService:
    def __init__(self):
        self._local_cache: dict[str, dict] = {}
        self._cache_ts: float = 0

    async def _load_flags(self) -> dict[str, dict]:
        import time
        now = time.time()
        if self._local_cache and now - self._cache_ts < FLAG_CACHE_TTL:
            return self._local_cache

        try:
            redis = await get_redis()
            data = await redis.get(FEATURE_FLAGS_KEY)
            if data:
                self._local_cache = json.loads(data)
            else:
                self._local_cache = dict(_DEFAULT_FLAGS)
                await redis.set(FEATURE_FLAGS_KEY, json.dumps(self._local_cache))
            self._cache_ts = now
        except Exception:
            self._local_cache = dict(_DEFAULT_FLAGS)

        return self._local_cache

    async def is_enabled(
        self,
        flag_name: str,
        user_id: str | None = None,
        plan: str | None = None,
    ) -> bool:
        flags = await self._load_flags()
        flag = flags.get(flag_name)

        if not flag:
            return False

        if not flag.get("enabled", False):
            return False

        allowed_plans = flag.get("allowed_plans")
        if allowed_plans and plan and plan not in allowed_plans:
            return False

        rollout_pct = flag.get("rollout_pct", 0)
        if rollout_pct < 100 and user_id:
            import hashlib
            hash_val = int(hashlib.md5(f"{flag_name}:{user_id}".encode()).hexdigest(), 16)
            bucket = (hash_val % 100) + 1
            return bucket <= rollout_pct

        return True

    async def get_all_flags(self) -> dict[str, dict]:
        return await self._load_flags()

    async def set_flag(self, flag_name: str, config: dict) -> dict:
        flags = await self._load_flags()
        flags[flag_name] = {**flags.get(flag_name, {}), **config}

        redis = await get_redis()
        await redis.set(FEATURE_FLAGS_KEY, json.dumps(flags))
        self._local_cache = flags
        self._cache_ts = 0

        logger.info(f"Feature flag updated: {flag_name} -> {config}")
        return flags[flag_name]

    async def delete_flag(self, flag_name: str) -> bool:
        flags = await self._load_flags()
        if flag_name not in flags:
            return False

        del flags[flag_name]
        redis = await get_redis()
        await redis.set(FEATURE_FLAGS_KEY, json.dumps(flags))
        self._local_cache = flags
        self._cache_ts = 0
        return True

    async def reset_to_defaults(self) -> dict:
        self._local_cache = dict(_DEFAULT_FLAGS)
        redis = await get_redis()
        await redis.set(FEATURE_FLAGS_KEY, json.dumps(self._local_cache))
        self._cache_ts = 0
        return self._local_cache


feature_flag_service = FeatureFlagService()
