"""
检查店铺首页商品卡片中的上架时间 - 查找mallGoodsTarget
"""

import time
import json
from html import unescape
from DrissionPage import ChromiumPage, ChromiumOptions

def check_product_cards():
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
        
        # 滚动到商品区域
        page.scroll.down(300)
        time.sleep(2)
        
        # 点击"商品"标签
        try:
            product_tab = page.ele('text:商品', timeout=3)
            if product_tab:
                product_tab.click()
                time.sleep(3)
                print("✅ 已点击商品标签")
        except:
            print("⚠️ 未找到商品标签，继续...")
        
        # 滚动加载
        for i in range(3):
            page.scroll.down(400)
            time.sleep(1)
        
        page.scroll.to_top()
        time.sleep(1)
        
        # 查找包含mallGoodsTarget的元素
        print("\n🔍 查找商品卡片...")
        eaglet_elems = page.eles('@data-eaglet')
        print(f"找到 {len(eaglet_elems)} 个 data-eaglet 元素")
        
        product_cards = []
        for elem in eaglet_elems:
            eaglet_str = elem.attr('data-eaglet')
            if eaglet_str and 'mallGoodsTarget' in eaglet_str:
                product_cards.append(elem)
        
        print(f"找到 {len(product_cards)} 个商品卡片")
        
        # 检查前3个商品卡片
        for idx, elem in enumerate(product_cards[:3], 1):
            print(f"\n{'='*60}")
            print(f"商品 {idx}:")
            print(f"{'='*60}")
            
            eaglet_str = elem.attr('data-eaglet')
            if eaglet_str:
                try:
                    decoded = unescape(eaglet_str)
                    data = json.loads(decoded)
                    print(f"data-eaglet JSON:")
                    print(json.dumps(data, ensure_ascii=False, indent=2)[:800])
                except Exception as e:
                    print(f"JSON解析错误: {e}")
            
            # 获取所有文本
            print(f"\n完整文本:")
            all_text = elem.text
            print(all_text)
            
            # 查找时间关键词
            time_keywords = ['上架', '发布', '时间', '2024', '2025', '2026', '天前', '小时前', '月']
            for keyword in time_keywords:
                if keyword in all_text:
                    print(f"  ⭐ 找到关键词: {keyword}")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        page.quit()

if __name__ == '__main__':
    check_product_cards()
