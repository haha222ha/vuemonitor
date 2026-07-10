# -*- coding: utf-8 -*-
"""从全量选品报告生成「免费体验包」：含 24h 加购指数(acc>0)，虚拟/实体分轨，总量≤3000。"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import zipfile
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from cloud_deploy.scripts.bootstrap_env import bootstrap

bootstrap()

from cloud_deploy.reporting.constants import COL, REPORT_COLUMNS, item_at
from cloud_deploy.reporting.data_js_builder import build_report_payload, resolve_report_assets_dir
from cloud_deploy.reporting.report_charts import build_charts_and_tops

MAX_ITEMS = 3000
MAX_PER_TRACK = 1500
MIN_ACC = 0.01

TRIAL_UPSELL = {
    "custom_keyword_member_price": 9.9,
    "custom_keyword_guest_price": 29.9,
    "custom_keyword_unit": "次",
    "pc_client_paid_only": True,
    "contact_hint": "开通会员后在 PC 端「使用说明」提交定制词库需求，或联系会员客服",
}

TRIAL_DISCLAIMER = {
    "title": "免费体验包 · 合规使用须知",
    "version": "2026-07",
    "lines": [
        "本体验包为基于公开页面信息与系统计算的选品数据样本，仅供研究参考，不构成投资建议或收益承诺。",
        "体验包限量展示，数据存在延迟与误差；「24h加购指数」为系统按扫描间隔推算的参考指标，非平台官方加购数。",
        "免费用户可通过网页预览/下载本体验包；完整日报/周报/月报及 PC 端选品分析工具仅向付费会员开放。",
        "禁止将本包数据批量转售、公开传播或用于侵权抄款、虚假宣传等违法违规用途。",
        "继续使用即视为已阅读并理解上述条款。",
    ],
}

TRIAL_SELECTION_GUIDE = {
    "title": "体验包选品指引（高转化版）",
    "principle": "优先看「24h加购指数 + 真实增量」双高商品；虚拟/实体分轨对比，勿混排。",
    "workflow": [
        {"step": "1", "name": "选赛道", "text": "左侧切换「虚拟商品 / 实体商品」。虚拟=交付轻、周转快；实体=需关注供应链。"},
        {"step": "2", "name": "看加购", "text": "卡片「24h加购指数」越高，短周期购买意向越强；配合真实增量验证是否真在卖。"},
        {"step": "3", "name": "验动销", "text": "真实增量≥5 且 pool 为 ACCEL/BURST 优先跟进；粉销比≤0.05 为低粉高销信号。"},
        {"step": "4", "name": "要完整", "text": "体验包仅样本；开通会员获取每日全量报告 + PC 监控工具。"},
    ],
    "upsell": [
        "会员定制词库：¥9.9/次（定向采集，稳定产出）",
        "非会员定制词库：¥29.9/次",
        "PC 选品分析工具：仅付费会员可用",
    ],
}


def load_report_data(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()
    if raw.startswith("var REPORT_DATA"):
        raw = raw.split("=", 1)[1].strip()
        if raw.endswith(";"):
            raw = raw[:-1]
    return json.loads(raw)


def _acc_score(row: list) -> float:
    acc = float(item_at(row, "acc", 0) or 0)
    if acc > 0:
        return acc
    v1h = float(item_at(row, "v1h", 0) or 0)
    if v1h > 0:
        return v1h * 24.0
    return 0.0


def filter_trial_items(items: list) -> tuple[list, list]:
    scored: list[tuple[float, list]] = []
    for row in items:
        score = _acc_score(row)
        if score < MIN_ACC:
            continue
        scored.append((score, row))
    scored.sort(key=lambda x: (-x[0], -float(item_at(x[1], "actual_v1d", 0) or 0)))
    virtual: list = []
    physical: list = []
    for _score, row in scored:
        if int(item_at(row, "is_virtual", 0) or 0) == 1:
            virtual.append(row)
        else:
            physical.append(row)
    virtual = virtual[:MAX_PER_TRACK]
    physical = physical[:MAX_PER_TRACK]
    merged = virtual + physical
    if len(merged) > MAX_ITEMS:
        merged = merged[:MAX_ITEMS]
    return merged, virtual, physical


def build_trial_payload(source: dict, report_date: str) -> dict:
    items, virtual_rows, physical_rows = filter_trial_items(source.get("items") or [])
    if not items:
        raise RuntimeError("无 acc>0 的商品，请换一份更新的全量报告")
    payload = build_report_payload(
        items,
        report_date,
        scope="trial",
        scope_label=f"体验包：24h加购指数>{MIN_ACC}；虚拟{len(virtual_rows)}+实体{len(physical_rows)}；总量≤{MAX_ITEMS}",
        source="trial_experience_pack",
    )
    meta = payload["meta"]
    meta["pack_type"] = "trial_experience"
    meta["trial"] = True
    meta["max_items"] = MAX_ITEMS
    meta["acc_filter_min"] = MIN_ACC
    meta["virtual_count"] = len(virtual_rows)
    meta["physical_count"] = len(physical_rows)
    meta["disclaimer"] = TRIAL_DISCLAIMER
    meta["upsell"] = TRIAL_UPSELL
    meta["title"] = "选品报告 · 免费体验包"
    meta["subtitle"] = "24h加购指数精选 · 虚拟/实体分轨 · 明亮科技风预览"
    charts, top_keywords, top_stores = build_charts_and_tops(items)
    payload["charts"] = charts
    payload["top_keywords"] = top_keywords
    payload["top_stores"] = top_stores
    payload["selection_guide"] = TRIAL_SELECTION_GUIDE
    acc_guide = {
        "field": "24h加购指数",
        "key": "acc",
        "formula": "短周期动销加权推算（v1h×24 等）",
        "desc": "反映近 24 小时购买意向强度的参考指数，越高表示短周期加购/动销越活跃。",
        "reference": "体验包按此指数降序精选；请配合真实增量交叉验证。",
    }
    guides = list(payload.get("field_guide") or [])
    if not any(g.get("key") == "acc" for g in guides):
        guides.insert(8, acc_guide)
    payload["field_guide"] = guides
    return payload


def write_trial_dir(output_dir: str, payload: dict, assets_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    js_path = os.path.join(output_dir, "data.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("var REPORT_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        f.write(";\n")
    bundle = (
        "index_trial.html",
        "trial_theme.css",
        "report_theme.js",
    )
    for name in bundle:
        src = os.path.join(assets_dir, name)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(output_dir, name))
    readme = os.path.join(output_dir, "README.txt")
    with open(readme, "w", encoding="utf-8") as f:
        f.write(
            "选品报告 · 免费体验包\n"
            f"生成时间：{datetime.now():%Y-%m-%d %H:%M:%S}\n"
            f"商品数：{payload['meta'].get('count', 0)}（上限 {MAX_ITEMS}）\n"
            "打开 index_trial.html 预览（推荐 Chrome）。\n"
            "完整功能与 PC 端工具需开通付费会员。\n"
        )


def zip_dir(src_dir: str, zip_path: str) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(src_dir):
            for name in files:
                full = os.path.join(root, name)
                arc = os.path.relpath(full, src_dir).replace("\\", "/")
                zf.write(full, arc)


def main() -> int:
    parser = argparse.ArgumentParser(description="生成选品免费体验包")
    parser.add_argument(
        "--source",
        default=os.path.join(ROOT, "server_sync_pack", "historical_reports", "全量0619", "data.js"),
        help="源全量报告 data.js",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(ROOT, "cloud_deploy", "assets", "trial_experience"),
    )
    parser.add_argument("--date", default="", help="报告日期 YYYY-MM-DD，默认同源 meta")
    args = parser.parse_args()
    if not os.path.isfile(args.source):
        print(f"源文件不存在: {args.source}", file=sys.stderr)
        return 1
    source = load_report_data(args.source)
    report_date = (args.date or (source.get("meta") or {}).get("date") or datetime.now().strftime("%Y-%m-%d"))[:10]
    payload = build_trial_payload(source, report_date)
    assets_dir = resolve_report_assets_dir()
    write_trial_dir(args.output_dir, payload, assets_dir)
    zip_path = args.output_dir.rstrip("/\\") + ".zip"
    zip_dir(args.output_dir, zip_path)
    meta = payload["meta"]
    print(f"OK 体验包已生成: {args.output_dir}")
    print(f"   商品 {meta.get('count')}（虚拟 {meta.get('virtual_count')} / 实体 {meta.get('physical_count')}）")
    print(f"   ZIP: {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
