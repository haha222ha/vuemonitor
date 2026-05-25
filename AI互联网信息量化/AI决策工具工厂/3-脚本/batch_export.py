"""
批量导出整理脚本
将HTML + PDF + 封面统一打包到export目录

用法: python batch_export.py <batch_id>
示例: python batch_export.py B20260522001
"""

import json, os, sys, shutil, zipfile
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"


def export_batch(batch_id: str, include_html: bool = True):
    """打包导出"""
    batch_dir = OUTPUT_DIR / batch_id
    export_dir = batch_dir / "export"
    export_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = batch_dir / "manifest.json"
    if not manifest_path.exists():
        print("❌ 找不到manifest，请先完成灌装")
        return

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    print(f"📦 导出批次: {batch_id}")

    files_to_zip = []

    # 复制PDF
    pdf_dir = batch_dir / "pdf"
    if pdf_dir.exists():
        for pdf in pdf_dir.glob("*.pdf"):
            dest = export_dir / pdf.name
            shutil.copy2(pdf, dest)
            files_to_zip.append(dest)
            print(f"  ✅ PDF: {pdf.name}")

    # 复制封面
    covers_dir = batch_dir / "covers"
    if covers_dir.exists():
        for png in covers_dir.glob("*.png"):
            if "manifest" not in png.name:
                dest = export_dir / png.name
                shutil.copy2(png, dest)
                files_to_zip.append(dest)
                print(f"  ✅ 封面: {png.name}")

    # 可选HTML
    if include_html:
        html_dir = batch_dir / "html"
        if html_dir.exists():
            for html in html_dir.glob("*.html"):
                dest = export_dir / html.name
                shutil.copy2(html, dest)
                files_to_zip.append(dest)
                # 不逐个打印以减少输出

    # 生成导出清单
    export_manifest = {
        "batch_id": batch_id,
        "category": manifest.get("category", ""),
        "products_count": len(manifest.get("products", [])),
        "exported_at": batch_id,
    }

    emp_path = export_dir / "export_manifest.json"
    with open(emp_path, "w", encoding="utf-8") as f:
        json.dump(export_manifest, f, ensure_ascii=False, indent=2)

    # 打包ZIP
    zip_path = batch_dir / f"{batch_id}_export.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp in files_to_zip:
            zf.write(fp, fp.name)

    zip_size = os.path.getsize(zip_path)
    print(f"\n📦 ZIP打包: {zip_path.name} ({zip_size//1024}KB)")
    print(f"🎉 导出完成: {export_dir}")
    return str(zip_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python batch_export.py <batch_id>")
        sys.exit(1)

    export_batch(sys.argv[1])