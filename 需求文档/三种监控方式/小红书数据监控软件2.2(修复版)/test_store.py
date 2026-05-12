"""
测试商铺商品列表采集
"""

import asyncio
import json
from xiaohongshu_crawler import (
    XiaohongshuHighConcurrencyCrawler,
    XiaohongshuCrawlerConfig
)


async def test_store_collection():
    """测试商铺商品列表采集"""
    print("=" * 60)
    print("测试商铺商品列表采集")
    print("=" * 60)
    
    config = XiaohongshuCrawlerConfig()
    config.MAX_CONCURRENCY = 1
    config.PAGE_LOAD_TIMEOUT = 20
    config.ELEMENT_WAIT_TIMEOUT = 15
    
    crawler = XiaohongshuHighConcurrencyCrawler(config)
    
    try:
        print("\n🚀 正在初始化采集器...")
        await crawler.initialize()
        
        store_url = 'https://www.xiaohongshu.com/vendor/68c59952c095d90015b6c758'
        print(f"\n📥 开始采集商铺: {store_url}")
        
        products = await crawler.collect_store_products(store_url)
        
        print(f"\n{'=' * 60}")
        print(f"✅ 采集完成！共采集到 {len(products)} 个商品")
        print(f"{'=' * 60}\n")
        
        for i, product in enumerate(products, 1):
            print(f"商品 {i}:")
            print(f"  名称: {product.get('product_name', 'N/A')}")
            print(f"  价格: ¥{product.get('product_price', 'N/A')}")
            print(f"  销量: {product.get('product_sales', 'N/A')}")
            print(f"  ID: {product.get('product_id', 'N/A')}")
            print(f"  链接: {product.get('product_url', 'N/A')}")
            print()
        
        # 保存结果
        output_file = 'test_store_products.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        print(f"💾 结果已保存到: {output_file}")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await crawler.close()
        print("\n✅ 采集器已关闭")


if __name__ == '__main__':
    asyncio.run(test_store_collection())
