"""
调试商铺页面 DOM 结构
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))

from DrissionPage import ChromiumPage, ChromiumOptions


def debug_page():
    co = ChromiumOptions()
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--no-sandbox')
    co.auto_port()
    
    page = ChromiumPage(addr_or_opts=co)
    
    try:
        store_url = 'https://www.xiaohongshu.com/vendor/68c59952c095d90015b6c758'
        print(f"🌐 打开商铺: {store_url}")
        page.get(store_url)
        time.sleep(5)
        
        # 滚动加载
        print("\n📜 滚动加载...")
        for i in range(5):
            old_h = page.run_js('return document.documentElement.scrollHeight')
            page.scroll.to_bottom()
            time.sleep(1)
            new_h = page.run_js('return document.documentElement.scrollHeight')
            print(f"  滚动 {i+1}: {old_h} -> {new_h}")
            if new_h == old_h:
                break
        
        # 保存 HTML
        html = page.html
        with open('debug_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n💾 HTML 已保存: debug_page.html ({len(html)} 字符)")
        
        # 尝试各种选择器
        selectors = [
            '.goods-card',
            '[class*="goods-card"]',
            '.goods-title',
            '.price-container',
            '.deal-price',
            '.goods-image',
            'div[class*="goods"]',
            'div[class*="product"]',
            'a[href*="goods-detail"]',
        ]
        
        print("\n🔍 选择器测试:")
        for sel in selectors:
            try:
                elems = page.eles(sel)
                print(f"  {sel}: {len(elems)} 个")
                if elems:
                    for j, elem in enumerate(elems[:2]):
                        text = elem.text[:80] if elem.text else ''
                        print(f"    [{j}] {text}")
            except Exception as e:
                print(f"  {sel}: 错误 - {e}")
        
        # 检查页面是否有 iframe
        print("\n🔍 iframe 检查:")
        iframes = page.eles('tag:iframe')
        print(f"  找到 {len(iframes)} 个 iframe")
        
        # 检查 shadow-root
        print("\n🔍 shadow-root 检查:")
        shadow_hosts = page.eles('xpath://*[@shadowroot]')
        print(f"  找到 {len(shadow_hosts)} 个 shadow host")
        
        # 获取所有 class（前30个）
        print("\n🏷️ 主要 class 名称:")
        all_classes = set()
        elements = page.eles('xpath://*[@class]')
        for elem in elements:
            cls = elem.attr('class')
            if cls:
                for c in cls.split():
                    if len(c) > 3 and not c.startswith('data-v'):
                        all_classes.add(c)
        
        for cls in sorted(list(all_classes))[:30]:
            count = len(page.eles(f'.{cls}'))
            print(f"  .{cls}: {count} 个")
        
        # 获取所有链接
        print("\n🔗 链接检查 (goods-detail):")
        links = page.eles('tag:a')
        goods_links = [l.attr('href') for l in links if l.attr('href') and 'goods-detail' in l.attr('href')]
        print(f"  找到 {len(goods_links)} 个商品链接")
        for link in goods_links[:5]:
            print(f"    {link}")
        
        # 检查 data-eaglet 属性
        print("\n🔍 data-eaglet 属性检查:")
        eaglet_elems = page.eles('xpath://*[@data-eaglet]')
        print(f"  找到 {len(eaglet_elems)} 个元素有 data-eaglet 属性")
        for elem in eaglet_elems[:3]:
            eaglet = elem.attr('data-eaglet')
            print(f"    {eaglet[:100]}...")
        
    finally:
        page.quit()


if __name__ == '__main__':
    debug_page()
