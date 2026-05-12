"""
调试商品详情页结构
"""

import time
import json
from DrissionPage import ChromiumPage, ChromiumOptions

def debug_product_page():
    print("=" * 60)
    print("调试商品详情页结构")
    print("=" * 60)
    
    co = ChromiumOptions()
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--no-sandbox')
    co.auto_port()
    
    page = ChromiumPage(addr_or_opts=co)
    
    try:
        product_url = 'https://www.xiaohongshu.com/goods-detail/69b68cb01b6b3f0001385bc6'
        print(f"\n🌐 打开商品: {product_url}")
        page.get(product_url)
        time.sleep(5)
        
        # 检查页面标题
        print(f"\n📄 页面标题: {page.title}")
        print(f"🔗 当前URL: {page.url}")
        
        # 检查各种选择器
        print("\n🔍 检查元素选择器:")
        
        selectors = [
            # 商品名称
            'div.goods-name',
            '[class*="goods-name"]',
            'h1[class*="title"]',
            '[class*="product-name"]',
            # 价格
            '.price-container',
            '[class*="price-container"]',
            '[class*="price"]',
            # 销量
            '.spu-text',
            '[class*="spu-text"]',
            '[class*="sales"]',
            # 上架时间
            '[class*="publish-time"]',
            '[class*="release-time"]',
            '[class*="create-time"]',
            'span[class*="time"]',
            # 商铺信息
            '.seller-container',
            '.shop-info',
            '[class*="seller"]',
            '[class*="shop"]',
            '[class*="store"]',
        ]
        
        for sel in selectors:
            try:
                elems = page.eles(sel)
                print(f"  {sel}: {len(elems)} 个元素")
                if len(elems) > 0:
                    for idx, elem in enumerate(elems[:2], 1):
                        text = elem.text.strip() if elem.text else '无文本'
                        print(f"    元素 {idx}: {text[:80]}")
            except Exception as e:
                print(f"  {sel}: 错误 - {e}")
        
        # 获取页面中所有包含文本的元素
        print("\n🔍 查找包含关键信息的元素:")
        
        keywords = ['商品名称', '价格', '销量', '已售', '上架', '发布', '店铺', '商铺']
        for keyword in keywords:
            js = f"""
            () => {{
                const elements = document.querySelectorAll('*');
                const results = [];
                elements.forEach(el => {{
                    if (el.textContent && el.textContent.includes('{keyword}') && el.children.length < 5) {{
                        results.push({{
                            tag: el.tagName,
                            className: el.className,
                            text: el.textContent.substring(0, 100)
                        }});
                    }}
                }});
                return results.slice(0, 3);
            }}
            """
            try:
                results = page.run_js(js)
                if results:
                    print(f"\n  关键词 '{keyword}':")
                    for r in results:
                        print(f"    {r['tag']}.{r['className']}: {r['text']}")
            except:
                pass
        
        # 保存 HTML
        html = page.html
        with open('debug_product.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n💾 HTML 已保存: debug_product.html ({len(html)} 字符)")
        
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
    debug_product_page()
