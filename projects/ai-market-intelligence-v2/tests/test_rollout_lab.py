# -*- coding: utf-8 -*-
"""v2.2 上线需求 Lab 验收测试"""
from __future__ import annotations

import importlib.util
import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_portal_route_insight_only():
    ent = _load_module("entitlements_v2", _ROOT / "cloud-stubs" / "entitlements_v2.py")
    raw = {"insight_enabled": True, "insight_only": True, "legacy_zip_enabled": False}
    assert ent.portal_route(raw) == "insight_only"


def test_portal_route_legacy_preview():
    ent = _load_module("entitlements_v2", _ROOT / "cloud-stubs" / "entitlements_v2.py")
    raw = ent.PREVIEW_ENTITLEMENTS_LEGACY
    assert ent.portal_route(raw) == "legacy_with_preview"


def test_lab_personas_and_profile():
    lab = _load_module("lab_session", _ROOT / "services" / "lab_session.py")
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        lab.SESSION_PATH = td_path / "lab_session.json"
        lab.SESSIONS_DIR = td_path / "sessions"
        prof = lab.set_persona("insight_pro")
        assert prof["portal_route"] == "insight_only"
        assert prof["entitlements"]["legacy_zip_enabled"] is False
        prof2 = lab.set_persona("legacy_only")
        assert prof2["portal_route"] == "legacy_only"
        assert prof2["entitlements"]["insight_enabled"] is False


def test_lab_persona_timeline_entitlements():
    """A1/A2 回归：Pro 30 天、legacy_preview 7 天时间轴"""
    lab = _load_module("lab_session", _ROOT / "services" / "lab_session.py")
    ent = _load_module("entitlements_v2", _ROOT / "cloud-stubs" / "entitlements_v2.py")
    pro_cfg = lab.get_persona_config("insight_pro")
    preview_cfg = lab.get_persona_config("legacy_preview")
    assert pro_cfg["entitlements"]["insight_timeline_days"] == 30
    assert preview_cfg["entitlements"]["insight_timeline_days"] == 7
    ok, msg = ent.can_insight_timeline(pro_cfg["entitlements"], days=7)
    assert ok is True, msg
    ok2, msg2 = ent.can_insight_timeline(preview_cfg["entitlements"], days=7)
    assert ok2 is True, msg2
    std_cfg = lab.get_persona_config("insight_standard")
    ok3, _ = ent.can_insight_timeline(std_cfg["entitlements"], days=7)
    assert ok3 is False


def test_report_storage_persona_isolation():
    storage = _load_module("report_storage", _ROOT / "services" / "report_storage.py")
    lab = _load_module("lab_session", _ROOT / "services" / "lab_session.py")
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        storage.OUTPUT = base
        lab.SESSION_PATH = base / "lab_session.json"
        lab.SESSIONS_DIR = base / "sessions"
        lab.set_persona("insight_pro")
        storage.save_report(
            "2026-07-12",
            "美甲美睫",
            "<html>pro</html>",
            {"category": "美甲美睫", "report_date": "2026-07-12"},
            {"opportunity_stars": 4},
            persona="insight_pro",
        )
        lab.set_persona("insight_standard")
        storage.save_report(
            "2026-07-12",
            "小学教辅",
            "<html>std</html>",
            {"category": "小学教辅", "report_date": "2026-07-12"},
            {"opportunity_stars": 3},
            persona="insight_standard",
        )
        pro_path = storage.resolve_preview_path(persona="insight_pro")
        std_path = storage.resolve_preview_path(persona="insight_standard")
        assert pro_path is not None and "pro" in pro_path.read_text()
        assert std_path is not None and "std" in std_path.read_text()
        assert "std" not in pro_path.read_text()
        assert "pro" not in std_path.read_text()


def test_llm_budget_record():
    budget = _load_module("llm_budget", _ROOT / "services" / "llm_budget.py")
    with tempfile.TemporaryDirectory() as td:
        budget.USAGE_PATH = Path(td) / "llm_usage.json"
        ok, _ = budget.check_budget("insight_pro_monthly")
        assert ok is True
        budget.record_usage({"prompt_tokens": 100, "completion_tokens": 50})
        usage = budget.get_daily_usage()
        assert usage["total_tokens"] == 150


def test_legacy_gate_monthly():
    gate = _load_module("legacy_gate", _ROOT / "cloud-stubs" / "legacy_gate.py")
    future = datetime.now(timezone.utc) + timedelta(days=10)
    assert gate.legacy_zip_enabled(plan_code="monthly", expires_at=future) is True
    assert gate.legacy_zip_enabled(plan_code="insight_pro_monthly", expires_at=future) is False
