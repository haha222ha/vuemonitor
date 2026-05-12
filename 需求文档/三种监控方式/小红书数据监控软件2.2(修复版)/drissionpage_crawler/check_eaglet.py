"""
检查 data-eaglet 实际结构
"""

import time
import json
from DrissionPage import ChromiumPage, ChromiumOptions

def check_eaglet():
    print("=" * 60)
    print("检查 data-eaglet 实际结构")
    print("=" * 60)
    
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
        
        # 滚动加载
        print("\n📜 滚动加载...")
        for i in range(5):
            old_h = page.run_js('return document.documentElement.scrollHeight')
            page.scroll.to_bottom()
            time.sleep(2)
            new_h = page.run_js('return document.documentElement.scrollHeight')
            if new_h == old_h:
                break
        
        time.sleep(3)
        
        # 获取所有 data-eaglet 并打印前几个的完整内容
        print("\n🔍 获取 data-eaglet 内容...")
        js = """
        () => {
            const elements = document.querySelectorAll('[data-eaglet]');
            const results = [];
            elements.forEach((el, idx) => {
                if (idx < 10) {
                    results.push({
                        index: idx,
                        eaglet: el.getAttribute('data-eaglet'),
                        className: el.className,
                        tagName: el.tagName
                    });
                }
            });
            return results;
        }
        """
        
        results = page.run_js(js)
        if results:
            for item in results:
                print(f"\n--- 元素 {item['index']} ---")
                print(f"  标签: {item['tagName']}")
                print(f"  类名: {item['className']}")
                print(f"  eaglet: {item['eaglet'][:200]}...")
                
                # 尝试解析 eaglet JSON
                try:
                    eaglet_json = item['eaglet'].replace('&quot;', '"')
                    eaglet_data = json.loads(eaglet_json)
                    print(f"  解析后: {json.dumps(eaglet_data, ensure_ascii=False)[:200]}")
                except:
                    print(f"  JSON解析失败")
        
        print("\n" + "=" * 60)
        print("检查完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        page.quit()

if __name__ == '__main__':
    check_eaglet()
