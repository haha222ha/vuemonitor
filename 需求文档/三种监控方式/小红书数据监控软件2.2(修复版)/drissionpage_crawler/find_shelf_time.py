"""
查找 on shelf time 上架时间字段
"""

import time
import json
from DrissionPage import ChromiumPage, ChromiumOptions

def find_on_shelf_time():
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
        
        page.scroll.to_bottom()
        time.sleep(2)
        page.scroll.to_top()
        time.sleep(1)
        
        # 搜索 on shelf time 相关关键词
        print("\n🔍 搜索上架时间相关关键词...")
        
        keywords = ['on shelf', 'onShelf', 'shelfTime', 'shelf_time', 'shelf time', 'on-shelf']
        
        for keyword in keywords:
            js = f"""
            () => {{
                const results = [];
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null
                );
                let node;
                while (node = walker.nextNode()) {{
                    const text = node.textContent;
                    if (text.toLowerCase().includes('{keyword}')) {{
                        const parent = node.parentElement;
                        results.push({{
                            tag: parent ? parent.tagName : 'null',
                            class: parent ? parent.className : 'null',
                            text: text.trim().substring(0, 200)
                        }});
                    }}
                }}
                return results.slice(0, 10);
            }}
            """
            try:
                results = page.run_js(js)
                if results and len(results) > 0:
                    print(f"\n✅ 找到关键词 '{keyword}':")
                    for r in results:
                        print(f"  [{r['tag']}] class={r['class'][:60]}")
                        print(f"  文本: {r['text']}")
                        print()
                else:
                    print(f"  未找到 '{keyword}'")
            except Exception as e:
                print(f"  JS错误: {e}")
        
        # 检查 HTML 中是否包含 onShelfTime 或类似字段
        print("\n🔍 检查 HTML 中的 JSON 数据...")
        html = page.html
        
        import re
        patterns = [
            r'"onShelfTime"\s*:\s*"?([^",}]+)"?',
            r'"on_shelf_time"\s*:\s*"?([^",}]+)"?',
            r'"on-shelf-time"\s*:\s*"?([^",}]+)"?',
            r'"shelfTime"\s*:\s*"?([^",}]+)"?',
            r'"shelf_time"\s*:\s*"?([^",}]+)"?',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                print(f"\n✅ 找到模式 {pattern}:")
                for i, match in enumerate(matches[:5], 1):
                    print(f"  {i}. {match}")
        
        # 保存 HTML 用于分析
        with open('product_detail_shelf_time.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n💾 HTML 已保存: product_detail_shelf_time.html")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        page.quit()

if __name__ == '__main__':
    find_on_shelf_time()
