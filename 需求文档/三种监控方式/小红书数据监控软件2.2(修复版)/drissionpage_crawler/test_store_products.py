"""
测试商铺列表页采集 - 检查商品名称
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from crawler import HighConcurrencyCrawler, CrawlerConfig

config = CrawlerConfig()
crawler = HighConcurrencyCrawler(config)

try:
    crawler.init()
    
    store_url = 'https://www.xiaohongshu.com/vendor/68c59952c095d90015b6c758'
    print(f"📥 采集商铺: {store_url}\n")
    
    products = crawler.collect_store(store_url)
    
    print(f"\n✅ 采集完成: {len(products)} 个商品\n")
    
    # 显示前10个商品的完整信息
    for i, p in enumerate(products[:10], 1):
        print(f"商品 {i}:")
        print(f"  ID: {p.get('product_id')}")
        print(f"  名称: {p.get('product_name')}")
        print(f"  价格: {p.get('product_price')}")
        print(f"  链接: {p.get('product_url')}")
        print()
    
    # 保存结果
    import json
    with open('store_products_test.json', 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print(f"💾 结果已保存: store_products_test.json")
    
finally:
    crawler.close()
