"""
检查页面结构
"""

import time
import json
from DrissionPage import ChromiumPage, ChromiumOptions

def check_structure():
    print("=" * 60)
    print("检查页面结构")
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
        
        # 检查 iframe
        print("\n🔍 检查 iframe...")
        iframes = page.eles('tag:iframe')
        print(f"  iframe 数量: {len(iframes)}")
        
        # 检查 shadow root
        print("\n🔍 检查 shadow root...")
        js_shadow = """
        () => {
            const results = [];
            function checkShadow(element, path) {
                if (element.shadowRoot) {
                    results.push({
                        path: path,
                        shadowHTML: element.shadowRoot.innerHTML.substring(0, 200)
                    });
                }
                element.querySelectorAll('*').forEach(child => {
                    if (child.shadowRoot) {
                        checkShadow(child, path + ' > ' + child.tagName + '.' + (child.className || ''));
                    }
                });
            }
            checkShadow(document.body, 'body');
            return results;
        }
        """
        try:
            shadow_results = page.run_js(js_shadow)
            print(f"  Shadow root 数量: {len(shadow_results) if shadow_results else 0}")
            if shadow_results:
                for r in shadow_results[:3]:
                    print(f"    {r['path']}: {r['shadowHTML'][:100]}...")
        except Exception as e:
            print(f"  错误: {e}")
        
        # 使用 DrissionPage 的 eles 方法检查
        print("\n🔍 使用 DrissionPage 检查元素...")
        eaglet_elems = page.eles('@data-eaglet')
        print(f"  @data-eaglet 元素数量: {len(eaglet_elems)}")
        
        if eaglet_elems:
            for i, elem in enumerate(eaglet_elems[:3], 1):
                print(f"\n  元素 {i}:")
                print(f"    标签: {elem.tag}")
                print(f"    类名: {elem.attr('class')}")
                eaglet = elem.attr('data-eaglet')
                if eaglet:
                    print(f"    eaglet: {eaglet[:150]}...")
        
        # 检查 .goods-title
        print("\n🔍 检查 .goods-title...")
        titles = page.eles('.goods-title')
        print(f"  .goods-title 数量: {len(titles)}")
        if titles:
            for i, title in enumerate(titles[:3], 1):
                print(f"  {i}. {title.text}")
        
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
    check_structure()
