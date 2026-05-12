"""
详细调试脚本 - 检查页面实际结构
"""

import time
import json
from DrissionPage import ChromiumPage, ChromiumOptions

def debug_store():
    print("=" * 60)
    print("详细调试商铺页面")
    print("=" * 60)
    
    # 初始化浏览器
    co = ChromiumOptions()
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--no-sandbox')
    co.auto_port()
    
    page = ChromiumPage(addr_or_opts=co)
    
    try:
        store_url = 'https://www.xiaohongshu.com/vendor/68c59952c095d90015b6c758'
        print(f"\n🌐 打开商铺: {store_url}")
        page.get(store_url)
        time.sleep(5)
        
        # 检查页面标题
        print(f"\n📄 页面标题: {page.title}")
        
        # 检查当前URL
        print(f"🔗 当前URL: {page.url}")
        
        # 滚动加载
        print("\n📜 滚动加载...")
        for i in range(5):
            old_h = page.run_js('return document.documentElement.scrollHeight')
            page.scroll.to_bottom()
            time.sleep(2)
            new_h = page.run_js('return document.documentElement.scrollHeight')
            print(f"  滚动 {i+1}: {old_h} -> {new_h}")
            if new_h == old_h:
                break
        
        time.sleep(3)
        
        # 检查各种选择器
        print("\n🔍 检查元素选择器:")
        
        selectors = [
            '.goods-card',
            '[class*="goods-card"]',
            '.twin-layout__card',
            '.goods-title',
            '[class*="goods-title"]',
            '.price-container',
            '[class*="price-container"]',
            '.recommend-content',
            '.swiper-slide',
        ]
        
        for sel in selectors:
            try:
                elems = page.eles(sel)
                print(f"  {sel}: {len(elems)} 个元素")
                if len(elems) > 0 and len(elems) <= 3:
                    for idx, elem in enumerate(elems[:2], 1):
                        print(f"    元素 {idx}:")
                        print(f"      文本: {elem.text[:50] if elem.text else '无文本'}")
                        print(f"      标签: {elem.tag}")
                        eaglet = elem.attr('data-eaglet')
                        if eaglet:
                            print(f"      data-eaglet: {eaglet[:100]}...")
            except Exception as e:
                print(f"  {sel}: 错误 - {e}")
        
        # 检查页面HTML片段
        print("\n📝 检查页面HTML片段...")
        html = page.html
        
        # 查找 goods-card 出现的位置
        if 'goods-card' in html:
            print("✅ HTML中包含 'goods-card'")
            # 找到第一个出现的位置
            idx = html.find('goods-card')
            print(f"   位置: {idx}")
            print(f"   上下文: ...{html[max(0,idx-100):idx+200]}...")
        else:
            print("❌ HTML中不包含 'goods-card'")
        
        # 检查是否有 iframe
        iframes = page.eles('tag:iframe')
        print(f"\n🖼️  iframe数量: {len(iframes)}")
        
        # 保存完整HTML
        with open('debug_detailed.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n💾 HTML已保存: debug_detailed.html ({len(html)} 字符)")
        
        print("\n" + "=" * 60)
        print("调试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        page.quit()

if __name__ == '__main__':
    debug_store()
