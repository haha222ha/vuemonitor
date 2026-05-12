"""
测试 JavaScript 执行
"""

import time
import json
from DrissionPage import ChromiumPage, ChromiumOptions

def test_js():
    print("=" * 60)
    print("测试 JavaScript 执行")
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
            print(f"  滚动 {i+1}: {old_h} -> {new_h}")
            if new_h == old_h:
                break
        
        time.sleep(3)
        
        # 测试 1: 获取所有 data-eaglet 元素数量
        print("\n🔍 测试 1: 获取所有 [data-eaglet] 元素")
        js1 = "return document.querySelectorAll('[data-eaglet]').length"
        count1 = page.run_js(js1)
        print(f"  结果: {count1} 个元素")
        
        # 测试 2: 获取包含 goodsId 的元素
        print("\n🔍 测试 2: 获取包含 goodsId 的 data-eaglet")
        js2 = """
        () => {
            const elements = document.querySelectorAll('[data-eaglet]');
            const results = [];
            elements.forEach(el => {
                const eaglet = el.getAttribute('data-eaglet');
                if (eaglet && eaglet.includes('goodsId')) {
                    results.push(eaglet.substring(0, 100));
                }
            });
            return results;
        }
        """
        try:
            result2 = page.run_js(js2)
            print(f"  结果: {len(result2) if result2 else 0} 个元素")
            if result2 and len(result2) > 0:
                print(f"  示例: {result2[0]}")
        except Exception as e:
            print(f"  错误: {e}")
        
        # 测试 3: 直接获取 .goods-title 的文本
        print("\n🔍 测试 3: 获取 .goods-title 元素文本")
        js3 = """
        () => {
            const titles = document.querySelectorAll('.goods-title');
            return Array.from(titles).slice(0, 3).map(t => t.textContent.trim());
        }
        """
        try:
            result3 = page.run_js(js3)
            print(f"  结果: {len(result3) if result3 else 0} 个标题")
            if result3:
                for i, title in enumerate(result3[:3], 1):
                    print(f"    {i}. {title}")
        except Exception as e:
            print(f"  错误: {e}")
        
        # 测试 4: 获取包含 mallGoodsTarget 的元素
        print("\n🔍 测试 4: 获取包含 mallGoodsTarget 的 data-eaglet")
        js4 = """
        () => {
            const elements = document.querySelectorAll('[data-eaglet]');
            const results = [];
            elements.forEach(el => {
                const eaglet = el.getAttribute('data-eaglet');
                if (eaglet && eaglet.includes('mallGoodsTarget')) {
                    results.push({
                        eaglet: eaglet.substring(0, 200),
                        className: el.className
                    });
                }
            });
            return results;
        }
        """
        try:
            result4 = page.run_js(js4)
            print(f"  结果: {len(result4) if result4 else 0} 个元素")
            if result4 and len(result4) > 0:
                print(f"  示例 eaglet: {result4[0]['eaglet']}")
                print(f"  示例 className: {result4[0]['className']}")
        except Exception as e:
            print(f"  错误: {e}")
        
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
    test_js()
