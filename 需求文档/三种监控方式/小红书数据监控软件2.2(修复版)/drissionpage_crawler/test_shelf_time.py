"""
测试从店铺首页提取商品上架时间
"""

import time
import json
from html import unescape
from DrissionPage import ChromiumPage, ChromiumOptions

def extract_shelf_time():
    co = ChromiumOptions()
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--no-sandbox')
    co.auto_port()
    
    page = ChromiumPage(addr_or_opts=co)
    
    try:
        store_url = 'https://www.xiaohongshu.com/vendor/68c59952c095d90015b6c758'
        print(f"🌐 打开店铺: {store_url}")
        page.get(store_url)
        time.sleep(5)
        
        # 点击商品标签
        try:
            product_tab = page.ele('text:商品', timeout=3)
            if product_tab:
                product_tab.click()
                time.sleep(3)
        except:
            pass
        
        # 滚动加载
        for i in range(5):
            page.scroll.down(400)
            time.sleep(1)
        
        page.scroll.to_top()
        time.sleep(1)
        
        # 查找日期标题
        print("\n🔍 查找日期标题...")
        
        # 方法1: 查找 h1 标签
        h1_elements = page.eles('tag:h1')
        print(f"找到 {len(h1_elements)} 个 h1 元素:")
        for h1 in h1_elements:
            text = h1.text.strip()
            if text:
                print(f"  h1: {text}")
        
        # 方法2: 查找包含日期的元素
        print("\n🔍 查找所有商品分组...")
        
        # 获取所有商品卡片，按顺序排列
        eaglet_elems = page.eles('@data-eaglet')
        
        current_date = None
        products_with_date = []
        
        # 遍历所有元素，查找日期标题和商品卡片
        all_elements = page.eles('xpath://*')
        
        for elem in all_elements:
            try:
                tag = elem.tag
                text = elem.text.strip() if elem.text else ''
                
                # 检查是否是日期标题
                if tag == 'h1' and text and ('月' in text or '日' in text or '年' in text):
                    current_date = text
                    print(f"\n📅 发现日期分组: {current_date}")
                    continue
                
                # 检查是否是商品卡片
                eaglet_str = elem.attr('data-eaglet')
                if eaglet_str and 'mallGoodsTarget' in eaglet_str:
                    try:
                        decoded = unescape(eaglet_str)
                        data = json.loads(decoded)
                        goods_id = data.get('mallGoodsTarget', {}).get('value', {}).get('goodsId')
                        
                        if goods_id:
                            # 获取商品名称
                            title_elem = elem.ele('.goods-title', timeout=1)
                            product_name = title_elem.text.strip() if title_elem else 'N/A'
                            
                            products_with_date.append({
                                'product_id': goods_id,
                                'product_name': product_name,
                                'shelf_date': current_date or '未知'
                            })
                            
                            print(f"  商品: {product_name[:30]}... | 上架: {current_date or '未知'}")
                    except:
                        pass
            except:
                pass
        
        print(f"\n\n✅ 共采集 {len(products_with_date)} 个商品（含上架时间）")
        
        # 保存结果
        with open('products_with_shelf_time.json', 'w', encoding='utf-8') as f:
            json.dump(products_with_date, f, ensure_ascii=False, indent=2)
        print(f"💾 结果已保存: products_with_shelf_time.json")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        page.quit()

if __name__ == '__main__':
    extract_shelf_time()
