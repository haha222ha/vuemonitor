#!/usr/bin/env python3
# AIGC START
"""
每日小红书情报单篇生成（无 Day01~Day10）
读取 trend / opportunity / risk 库 → 输出 output/daily_xhs/{date}/
用法: python generate_daily_intel.py [--date 2026-05-25]
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # AI互联网信息量化
DB_DIR = ROOT / "商业情报中转站" / "database"
OUT_ROOT = Path(__file__).resolve().parent / "daily_xhs"
LOG_FILE = OUT_ROOT / "publish_log.json"

BANNED_PATTERN = re.compile(
    r"AI副业|网络兼职|兼职招聘|日结|在家赚钱|刷单|转账返利|押金|网赚|躺赚|轻松月入|月入\d+",
    re.I,
)

SAFE_TAGS = "#副业情报 #轻创业 #一人公司 #财富情报 #赛道观察 #避坑"


def load_json(name: str) -> dict:
    path = DB_DIR / name
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_publish_log() -> list[dict]:
    if not LOG_FILE.exists():
        return []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("entries", [])


def save_publish_log(entries: list[dict]) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump({"entries": entries[-60:]}, f, ensure_ascii=False, indent=2)


def sanitize(text: str) -> str:
    text = BANNED_PATTERN.sub("", text)
    text = text.replace("AI副业", "轻创业情报")
    return re.sub(r"\s+", " ", text).strip()


def pick_trend(trends: list, used_ids: set[str]) -> dict | None:
    priority = ["快速上升", "上升", "rising"]
    for p in priority:
        for t in trends:
            tid = t.get("id", t.get("trend_name", ""))
            if tid in used_ids:
                continue
            direction = t.get("direction", "")
            if p in str(direction):
                return t
    for t in trends:
        tid = t.get("id", t.get("trend_name", ""))
        if tid not in used_ids:
            return t
    return trends[0] if trends else None


def pick_opportunity(opps: list) -> dict | None:
    if not opps:
        return None
    for o in opps:
        if o.get("verdict") in ("推荐", "强烈推荐", "recommended"):
            return o
    return opps[0]


def pick_risk(risks: list) -> dict | None:
    eliminated = risks if isinstance(risks, list) else risks.get("eliminated", [])
    warnings = risks.get("warnings", []) if isinstance(risks, dict) else []
    pool = eliminated or warnings
    if not pool:
        return None
    return pool[0]


def build_title(trend: dict) -> str:
    name = sanitize(trend.get("trend_name", trend.get("title", "平台信号变化")))[:12]
    candidates = [
        f"这周{name}变了，别踩坑",
        f"3条轻创业信号，只看这条",
        f"{name}｜数据更新了",
    ]
    for c in candidates:
        if len(c) <= 20 and not BANNED_PATTERN.search(c):
            return c
    return candidates[0][:20]


def build_note(trend: dict, opp: dict | None, risk: dict | None) -> str:
    tname = sanitize(trend.get("trend_name", "趋势"))
    evidence = sanitize(trend.get("evidence", trend.get("actionable_insight", "")))[:120]
    insight = sanitize(trend.get("actionable_insight", ""))[:100]

    lines = [
        f"情报库刚更新：{tname} 这条信号值得单独记下来。",
        "",
        "📡 今日信号",
        f"· {tname}：{evidence or insight}",
        "",
    ]
    if opp:
        oname = sanitize(opp.get("name", opp.get("opportunity_name", "机会")))
        lines.extend(["💡 机会观察", f"· {oname}：值得列入观察清单，先小步验证再放大。", ""])
    if risk:
        rname = sanitize(risk.get("name", risk.get("risk_name", "风险")))
        reason = sanitize(risk.get("reason", risk.get("description", "")))[:80]
        lines.extend(["⚠️ 避坑", f"· {rname}：{reason or '供给过热或窗口收窄，慎跟风。'}", ""])

    lines.extend(
        [
            "完整周报与历史条目在会员站持续更新；需要的话看笔记下方商品（自动发授权码）。",
            "",
            "—— 副业财富情报 · 每日更新",
            "",
            SAFE_TAGS,
            "",
            "以上内容基于公开信息与趋势整理，不构成投资建议；副业投入需自行评估风险。",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()

    trend_db = load_json("trend_db.json")
    opp_db = load_json("opportunity_db.json")
    risk_db = load_json("risk_db.json")

    trends = trend_db.get("trends", [])
    opps = opp_db.get("opportunities", [])
    risks_raw = risk_db.get("eliminated", risk_db.get("risks", []))

    log = load_publish_log()
    used = {e.get("trend_id") for e in log[-7:]}

    trend = pick_trend(trends, used)
    if not trend:
        raise SystemExit("No trend data in trend_db.json")

    tid = trend.get("id", trend.get("trend_name", "unknown"))
    opp = pick_opportunity(opps)
    risk = pick_risk(risks_raw)

    day_dir = OUT_ROOT / args.date
    day_dir.mkdir(parents=True, exist_ok=True)

    title = build_title(trend)
    note = build_note(trend, opp, risk)

    (day_dir / "title.txt").write_text(title + "\n", encoding="utf-8")
    (day_dir / "note.md").write_text(note, encoding="utf-8")
    (day_dir / "pinned_comment.txt").write_text(
        "需要完整周报与情报库条目的，点笔记下方商品即可，付款后自动发授权码。\n",
        encoding="utf-8",
    )

    log.append(
        {
            "date": args.date,
            "trend_id": tid,
            "title": title,
            "cover_template": "A" if args.date[-1] in "13579" else "B",
        }
    )
    save_publish_log(log)

    print(f"[OK] {day_dir}")
    print(f"  title: {title}")
    print(f"  trend_id: {tid}")
    print("  下一步: 运行 regen_covers_v8.py 或手动生成 cover.png（目录体/数字判断体）")


if __name__ == "__main__":
    main()
# AIGC END
