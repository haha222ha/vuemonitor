# -*- coding: utf-8 -*-
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.compliance_gate import ComplianceViolation, assert_publishable


def test_pass_clean_report():
    metrics = {"category": "小学教辅", "growth_rate_pct": 42, "competition_index": 18}
    report = {"executive_summary": "趋势向好", "action_plan": {"enter": True}}
    html = "<html><body><p>AI 市场情报</p></body></html>"
    assert_publishable(metrics, report, html)


def test_block_goods_id():
    try:
        assert_publishable({"goods_id": "123"}, {}, "<html></html>")
        raise AssertionError("should fail")
    except ComplianceViolation as e:
        assert e.field == "goods_id"


def test_block_html_report_data():
    try:
        assert_publishable({}, {}, "<script>var REPORT_DATA = {}</script>")
        raise AssertionError("should fail")
    except ComplianceViolation:
        pass


def test_block_k_anonymity():
    try:
        assert_publishable({"category": "测试", "sample_size": 2}, {"executive_summary": "ok"}, "<html></html>", k_min=5)
        raise AssertionError("should fail")
    except ComplianceViolation as e:
        assert e.rule == "k_anonymity"


if __name__ == "__main__":
    test_pass_clean_report()
    test_block_goods_id()
    test_block_html_report_data()
    test_block_k_anonymity()
    print("compliance_gate tests OK")
