"""
批量灌装脚本 V2.0
读取AI生成的JSON → 填充母版模板 → 输出完整HTML

用法: python batch_fill.py <json_file_or_batch_id>
示例: python batch_fill.py B20260522001.json
      python batch_fill.py B20260522001  (自动查找archive/下对应文件)
"""

import json, os, re, sys, shutil
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

# ===== 配置 =====
BASE_DIR = Path(__file__).parent.parent
TEMPLATE_DIR = BASE_DIR / "1-母版模板"
ARCHIVE_DIR = BASE_DIR / "archive"
OUTPUT_DIR  = BASE_DIR / "output"
MATERIAL_DIR = BASE_DIR / "4-素材库"

TEMPLATE_MAP = {
    "self_assess":   "template_self_assess.html",
    "compare":       "template_compare.html",
    "checklist":     "template_checklist.html",
    "info_guide":    "template_info_guide.html",
    "method":        "template_info_guide.html",       # 暂映射到info_guide
    "decision_tree": "template_info_guide.html",       # 暂映射到info_guide
    "quick_lookup":  "template_info_guide.html",       # 暂映射到info_guide
    "template_pack": "template_info_guide.html",       # 暂映射到info_guide
}


def load_colors():
    """加载配色方案"""
    with open(MATERIAL_DIR / "colors.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_json(batch_ref: str):
    """加载批次JSON"""
    # 尝试直接路径
    json_path = Path(batch_ref)
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # 尝试archive目录
    json_path = ARCHIVE_DIR / batch_ref
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # 尝试加.json扩展名
    json_path = ARCHIVE_DIR / (batch_ref + ".json")
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    raise FileNotFoundError(f"找不到批次文件: {batch_ref}")


def fill_self_assess(product: dict, template: str, colors: dict) -> str:
    """填充自评打分表"""
    dims = product["dimensions"]
    tiers = product["tiers"]

    html = template
    html = html.replace("{{DIM_1_NAME}}", dims[0]["name"])
    html = html.replace("{{DIM_1_WEIGHT}}", str(dims[0]["weight"]))
    html = html.replace("{{DIM_1_CRITERIA}}", dims[0]["criteria"])
    html = html.replace("{{DIM_2_NAME}}", dims[1]["name"])
    html = html.replace("{{DIM_2_WEIGHT}}", str(dims[1]["weight"]))
    html = html.replace("{{DIM_2_CRITERIA}}", dims[1]["criteria"])
    html = html.replace("{{DIM_3_NAME}}", dims[2]["name"])
    html = html.replace("{{DIM_3_WEIGHT}}", str(dims[2]["weight"]))
    html = html.replace("{{DIM_3_CRITERIA}}", dims[2]["criteria"])
    html = html.replace("{{DIM_4_NAME}}", dims[3]["name"])
    html = html.replace("{{DIM_4_WEIGHT}}", str(dims[3]["weight"]))
    html = html.replace("{{DIM_4_CRITERIA}}", dims[3]["criteria"])
    html = html.replace("{{DIM_5_NAME}}", dims[4]["name"])
    html = html.replace("{{DIM_5_WEIGHT}}", str(dims[4]["weight"]))
    html = html.replace("{{DIM_5_CRITERIA}}", dims[4]["criteria"])

    html = html.replace("{{TIER_HIGH_RANGE}}", tiers[0]["range"])
    html = html.replace("{{TIER_HIGH_VERDICT}}", tiers[0]["verdict"])
    html = html.replace("{{TIER_HIGH_ACTION}}", tiers[0]["action"])
    html = html.replace("{{TIER_MID_RANGE}}", tiers[1]["range"])
    html = html.replace("{{TIER_MID_VERDICT}}", tiers[1]["verdict"])
    html = html.replace("{{TIER_MID_ACTION}}", tiers[1]["action"])
    html = html.replace("{{TIER_LOW_RANGE}}", tiers[2]["range"])
    html = html.replace("{{TIER_LOW_VERDICT}}", tiers[2]["verdict"])
    html = html.replace("{{TIER_LOW_ACTION}}", tiers[2]["action"])

    return html


def fill_compare(product: dict, template: str, colors: dict) -> str:
    """填充对比表"""
    dims = product["dimensions"]
    html = template

    for i in range(5):
        html = html.replace(f"{{{{DIM_{i+1}_NAME}}}}", dims[i]["name"])
        html = html.replace(f"{{{{DIM_{i+1}_WEIGHT}}}}", str(dims[i]["weight"]))
        html = html.replace(f"{{{{DIM_{i+1}_CRITERIA}}}}", dims[i]["criteria"])

    return html


def fill_checklist(product: dict, template: str, colors: dict) -> str:
    """填充检查清单"""
    items = product.get("items", [])
    html = template

    for i in range(15):
        if i < len(items):
            val = items[i]["question"]
        else:
            val = f"{{{{ITEM_{i+1}}}}}"
        html = html.replace(f"{{{{ITEM_{i+1}}}}}", val)

    return html


def fill_info_guide(product: dict, template: str, colors: dict) -> str:
    """填充信息攻略"""
    sections = product.get("sections", [])
    html = template

    # Section 1: 概览表格
    if len(sections) >= 1:
        s1 = sections[0]
        html = html.replace("{{SECTION_1_TITLE}}", s1["title"])
        html = html.replace("{{SECTION_1_CONTENT}}", render_table(s1.get("data", []), colors))
    else:
        html = html.replace("{{SECTION_1_TITLE}}", "概览对比")
        html = html.replace("{{SECTION_1_CONTENT}}", "<p>暂无数据</p>")

    # Section 2: 分人群推荐
    if len(sections) >= 2:
        s2 = sections[2] if len(sections) >= 3 and sections[1]["content_type"] == "comparison_table" else sections[1]
        html = html.replace("{{SECTION_2_TITLE}}", s2["title"])
        html = html.replace("{{SECTION_2_CONTENT}}", render_personas(s2.get("data", [])))
    else:
        html = html.replace("{{SECTION_2_TITLE}}", "分人群推荐")
        html = html.replace("{{SECTION_2_CONTENT}}", "<p>暂无数据</p>")

    # Section 3: 避坑清单
    if len(sections) >= 3:
        s3 = sections[2]
        html = html.replace("{{SECTION_3_TITLE}}", s3["title"])
        html = html.replace("{{SECTION_3_CONTENT}}", render_tips(s3.get("data", [])))
    else:
        html = html.replace("{{SECTION_3_TITLE}}", "避坑要点")
        html = html.replace("{{SECTION_3_CONTENT}}", "<p>暂无数据</p>")

    return html


def render_table(data: list, colors: dict) -> str:
    """渲染对比表格"""
    if not data or len(data) < 2:
        return "<p>暂无数据</p>"

    headers = data[0] if isinstance(data[0], list) else list(data[0].keys())
    rows = data[1:] if isinstance(data[0], list) else data

    thead = "<tr>" + "".join(f'<th>{h}</th>' for h in headers) + "</tr>"
    tbody = ""
    for row in rows:
        if isinstance(row, dict):
            vals = [str(row.get(h, "")) for h in headers]
        else:
            vals = [str(v) for v in row]
        tbody += "<tr>" + "".join(f'<td>{v}</td>' for v in vals) + "</tr>"

    return f'<table class="info-table"><thead>{thead}</thead><tbody>{tbody}</tbody></table>'


def render_personas(data: list) -> str:
    """渲染分人群推荐卡片"""
    if not data:
        return "<p>暂无数据</p>"

    emojis = ["👤", "👥", "🧑‍💻", "👩‍🎓"]
    cards = ""
    for i, p in enumerate(data[:4]):
        if isinstance(p, dict):
            icon = emojis[i % len(emojis)]
            name = p.get("persona", p.get("name", ""))
            rec = p.get("recommendation", p.get("rec", ""))
            reason = p.get("reason", "")
        else:
            icon = emojis[i % len(emojis)]
            name = str(p)
            rec = ""
            reason = ""

        cards += f'''
        <div class="persona-card">
          <div class="persona-icon">{icon}</div>
          <div class="persona-name">{name}</div>
          <div class="persona-rec">{rec}</div>
          <div class="persona-reason">{reason}</div>
        </div>'''

    return cards


def render_tips(data: list) -> str:
    """渲染避坑清单"""
    if not data:
        return "<p>暂无数据</p>"

    tips = ""
    for i, tip in enumerate(data, 1):
        if isinstance(tip, dict):
            text = tip.get("tip", tip.get("content", str(tip)))
        else:
            text = str(tip)
        tips += f'<div class="tip-item"><div class="tip-num">{i}</div><span>{text}</span></div>'

    return tips


def apply_colors(html: str, product: dict, batch: dict, colors: dict) -> str:
    """应用配色方案到HTML"""
    scheme_key = batch.get("color_scheme", "education")
    scheme = colors.get(scheme_key, colors["education"])

    html = html.replace("{{PRIMARY_COLOR}}", scheme["primary"])
    html = html.replace("{{ACCENT_COLOR}}", scheme["accent"])
    html = html.replace("{{BG_COLOR}}", scheme["bg"])
    html = html.replace("{{TIER_HIGH_COLOR}}", scheme["tiers"]["high"])
    html = html.replace("{{TIER_MID_COLOR}}", scheme["tiers"]["mid"])
    html = html.replace("{{TIER_LOW_COLOR}}", scheme["tiers"]["low"])

    return html


def apply_meta(html: str, product: dict, batch: dict) -> str:
    """应用元数据（标题/副标题等）"""
    batch_id = batch["batch_id"]
    product_id = f'{batch_id}-{product["id"]}'

    html = html.replace("{{TITLE}}", product["title"])
    html = html.replace("{{SUBTITLE}}", product.get("subtitle", ""))
    html = html.replace("{{CATEGORY}}", batch["category"])
    html = html.replace("{{PRICE}}", str(product.get("price", "9.9")))
    html = html.replace("{{PRODUCT_ID}}", product_id)

    return html


def batch_fill(batch_ref: str):
    """主函数：批量灌装"""
    batch = load_json(batch_ref)
    colors = load_colors()

    batch_id = batch["batch_id"]
    products = batch["products"]
    category = batch["category"]

    print(f"📦 批次: {batch_id} | 品类: {category} | 产品数: {len(products)}")

    # 创建输出目录
    batch_dir = OUTPUT_DIR / batch_id
    html_dir = batch_dir / "html"
    html_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for product in products:
        product_type = product["type"]
        product_id = product["id"]
        template_file = TEMPLATE_MAP.get(product_type)

        if not template_file:
            print(f"  ⚠️  {product_id}: 未知类型 {product_type}，跳过")
            continue

        template_path = TEMPLATE_DIR / template_file
        if not template_path.exists():
            print(f"  ⚠️  {product_id}: 模板文件不存在 {template_file}，跳过")
            continue

        # 读取母版
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()

        # 填充内容
        fill_funcs = {
            "self_assess": fill_self_assess,
            "compare": fill_compare,
            "checklist": fill_checklist,
            "info_guide": fill_info_guide,
            "method": fill_info_guide,
            "decision_tree": fill_info_guide,
            "quick_lookup": fill_info_guide,
            "template_pack": fill_info_guide,
        }

        fill_func = fill_funcs.get(product_type)
        if fill_func:
            html = fill_func(product, template, colors)

        # 应用配色和元数据
        html = apply_colors(html, product, batch, colors)
        html = apply_meta(html, product, batch)

        # 输出
        output_path = html_dir / f"{product_id}.html"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        results.append({
            "product_id": product_id,
            "type": product_type,
            "title": product["title"],
            "path": str(output_path),
        })

        print(f"  ✅ {product_id}: {product['title']} → {output_path.name}")

    # 输出manifest
    manifest = {
        "batch_id": batch_id,
        "category": category,
        "color_scheme": batch.get("color_scheme", "education"),
        "filled_at": f"{batch_id}",
        "products": results,
    }

    manifest_path = batch_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n📋 manifest已生成: {manifest_path}")
    print(f"🎉 灌装完成: {len(results)}/{len(products)} 个产品已生成")
    return manifest


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python batch_fill.py <json_file_or_batch_id>")
        print("示例: python batch_fill.py B20260522001.json")
        sys.exit(1)

    batch_fill(sys.argv[1])