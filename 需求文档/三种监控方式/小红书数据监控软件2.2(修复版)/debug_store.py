"""
调试商铺页面 DOM 结构
"""

import asyncio
from DrissionPage import ChromiumPage, ChromiumOptions


async def debug_store_page():
    """调试商铺页面"""
    print("=" * 60)
    print("调试商铺页面 DOM 结构")
    print("=" * 60)
    
    co = ChromiumOptions()
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-images')
    
    page = ChromiumPage(addr_or_opts=co)
    
    try:
        store_url = 'https://www.xiaohongshu.com/vendor/68c59952c095d90015b6c758'
        print(f"\n🌐 正在打开商铺页面...")
        page.get(store_url)
        await asyncio.sleep(5)
        
        # 滚动加载
        print("\n📜 滚动加载内容...")
        for i in range(5):
            old_height = page.run_js('return document.body.scrollHeight')
            page.scroll.to_bottom()
            await asyncio.sleep(1)
            new_height = page.run_js('return document.body.scrollHeight')
            print(f"  滚动 {i+1} 次: {old_height} -> {new_height}")
            if new_height == old_height:
                break
        
        # 获取页面 HTML
        html = page.html
        print(f"\n📄 页面 HTML 长度: {len(html)}")
        
        # 保存完整 HTML
        with open('store_page_debug.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"💾 完整 HTML 已保存到: store_page_debug.html")
        
        # 尝试各种选择器
        selectors_to_try = [
            '[class*="goods"]',
            '[class*="product"]',
            '[class*="item"]',
            '[class*="card"]',
            'a[href*="goods-detail"]',
            'a[href*="explore"]',
            '.note-item',
            '.goods-item',
            '.product-item',
        ]
        
        print("\n🔍 尝试各种选择器:")
        for selector in selectors_to_try:
            try:
                elems = page.eles(selector)
                print(f"  {selector}: 找到 {len(elems)} 个元素")
                if elems:
                    for i, elem in enumerate(elems[:3]):
                        print(f"    [{i}] {elem.text[:100]}")
                        if elem.attr('href'):
                            print(f"        href: {elem.attr('href')}")
            except Exception as e:
                print(f"  {selector}: 错误 - {e}")
        
        # 获取所有链接
        print("\n🔗 页面中的所有链接（前20个）:")
        all_links = page.eles('tag:a')
        for i, link in enumerate(all_links[:20]):
            href = link.attr('href')
            text = link.text[:50] if link.text else ''
            if href:
                print(f"  [{i}] {text} -> {href}")
        
        # 获取所有 class 名称
        print("\n🏷️ 页面中的主要 class 名称（前30个）:")
        all_elements = page.eles('xpath://*[@class]')
        class_set = set()
        for elem in all_elements:
            classes = elem.attr('class')
            if classes:
                for cls in classes.split():
                    if len(cls) > 3:
                        class_set.add(cls)
        
        for cls in sorted(list(class_set))[:30]:
            print(f"  .{cls}")
        
    finally:
        page.quit()


if __name__ == '__main__':
    asyncio.run(debug_store_page())
