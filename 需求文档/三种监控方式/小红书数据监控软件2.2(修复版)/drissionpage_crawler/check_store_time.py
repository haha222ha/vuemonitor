"""
检查店铺首页商品卡片中的上架时间
"""

import time
import json
from DrissionPage import ChromiumPage, ChromiumOptions

def check_store_publish_time():
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
        
        # 滚动加载
        for i in range(5):
            page.scroll.down(500)
            time.sleep(1)
        
        page.scroll.to_top()
        time.sleep(1)
        
        # 检查商品卡片元素
        print("\n🔍 检查商品卡片元素...")
        
        eaglet_elems = page.eles('@data-eaglet')
        print(f"找到 {len(eaglet_elems)} 个 data-eaglet 元素")
        
        # 检查前3个商品卡片的完整结构
        for idx, elem in enumerate(eaglet_elems[:3], 1):
            print(f"\n{'='*60}")
            print(f"商品 {idx}:")
            print(f"{'='*60}")
            
            eaglet_str = elem.attr('data-eaglet')
            if eaglet_str:
                try:
                    from html import unescape
                    decoded = unescape(eaglet_str)
                    data = json.loads(decoded)
                    print(f"data-eaglet 内容:")
                    print(json.dumps(data, ensure_ascii=False, indent=2)[:500])
                except:
                    pass
            
            # 获取所有子元素的文本
            print(f"\n元素文本:")
            all_text = elem.text
            print(all_text[:300])
            
            # 查找时间相关元素
            time_keywords = ['上架', '发布', '时间', '2024', '2025', '2026', '天前', '小时前']
            for keyword in time_keywords:
                if keyword in all_text:
                    print(f"  ⭐ 找到时间关键词: {keyword}")
        
        # 保存HTML
        html = page.html
        with open('store_page_debug.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n💾 HTML已保存: store_page_debug.html")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        page.quit()

if __name__ == '__main__':
    check_store_publish_time()
