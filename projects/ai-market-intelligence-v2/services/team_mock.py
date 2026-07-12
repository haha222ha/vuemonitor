# -*- coding: utf-8 -*-
"""Team 多席位 mock（实验室）。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TEAM_PATH = Path(__file__).resolve().parents[1] / "output" / "team_org.json"


def get_team_mock() -> dict[str, Any]:
    if TEAM_PATH.is_file():
        try:
            return json.loads(TEAM_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "org": {"name": "演示团队", "plan_code": "insight_team_monthly", "max_seats": 5},
        "seats": [
            {"role": "owner", "email": "owner@demo.local", "status": "active", "label": "主账号（你）"},
            {"role": "member", "email": "member1@demo.local", "status": "active", "label": "研究员 A"},
            {"role": "member", "email": "member2@demo.local", "status": "pending", "label": "待接受邀请"},
            {"role": "member", "email": None, "status": "empty", "label": "空席位"},
            {"role": "member", "email": None, "status": "empty", "label": "空席位"},
        ],
        "used_seats": 2,
        "max_seats": 5,
    }
