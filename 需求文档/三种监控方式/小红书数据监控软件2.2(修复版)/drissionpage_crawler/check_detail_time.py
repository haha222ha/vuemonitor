"""
检查商品详情页是否有上架时间
"""

import time
from DrissionPage import ChromiumPage, ChromiumOptions

def check_product_detail_time():
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
        
        # 滚动到底部
        page.scroll.to_bottom()
        time.sleep(2)
        page.scroll.to_top()
        time.sleep(1)
        
        # 获取页面所有文本
        print("\n📄 页面文本内容:")
        all_eles = page.eles('xpath://*')
        
        # 查找包含时间的元素
        time_patterns = ['上架', '发布', '创建', '2024-', '2025-', '2026-', '天前', '小时前']
        
        for elem in all_eles:
            try:
                text = elem.text
                if text and len(text) < 50 and len(text) > 5:
                    for pattern in time_patterns:
                        if pattern in text:
                            class_name = elem.attr('class') or ''
                            tag = elem.tag
                            print(f"  [{tag}] class={class_name[:50]}")
                            print(f"  文本: {text}")
                            print()
                            break
            except:
                pass
        
        # 使用JS查找
        print("\n🔍 JS查找时间信息...")
        js = """
        () => {
            const bodyText = document.body.innerText;
            const lines = bodyText.split('\\n').filter(l => l.trim());
            const timeLines = lines.filter(l => 
                l.includes('上架') || l.includes('发布') || 
                /\\d{4}[-/]\\d{1,2}[-/]\\d{1,2}/.test(l) ||
                l.includes('天前') || l.includes('小时前')
            );
            return timeLines.slice(0, 20);
        }
        """
        try:
            time_lines = page.run_js(js)
            if time_lines:
                print(f"找到 {len(time_lines)} 个时间相关行:")
                for line in time_lines:
                    print(f"  {line}")
            else:
                print("未找到时间信息")
        except Exception as e:
            print(f"JS错误: {e}")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        page.quit()

if __name__ == '__main__':
    check_product_detail_time()
