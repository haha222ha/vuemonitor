"""
调试商品详情页 - 查找商品名称和上架时间
"""

import time
import json
from DrissionPage import ChromiumPage, ChromiumOptions

def debug_product_detail():
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
        
        # 滚动页面确保所有内容加载
        page.scroll.to_bottom()
        time.sleep(2)
        page.scroll.to_top()
        time.sleep(1)
        
        # 使用 JS 查找所有包含文本的元素
        print("\n🔍 查找页面中的所有文本元素...")
        js = """
        () => {
            const allElements = document.querySelectorAll('*');
            const results = [];
            allElements.forEach(el => {
                const text = el.textContent.trim();
                const className = el.className || '';
                const tagName = el.tagName;
                
                // 查找可能包含商品名称的元素
                if (text.length > 5 && text.length < 100) {
                    if (className.includes('title') || 
                        className.includes('name') || 
                        className.includes('goods') ||
                        className.includes('product') ||
                        className.includes('detail')) {
                        results.push({
                            tag: tagName,
                            class: className.substring(0, 80),
                            text: text.substring(0, 100)
                        });
                    }
                }
            });
            return results.slice(0, 30);
        }
        """
        
        results = page.run_js(js)
        if results:
            print(f"\n找到 {len(results)} 个相关元素:")
            for i, r in enumerate(results, 1):
                print(f"\n{i}. [{r['tag']}] class={r['class']}")
                print(f"   文本: {r['text']}")
        
        # 查找时间相关元素
        print("\n\n🔍 查找时间相关元素...")
        js_time = """
        () => {
            const allElements = document.querySelectorAll('*');
            const results = [];
            allElements.forEach(el => {
                const text = el.textContent.trim();
                const className = el.className || '';
                
                if (className.includes('time') || 
                    className.includes('date') ||
                    className.includes('publish') ||
                    className.includes('release') ||
                    className.includes('create')) {
                    if (text.length > 0 && text.length < 50) {
                        results.push({
                            tag: el.tagName,
                            class: className.substring(0, 80),
                            text: text
                        });
                    }
                }
            });
            return results.slice(0, 20);
        }
        """
        
        time_results = page.run_js(js_time)
        if time_results:
            print(f"\n找到 {len(time_results)} 个时间相关元素:")
            for i, r in enumerate(time_results, 1):
                print(f"\n{i}. [{r['tag']}] class={r['class']}")
                print(f"   文本: {r['text']}")
        
        # 保存 HTML 用于分析
        html = page.html
        with open('product_detail_debug.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n\n💾 HTML 已保存: product_detail_debug.html")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        page.quit()

if __name__ == '__main__':
    debug_product_detail()
