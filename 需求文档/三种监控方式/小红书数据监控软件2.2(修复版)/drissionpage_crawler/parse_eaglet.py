"""
检查商品卡片 data-eaglet 中是否包含 on_shelf_time 时间戳
"""

import json
import re
from html import unescape

# 读取HTML文件
with open('store_page_debug.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 查找所有 data-eaglet 属性
matches = re.findall(r'data-eaglet="([^"]*mallGoodsTarget[^"]*)"', html)
print(f'找到 {len(matches)} 个商品卡片')

# 检查前3个商品卡片的完整JSON
for idx, m in enumerate(matches[:3], 1):
    try:
        decoded = unescape(m)
        data = json.loads(decoded)
        
        print(f"\n{'='*60}")
        print(f"商品 {idx} - 完整 data-eaglet JSON:")
        print(f"{'='*60}")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        
        # 搜索时间相关字段
        print(f"\n🔍 搜索时间相关字段...")
        json_str = json.dumps(data, ensure_ascii=False).lower()
        for key in ['onshelftime', 'on_shelf_time', 'shelftime', 'shelf_time', 'createtime', 'create_time', 'time', 'timestamp']:
            if key in json_str:
                print(f"  ✅ 找到字段: {key}")
        
    except Exception as e:
        print(f"JSON解析错误: {e}")
