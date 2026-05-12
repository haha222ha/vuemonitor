"""
测试商品名称提取
"""

import time
import json
from DrissionPage import ChromiumPage, ChromiumOptions

def test_product_name():
    print("=" * 60)
    print("测试商品名称提取")
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
        
        # 等待不同时间检查标题
        for wait_time in [3, 5, 8]:
            time.sleep(wait_time - 3)
            title = page.title
            print(f"\n⏱️  等待 {wait_time} 秒后:")
            print(f"  页面标题: {title}")
            
            # 检查是否有商品名称元素
            js = """
            () => {
                const allElements = document.querySelectorAll('*');
                const results = [];
                allElements.forEach(el => {
                    const text = el.textContent.trim();
                    if (text.length > 10 && text.length < 100 && 
                        !text.includes('script') && !text.includes('style') &&
                        el.children.length === 0) {
                        results.push(text);
                    }
                });
                return results.slice(0, 20);
            }
            """
            try:
                texts = page.run_js(js)
                if texts:
                    print(f"  找到的文本节点 (前10个):")
                    for i, text in enumerate(texts[:10], 1):
                        print(f"    {i}. {text}")
            except Exception as e:
                print(f"  JS执行错误: {e}")
        
        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        page.quit()

if __name__ == '__main__':
    test_product_name()
