"""
使用 JavaScript 提取商品详情页数据
"""

import time
import json
from DrissionPage import ChromiumPage, ChromiumOptions

def extract_product_data():
    print("=" * 60)
    print("使用 JavaScript 提取商品详情页数据")
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
        
        # 使用 JavaScript 提取所有可见文本
        print("\n🔍 提取页面可见文本...")
        js = """
        () => {
            const body = document.body;
            const walker = document.createTreeWalker(
                body,
                NodeFilter.SHOW_TEXT,
                {
                    acceptNode: function(node) {
                        if (node.parentElement.closest('script, style, noscript')) {
                            return NodeFilter.FILTER_REJECT;
                        }
                        if (node.textContent.trim().length > 0) {
                            return NodeFilter.FILTER_ACCEPT;
                        }
                        return NodeFilter.FILTER_REJECT;
                    }
                }
            );
            
            const texts = [];
            let node;
            while (node = walker.nextNode()) {
                const text = node.textContent.trim();
                if (text.length > 0 && text.length < 200) {
                    texts.push(text);
                }
            }
            return texts;
        }
        """
        
        texts = page.run_js(js)
        if texts:
            print(f"\n找到 {len(texts)} 个文本节点:")
            for i, text in enumerate(texts[:50], 1):
                print(f"  {i}. {text}")
        
        # 查找价格容器
        print("\n🔍 查找价格容器...")
        js_price = """
        () => {
            const priceContainers = document.querySelectorAll('[class*="price"]');
            const results = [];
            priceContainers.forEach(el => {
                results.push({
                    className: el.className,
                    text: el.textContent.trim().substring(0, 100),
                    tagName: el.tagName
                });
            });
            return results;
        }
        """
        price_results = page.run_js(js_price)
        if price_results:
            for r in price_results[:5]:
                print(f"  {r['tagName']}.{r['className']}: {r['text']}")
        
        # 查找商铺容器
        print("\n🔍 查找商铺容器...")
        js_seller = """
        () => {
            const sellerContainers = document.querySelectorAll('[class*="seller"], [class*="shop"], [class*="store"]');
            const results = [];
            sellerContainers.forEach(el => {
                results.push({
                    className: el.className,
                    text: el.textContent.trim().substring(0, 100),
                    tagName: el.tagName
                });
            });
            return results;
        }
        """
        seller_results = page.run_js(js_seller)
        if seller_results:
            for r in seller_results[:5]:
                print(f"  {r['tagName']}.{r['className']}: {r['text']}")
        
        print("\n" + "=" * 60)
        print("提取完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        page.quit()

if __name__ == '__main__':
    extract_product_data()
