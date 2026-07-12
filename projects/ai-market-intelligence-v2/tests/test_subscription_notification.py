# -*- coding: utf-8 -*-
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.notification_mock import list_notifications, mark_read
from services.subscription_mock import can_generate, get_plan_info, record_generation, set_plan


def test_plan():
    info = get_plan_info()
    assert info["plan_id"]
    assert "usage_today" in info


def test_can_generate():
    set_plan("insight_pro_monthly")
    ok, _ = can_generate("美甲美睫")
    assert ok


def test_notifications():
    r = list_notifications(refresh=True)
    assert r["items"]
    assert "unread_count" in r
    mark_read(r["items"][0]["id"])


if __name__ == "__main__":
    test_plan()
    test_can_generate()
    test_notifications()
    print("subscription + notification tests OK")
