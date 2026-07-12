# -*- coding: utf-8 -*-
"""
测试 PackyAPI + DeepSeek V4 Flash 连通性。

  cd projects/ai-market-intelligence-v2
  copy .env.example .env   # 填入 INSIGHT_LLM_API_KEY
  python scripts/test_llm_connection.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.env_loader import load_lab_env
from services.llm_client import LLMError, chat_json_with_usage, describe_config, llm_configured

load_lab_env(ROOT)


def main() -> int:
    cfg = describe_config()
    print("=== LLM 配置 ===")
    print(json.dumps(cfg, ensure_ascii=False, indent=2))

    if not llm_configured():
        print("\n未配置 INSIGHT_LLM_API_KEY（或 DEEPSEEK_API_KEY），跳过真 LLM 测试。")
        return 0

    print("\n=== 连通性测试（deepseek-v4-flash JSON）===")
    try:
        result, usage = chat_json_with_usage(
            "你是测试助手。只输出 JSON。",
            '回复 {"status":"ok","model_working":true}',
            agent="market",
        )
        print("响应:", json.dumps(result, ensure_ascii=False))
        print(f"用量: in={usage.prompt_tokens} out={usage.completion_tokens} model={usage.model}")
        print("\n✅ LLM 连通正常")
        return 0
    except LLMError as e:
        print(f"\n❌ LLM 失败: {e}")
        print("\n排查：")
        print("  1. PackyAPI 令牌分组是否为 deepseek-officially")
        print("  2. BASE_URL 是否为 https://www.packyapi.com/v1")
        print("  3. 模型名是否为 deepseek-v4-flash")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
