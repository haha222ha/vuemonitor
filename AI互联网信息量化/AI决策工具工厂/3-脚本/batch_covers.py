"""
批量封面生成脚本
读取cover_template.html → Playwright渲染 → 输出封面PNG

用法: python batch_covers.py <batch_id>
示例: python batch_covers.py B20260522001
依赖: pip install playwright && playwright install chromium
"""

import json, os, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
MATERIAL_DIR = BASE_DIR / "4-素材库"


def load_colors():
    with open(MATERIAL_DIR / "colors.json", "r", encoding="utf-8") as f:
        return json.load(f)


def generate_covers(batch_id: str):
    """生成批次中所有产品的封面PNG"""
    batch_dir = OUTPUT_DIR / batch_id
    manifest_path = batch_dir / "manifest.json"

    if not manifest_path.exists():
        print(f"❌ 找不到manifest: {manifest_path}")
        print("   请先运行 batch_fill.py")
        return

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    with open(MATERIAL_DIR / "cover_template.html", "r", encoding="utf-8") as f:
        cover_template = f.read()

    colors = load_colors()
    scheme_key = manifest.get("color_scheme", "education")
    scheme = colors.get(scheme_key, colors["education"])

    covers_dir = batch_dir / "covers"
    covers_dir.mkdir(parents=True, exist_ok=True)

    products = manifest["products"]
    print(f"🎨 生成封面: {batch_id} | 产品数: {len(products)}")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ 需要安装playwright: pip install playwright && playwright install chromium")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1440})

        for prod in products:
            html = cover_template

            # 替换封面变量
            html = html.replace("{{BG_COLOR}}", scheme["bg"])
            html = html.replace("{{ACCENT_COLOR}}", scheme["accent"])
            html = html.replace("{{PRIMARY_COLOR}}", scheme["primary"])
            html = html.replace("{{CATEGORY_EMOJI}}", scheme.get("emoji", "📋"))
            html = html.replace("{{COVER_TITLE}}", prod["title"])
            html = html.replace("{{COVER_SUBTITLE}}", prod.get("subtitle", manifest.get("category", "")))
            html = html.replace("{{COVER_HOOK}}", prod.get("hook", "5分钟帮你做出最优决策"))
            html = html.replace("{{PRODUCT_ID}}", prod["product_id"])

            # 设置HTML并截图
            page.set_content(html, wait_until="networkidle")
            page.wait_for_timeout(500)  # 等待字体渲染

            output_path = covers_dir / f"{prod['product_id']}_cover.png"
            page.screenshot(path=str(output_path), full_page=False)

            # 验证
            size = os.path.getsize(output_path)
            print(f"  ✅ {prod['product_id']}: {output_path.name} ({size//1024}KB)")

        browser.close()

    # 输出封面manifest
    cover_files = sorted(covers_dir.glob("*.png"))
    cover_manifest = {
        "batch_id": batch_id,
        "total": len(cover_files),
        "files": [{"name": f.name, "product_id": f.stem.replace("_cover", "")} for f in cover_files],
    }

    cm_path = covers_dir / "cover_manifest.json"
    with open(cm_path, "w", encoding="utf-8") as f:
        json.dump(cover_manifest, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 封面生成完成: {len(cover_files)}张 → {covers_dir}")
    return cover_manifest


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python batch_covers.py <batch_id>")
        sys.exit(1)

    generate_covers(sys.argv[1])