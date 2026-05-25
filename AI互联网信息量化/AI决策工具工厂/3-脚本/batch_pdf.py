"""
批量PDF导出脚本
将灌装好的HTML → Playwright渲染 → PDF

用法: python batch_pdf.py <batch_id>
示例: python batch_pdf.py B20260522001
依赖: pip install playwright && playwright install chromium
"""

import json, os, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"


def generate_pdfs(batch_id: str):
    """生成批次中所有产品的PDF"""
    batch_dir = OUTPUT_DIR / batch_id
    html_dir = batch_dir / "html"
    pdf_dir = batch_dir / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    html_files = sorted(html_dir.glob("*.html"))
    if not html_files:
        print("❌ 没有找到HTML文件，请先运行 batch_fill.py")
        return

    print(f"📄 生成PDF: {batch_id} | HTML文件数: {len(html_files)}")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ 需要安装playwright: pip install playwright && playwright install chromium")
        return

    success = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        for html_file in html_files:
            try:
                # 用file://协议加载HTML
                file_url = html_file.as_uri()
                page.goto(file_url, wait_until="networkidle", timeout=15000)
                page.wait_for_timeout(500)

                pdf_path = pdf_dir / f"{html_file.stem}.pdf"
                page.pdf(
                    path=str(pdf_path),
                    format="A4",
                    print_background=True,
                    margin={"top": "10mm", "bottom": "10mm", "left": "8mm", "right": "8mm"},
                )

                size = os.path.getsize(pdf_path)
                print(f"  ✅ {html_file.stem}: {pdf_path.name} ({size//1024}KB)")
                success += 1

            except Exception as e:
                print(f"  ❌ {html_file.stem}: {e}")

        browser.close()

    print(f"\n🎉 PDF生成完成: {success}/{len(html_files)} → {pdf_dir}")
    return success


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python batch_pdf.py <batch_id>")
        sys.exit(1)

    generate_pdfs(sys.argv[1])