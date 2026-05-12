"""
测试商铺商品列表采集
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from crawler import HighConcurrencyCrawler, CrawlerConfig


def test_store():
    print("=" * 60)
    print("测试商铺商品列表采集")
    print("=" * 60)
    
    config = CrawlerConfig()
    config.MAX_CONCURRENCY = 1
    
    crawler = HighConcurrencyCrawler(config)
    
    try:
        print("\n🚀 初始化采集器...")
        crawler.init()
        
        store_url = 'https://www.xiaohongshu.com/vendor/68c59952c095d90015b6c758'
        print(f"\n📥 采集商铺: {store_url}")
        
        products = crawler.collect_store(store_url)
        
        print(f"\n{'=' * 60}")
        print(f"✅ 采集完成！共 {len(products)} 个商品")
        print(f"{'=' * 60}\n")
        
        for i, p in enumerate(products, 1):
            print(f"商品 {i}:")
            print(f"  ID: {p.get('product_id')}")
            print(f"  名称: {p.get('product_name')}")
            print(f"  价格: ¥{p.get('product_price')}")
            print(f"  标签: {', '.join(p.get('tags', []))}")
            print(f"  链接: {p.get('product_url')}")
            print()
        
        # 保存商铺采集结果
        crawler.results = products
        crawler.save_results('test_store_products.json')
        
    except Exception as e:
        print(f"\n❌ 失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        crawler.close()


if __name__ == '__main__':
    test_store()
