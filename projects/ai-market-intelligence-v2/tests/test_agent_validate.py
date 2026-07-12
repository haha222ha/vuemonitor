# -*- coding: utf-8 -*-
"""agent_validate 单元测试。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.agent_validate import AgentOutputError, validate_agent_output


def test_ceo_valid():
    data = validate_agent_output(
        "ceo",
        {"executive_summary": "ok", "opportunity_stars": 4, "confidence": 0.8, "verdict": "适合进入"},
    )
    assert data["opportunity_stars"] == 4


def test_market_missing_field():
    try:
        validate_agent_output("market", {"trend_summary": "x"})
        assert False, "should raise"
    except AgentOutputError as e:
        assert e.agent == "market"


if __name__ == "__main__":
    test_ceo_valid()
    test_market_missing_field()
    print("agent_validate tests OK")
