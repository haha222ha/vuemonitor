"""
查找页面中的 JSON 数据
"""

import time
import re
import json
from DrissionPage import ChromiumPage, ChromiumOptions

def find_json_data():
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
        
        # 获取 HTML
        html = page.html
        
        # 查找 script 标签中的 JSON 数据
        print("\n🔍 查找 script 标签中的 JSON 数据...")
        
        # 查找包含商品信息的 script
        patterns = [
            r'window\.__INITIAL_SSR_STATE__\s*=\s*({.*?})\s*</script>',
            r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*</script>',
            r'window\.__DATA__\s*=\s*({.*?})\s*</script>',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                print(f"\n✅ 找到匹配模式: {pattern[:50]}...")
                try:
                    data = json.loads(match.group(1))
                    print(f"  数据类型: {type(data)}")
                    if isinstance(data, dict):
                        print(f"  键: {list(data.keys())[:10]}")
                        
                        # 查找商品名称
                        for key in ['title', 'name', 'goodsName', 'productName', 'itemTitle']:
                            if key in data:
                                print(f"  {key}: {data[key][:100] if isinstance(data[key], str) else data[key]}")
                except json.JSONDecodeError as e:
                    print(f"  JSON 解析错误: {e}")
                    # 打印前500字符
                    print(f"  数据预览: {match.group(1)[:500]}")
        
        # 查找所有包含商品名称的字符串
        print("\n🔍 查找商品名称相关字符串...")
        title_patterns = [
            r'"title"\s*:\s*"([^"]{10,100})"',
            r'"name"\s*:\s*"([^"]{10,100})"',
            r'"goodsName"\s*:\s*"([^"]{10,100})"',
        ]
        
        for pattern in title_patterns:
            matches = re.findall(pattern, html)
            if matches:
                print(f"\n模式 {pattern[:30]}... 找到 {len(matches)} 个匹配:")
                for i, match in enumerate(matches[:5], 1):
                    print(f"  {i}. {match}")
        
        # 尝试使用 JS 获取页面数据
        print("\n🔍 使用 JS 获取页面数据...")
        js = """
        () => {
            // 尝试获取 window 对象上的数据
            const keys = Object.keys(window).filter(k => 
                k.includes('INITIAL') || 
                k.includes('STATE') || 
                k.includes('DATA') ||
                k.includes('__')
            );
            
            const results = {};
            keys.forEach(key => {
                try {
                    const data = window[key];
                    if (typeof data === 'object' && data !== null) {
                        results[key] = JSON.stringify(data).substring(0, 500);
                    }
                } catch (e) {
                    results[key] = 'Error: ' + e.message;
                }
            });
            
            return results;
        }
        """
        
        try:
            window_data = page.run_js(js)
            if window_data:
                print(f"\n找到 {len(window_data)} 个全局变量:")
                for key, value in window_data.items():
                    print(f"\n  {key}:")
                    print(f"  {value[:200]}...")
        except Exception as e:
            print(f"  JS 错误: {e}")
        
        print("\n" + "=" * 60)
        print("调试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        page.quit()

if __name__ == '__main__':
    find_json_data()
