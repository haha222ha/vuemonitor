# -*- coding: utf-8 -*-
"""
LLM 客户端 — 默认 PackyAPI + DeepSeek V4 Flash（OpenAI 兼容）。

与主仓库 server/app/ai/providers.py DeepSeekProvider 对齐：
  base_url = https://www.packyapi.com/v1
  model    = deepseek-v4-flash

PackyAPI 令牌分组须选 deepseek-officially，见 docs/13-LLM-PACKYAPI-DEEPSEEK.md
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# .env 加载统一由 services.env_loader.load_lab_env() 负责(在 server/pipeline 入口调用),
# 此处不再重复加载,避免 python-dotenv 与 env_loader 行为不一致。

# 预设（env 可覆盖）
PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "packy_deepseek": {
        "base_url": "https://www.packyapi.com/v1",
        "model": "deepseek-v4-flash",
    },
    "deepseek_direct": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-v4-flash",
    },
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
    },
}

LLM_PROFILES_PATH = Path(__file__).resolve().parents[1] / "config" / "llm_profiles.yaml"


class LLMError(RuntimeError):
    pass


@dataclass
class LLMUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ""
    agent: str = ""


def _env(key: str, default: str = "") -> str:
    return (os.environ.get(key) or default).strip()


def llm_configured() -> bool:
    return bool(_env("INSIGHT_LLM_API_KEY") or _env("DEEPSEEK_API_KEY"))


def _api_key() -> str:
    key = _env("INSIGHT_LLM_API_KEY") or _env("DEEPSEEK_API_KEY")
    if not key:
        raise LLMError("INSIGHT_LLM_API_KEY / DEEPSEEK_API_KEY 未配置")
    return key


def _load_profiles() -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        return {}
    if not LLM_PROFILES_PATH.is_file():
        return {}
    return yaml.safe_load(LLM_PROFILES_PATH.read_text(encoding="utf-8")) or {}


def _resolve_config(agent: str | None = None) -> tuple[str, str, str, bool]:
    """返回 (base_url, model, provider_name, thinking_disabled)。"""
    profiles = _load_profiles()
    provider = _env("INSIGHT_LLM_PROVIDER") or profiles.get("provider") or "packy_deepseek"
    preset = PROVIDER_PRESETS.get(provider, PROVIDER_PRESETS["packy_deepseek"])

    base = _env("INSIGHT_LLM_BASE_URL") or profiles.get("base_url") or preset["base_url"]
    base = base.rstrip("/")

    default_model = _env("INSIGHT_LLM_MODEL") or profiles.get("default_model") or preset["model"]

    model = default_model
    if agent:
        agents_map = profiles.get("agents") or {}
        env_key = f"INSIGHT_LLM_MODEL_{agent.upper()}"
        model = _env(env_key) or agents_map.get(agent) or default_model

    thinking_raw = _env("INSIGHT_LLM_THINKING") or profiles.get("thinking") or "disabled"
    thinking_disabled = thinking_raw.lower() in ("0", "false", "no", "disabled", "off")

    return base, model, provider, thinking_disabled


def _parse_json_content(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    if not text:
        raise LLMError("LLM 返回空内容")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        return json.loads(m.group(1).strip())
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        return json.loads(m.group(0))
    raise LLMError(f"LLM 响应非 JSON: {text[:200]}")


def chat_json(
    system: str,
    user: str,
    *,
    agent: str | None = None,
    temperature: float = 0.3,
) -> dict[str, Any]:
    """
    调用 Chat Completions，要求模型返回 JSON 对象。
    返回的 dict 不含 _llm_usage；用量见 chat_json_with_usage。
    """
    result, _ = chat_json_with_usage(system, user, agent=agent, temperature=temperature)
    return result


def chat_json_with_usage(
    system: str,
    user: str,
    *,
    agent: str | None = None,
    temperature: float = 0.3,
) -> tuple[dict[str, Any], LLMUsage]:
    base, model, provider, thinking_disabled = _resolve_config(agent)
    timeout = int(_env("INSIGHT_LLM_TIMEOUT") or "60")
    max_retries = int(_env("INSIGHT_LLM_MAX_RETRIES") or "2")

    payload: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {
                "role": "system",
                "content": system + "\n\n你必须只输出一个 JSON 对象，不要 markdown 代码块。",
            },
            {"role": "user", "content": user},
        ],
    }

    # DeepSeek V4 默认开启 thinking；Agent JSON 任务建议关闭以降延迟/成本
    if thinking_disabled and "deepseek-v4" in model.lower():
        payload["thinking"] = {"type": "disabled"}

    # 智谱 / Packy OpenAI 兼容通道支持 json_object
    if provider in ("packy_deepseek", "deepseek_direct", "zhipu") or _env("INSIGHT_LLM_JSON_MODE", "1") != "0":
        payload["response_format"] = {"type": "json_object"}

    url = f"{base}/chat/completions"
    last_err: Exception | None = None

    for attempt in range(max_retries + 1):
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {_api_key()}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            parsed = _parse_json_content(content)
            usage_raw = body.get("usage") or {}
            usage = LLMUsage(
                prompt_tokens=int(usage_raw.get("prompt_tokens") or 0),
                completion_tokens=int(usage_raw.get("completion_tokens") or 0),
                model=model,
                agent=agent or "",
            )
            return parsed, usage
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            last_err = LLMError(f"LLM HTTP {e.code} [{model}@{provider}]: {detail}")
            if e.code in (429, 500, 502, 503, 504) and attempt < max_retries:
                time.sleep(min(2 ** attempt, 8))
                continue
            raise last_err from e
        except (LLMError, json.JSONDecodeError) as e:
            last_err = e if isinstance(e, LLMError) else LLMError(str(e))
            if attempt < max_retries:
                time.sleep(1)
                continue
            raise last_err from e
        except Exception as e:
            raise LLMError(str(e)) from e

    raise last_err or LLMError("LLM 调用失败")


def describe_config() -> dict[str, Any]:
    """供 health / 调试接口展示（不含 Key）。"""
    base, model, provider, thinking_disabled = _resolve_config()
    _, ceo_model, _, _ = _resolve_config("ceo")
    return {
        "configured": llm_configured(),
        "provider": provider,
        "base_url": base,
        "default_model": model,
        "ceo_model": ceo_model,
        "thinking": "disabled" if thinking_disabled else "enabled",
    }
