"""
AI决策工具工厂 · 批处理总控 V2.0
一条命令：从JSON → 灌装HTML → 封面PNG → PDF → 打包导出

用法: python 批处理.py <json_file_or_batch_id>
示例: python 批处理.py B20260522001
      python 批处理.py "考研决策_10个.json"
"""

import sys, os
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

# 确保能import同目录脚本
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from batch_fill import batch_fill
from batch_covers import generate_covers
from batch_pdf import generate_pdfs
from batch_export import export_batch


def pipeline(batch_ref: str):
    """五步流水线"""
    print("=" * 60)
    print("  AI决策工具工厂 · 批处理流水线 V2.0")
    print("=" * 60)

    # Step 1: 灌装
    print("\n📝 [1/4] 灌装HTML...")
    manifest = batch_fill(batch_ref)
    batch_id = manifest["batch_id"]

    # Step 2: 封面
    print("\n🎨 [2/4] 生成封面...")
    try:
        generate_covers(batch_id)
    except Exception as e:
        print(f"  ⚠️ 封面生成失败（可跳过）: {e}")

    # Step 3: PDF
    print("\n📄 [3/4] 导出PDF...")
    try:
        generate_pdfs(batch_id)
    except Exception as e:
        print(f"  ⚠️ PDF生成失败（可跳过）: {e}")

    # Step 4: 打包导出
    print("\n📦 [4/4] 打包导出...")
    try:
        zip_path = export_batch(batch_id)
    except Exception as e:
        print(f"  ⚠️ 打包失败: {e}")
        zip_path = None

    # 总结
    print("\n" + "=" * 60)
    print(f"  ✅ 批次 {batch_id} 处理完成！")
    print(f"  📂 输出目录: output/{batch_id}/")
    if zip_path:
        print(f"  📦 打包文件: {zip_path}")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python 批处理.py <json_file_or_batch_id>")
        print("")
        print("三步走完整流程：")
        print("  1. 将万能产品生成器.txt提示词发给AI → 获得产品设计JSON")
        print("  2. 将JSON保存为 archive/B{日期}{序号}.json")
        print("  3. python 批处理.py B{日期}{序号}")
        print("")
        print("结果在 output/{batch_id}/export/ 下")
        sys.exit(1)

    pipeline(sys.argv[1])