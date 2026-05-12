"""
检查商品详情页script标签中是否包含完整时间数据
"""

import json
import re

# 读取HTML
with open('product_detail_full.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 提取所有script标签内容
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)

print(f'找到 {len(scripts)} 个script标签')

# 搜索包含时间的内容
for i, script in enumerate(scripts):
    # 搜索时间戳或日期格式
    if any(x in script for x in ['onShelf', 'on_shelf', 'shelfTime', 'shelf_time', 'createTime', 'create_time', 'publishTime', 'listTime']):
        print(f"\n{'='*60}")
        print(f"Script {i+1} 包含时间相关字段:")
        print(f"{'='*60}")
        # 打印包含关键词的上下文
        for keyword in ['onShelf', 'on_shelf', 'shelfTime', 'shelf_time', 'createTime', 'create_time', 'publishTime', 'listTime']:
            idx = script.find(keyword)
            if idx > 0:
                context = script[max(0, idx-100):idx+200]
                print(f"\n关键词: {keyword}")
                print(f"上下文: ...{context}...")

# 搜索所有script中的日期格式
print("\n\n🔍 搜索所有script中的日期格式...")
for i, script in enumerate(scripts):
    # 搜索 2024- 2025- 2026- 等日期格式
    dates = re.findall(r'202[4-6]-\d{2}-\d{2}', script)
    if dates:
        print(f"\nScript {i+1} 包含日期: {dates}")

# 搜索包含商品数据的JSON
print("\n\n🔍 搜索包含商品数据的JSON...")
for i, script in enumerate(scripts):
    if 'goodsId' in script or 'goods_id' in script or 'itemId' in script:
        print(f"\nScript {i+1} 包含商品数据 (长度: {len(script)})")
        if len(script) < 5000:
            print(script[:2000])
