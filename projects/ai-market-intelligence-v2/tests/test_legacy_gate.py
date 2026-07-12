# -*- coding: utf-8 -*-
"""legacy_gate 单元测试"""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import importlib.util

_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "legacy_gate",
    _ROOT / "cloud-stubs" / "legacy_gate.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
legacy_zip_enabled = _mod.legacy_zip_enabled
insight_enabled = _mod.insight_enabled


def _future(days=30):
    return datetime.now(timezone.utc) + timedelta(days=days)


def _past(days=1):
    return datetime.now(timezone.utc) - timedelta(days=days)


def test_v2_plan_never_zip():
    assert legacy_zip_enabled(plan_code="insight_pro_monthly", expires_at=_future()) is False
    assert insight_enabled(plan_code="insight_pro_monthly", expires_at=_future()) is True


def test_legacy_in_period_has_zip():
    assert legacy_zip_enabled(plan_code="monthly", expires_at=_future()) is True
    assert insight_enabled(plan_code="monthly", expires_at=_future()) is False


def test_legacy_expired_no_zip():
    assert legacy_zip_enabled(plan_code="yearly", expires_at=_past()) is False


def test_entitlement_override():
    assert legacy_zip_enabled(
        plan_code="monthly",
        expires_at=_future(),
        entitlements={"legacy_zip_enabled": False},
    ) is False
