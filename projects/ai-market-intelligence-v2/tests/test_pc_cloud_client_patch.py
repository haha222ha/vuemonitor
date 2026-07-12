"""PC-1 cloud_client 补丁 — resolve_menu_flags / insight_view_url 单元测试。"""
from __future__ import annotations

import sys
from pathlib import Path

_STUB = Path(__file__).resolve().parents[1] / "cloud-stubs"
if str(_STUB) not in sys.path:
    sys.path.insert(0, str(_STUB))

import pc_cloud_client_v2_patch as pc  # noqa: E402


def test_resolve_menu_flags_insight_only():
    profile = {
        "legacy_zip_enabled": False,
        "insight_enabled": True,
        "portal_route": "insight_only",
        "entitlements": {"plan_code": "insight_pro"},
    }
    flags = pc.resolve_menu_flags(profile)
    assert flags["show_legacy_zip"] is False
    assert flags["show_insight"] is True
    assert flags["default_section"] == "insight"


def test_resolve_menu_flags_legacy_monthly():
    profile = {
        "legacy_zip_enabled": True,
        "insight_enabled": False,
        "portal_route": "legacy_only",
    }
    flags = pc.resolve_menu_flags(profile)
    assert flags["show_legacy_zip"] is True
    assert flags["show_insight"] is False
    assert flags["default_section"] == "legacy"


def test_resolve_menu_flags_dual_preview():
    profile = {
        "legacy_zip_enabled": True,
        "insight_enabled": True,
        "portal_route": "dual",
        "entitlements": {"insight_preview": True},
    }
    flags = pc.resolve_menu_flags(profile)
    assert flags["show_legacy_zip"] is True
    assert flags["show_insight"] is True


def test_insight_view_url():
    pc._bind_cloud_client(
        lambda *a, **k: (200, {}),
        lambda: "tok123",
        lambda: "https://monitor.xhs365.cn",
    )
    url = pc.insight_view_url("2026-07-12", "女装")
    assert url.startswith("https://monitor.xhs365.cn/api/v1/member/insight/2026-07-12/")
    assert "access_token=tok123" in url
