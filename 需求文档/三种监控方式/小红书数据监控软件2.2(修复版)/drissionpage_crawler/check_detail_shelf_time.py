"""
检查商品详情页是否包含完整上架时间
"""

import json
import re
from DrissionPage import ChromiumPage, ChromiumOptions
import time

def check_product_detail_for_shelf_time():
    co = ChromiumOptions()
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--no-sandbox')
    co.auto_port()
    
    page = ChromiumPage(addr_or_opts=co)
    
    try:
        product_url = 'https://www.xiaohongshu.com/goods-detail/69b68cb01b6b3f0001385bc6'
        print(f"🌐 打开商品: {product_url}")
        page.get(product_url)
        time.sleep(5)
        
        # 滚动加载完整内容
        page.scroll.to_bottom()
        time.sleep(2)
        page.scroll.to_top()
        
        # 获取完整HTML
        html = page.html
        
        # 搜索时间相关字段
        print("\n🔍 搜索时间相关字段...")
        
        patterns = [
            (r'"onShelfTime"\s*:\s*"?([^",}]+)"?', 'onShelfTime'),
            (r'"on_shelf_time"\s*:\s*"?([^",}]+)"?', 'on_shelf_time'),
            (r'"shelfTime"\s*:\s*"?([^",}]+)"?', 'shelfTime'),
            (r'"shelf_time"\s*:\s*"?([^",}]+)"?', 'shelf_time'),
            (r'"createTime"\s*:\s*"?([^",}]+)"?', 'createTime'),
            (r'"create_time"\s*:\s*"?([^",}]+)"?', 'create_time'),
            (r'"publishTime"\s*:\s*"?([^",}]+)"?', 'publishTime'),
            (r'"publish_time"\s*:\s*"?([^",}]+)"?', 'publish_time'),
            (r'"listTime"\s*:\s*"?([^",}]+)"?', 'listTime'),
            (r'"list_time"\s*:\s*"?([^",}]+)"?', 'list_time'),
        ]
        
        for pattern, name in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                print(f"\n✅ 找到 {name}:")
                for i, match in enumerate(matches[:3], 1):
                    print(f"  {i}. {match}")
        
        # 搜索包含时间的JSON块
        print("\n🔍 搜索包含时间的JSON数据块...")
        time_patterns = ['2024-', '2025-', '2026-', '2023-']
        for tp in time_patterns:
            idx = html.find(tp)
            if idx > 0:
                context = html[max(0, idx-100):idx+100]
                print(f"\n找到 '{tp}' 上下文:")
                print(f"  ...{context}...")
        
        # 保存HTML
        with open('product_detail_full.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n💾 HTML已保存: product_detail_full.html")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        page.quit()

if __name__ == '__main__':
    check_product_detail_for_shelf_time()
