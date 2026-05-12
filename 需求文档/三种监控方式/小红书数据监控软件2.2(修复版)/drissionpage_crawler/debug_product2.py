"""
调试商品详情页 - 使用 DrissionPage 原生方法
"""

import time
from DrissionPage import ChromiumPage, ChromiumOptions

def debug_product():
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
        
        # 滚动确保加载
        page.scroll.to_bottom()
        time.sleep(2)
        page.scroll.to_top()
        time.sleep(1)
        
        # 打印页面所有文本
        print("\n📄 页面完整文本:")
        page_text = page.text
        print(page_text[:2000])
        
        # 查找所有元素
        print("\n\n🔍 查找所有元素...")
        all_eles = page.eles('xpath://*')
        print(f"总共找到 {len(all_eles)} 个元素")
        
        # 查找包含特定关键词的元素
        keywords = ['大赛', '比赛', '资料', '文件', '时间', '上架', '发布']
        for keyword in keywords:
            print(f"\n🔍 搜索关键词: {keyword}")
            js = f"""
            () => {{
                const elements = [];
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null
                );
                let node;
                while (node = walker.nextNode()) {{
                    if (node.textContent.includes('{keyword}')) {{
                        const parent = node.parentElement;
                        elements.push({{
                            tag: parent ? parent.tagName : 'null',
                            class: parent ? parent.className : 'null',
                            text: node.textContent.trim().substring(0, 100)
                        }});
                    }}
                }}
                return elements.slice(0, 10);
            }}
            """
            try:
                results = page.run_js(js)
                if results and len(results) > 0:
                    for r in results:
                        print(f"  [{r['tag']}] class={r['class'][:60]}")
                        print(f"  文本: {r['text']}")
                        print()
                else:
                    print(f"  未找到包含 '{keyword}' 的元素")
            except Exception as e:
                print(f"  JS 错误: {e}")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        page.quit()

if __name__ == '__main__':
    debug_product()
