"""
检查商品卡片 data-eaglet 中是否包含 on_shelf_time 时间戳
"""

import json
from html import unescape
from DrissionPage import ChromiumPage, ChromiumOptions
import time

def check_eaglet_for_shelf_time():
    co = ChromiumOptions()
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--no-sandbox')
    co.auto_port()
    
    page = ChromiumPage(addr_or_opts=co)
    
    try:
        store_url = 'https://www.xiaohongshu.com/vendor/68c59952c095d90015b6c758'
        print(f"🌐 打开店铺: {store_url}")
        page.get(store_url)
        time.sleep(5)
        
        # 点击商品标签
        try:
            product_tab = page.ele('text:商品', timeout=3)
            if product_tab:
                product_tab.click()
                time.sleep(3)
        except:
            pass
        
        # 滚动加载
        for i in range(3):
            page.scroll.down(400)
            time.sleep(1)
        
        # 查找所有商品卡片
        eaglet_elems = page.eles('@data-eaglet')
        print(f"\n找到 {len(eaglet_elems)} 个 data-eaglet 元素")
        
        # 检查前5个商品卡片的完整JSON
        for idx, elem in enumerate(eaglet_elems[:5], 1):
            eaglet_str = elem.attr('data-eaglet')
            if eaglet_str and 'mallGoodsTarget' in eaglet_str:
                try:
                    decoded = unescape(eaglet_str)
                    data = json.loads(decoded)
                    
                    print(f"\n{'='*60}")
                    print(f"商品 {idx} - 完整 data-eaglet JSON:")
                    print(f"{'='*60}")
                    print(json.dumps(data, ensure_ascii=False, indent=2))
                    
                    # 搜索时间相关字段
                    print(f"\n🔍 搜索时间相关字段...")
                    for key in ['onShelfTime', 'on_shelf_time', 'shelfTime', 'shelf_time', 'createTime', 'create_time', 'time', 'timestamp']:
                        if key.lower() in json.dumps(data, ensure_ascii=False).lower():
                            print(f"  ✅ 找到字段: {key}")
                    
                except Exception as e:
                    print(f"JSON解析错误: {e}")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
    finally:
        page.quit()

if __name__ == '__main__':
    check_eaglet_for_shelf_time()
