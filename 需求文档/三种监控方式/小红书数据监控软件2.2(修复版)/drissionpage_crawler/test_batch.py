"""
批量采集测试脚本
测试商铺商品列表 + 商品详情批量采集
包含上架时间和销量信息
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from crawler import HighConcurrencyCrawler, CrawlerConfig


def test_batch_collection():
    print("=" * 60)
    print("批量采集测试")
    print("=" * 60)
    
    # 配置
    config = CrawlerConfig()
    config.MAX_CONCURRENCY = 3  # 使用3个并发
    
    crawler = HighConcurrencyCrawler(config)
    
    try:
        # 初始化
        print("\n🚀 初始化采集器...")
        crawler.init()
        
        # 步骤1: 采集商铺商品列表
        store_url = 'https://www.xiaohongshu.com/vendor/68c59952c095d90015b6c758'
        print(f"\n{'=' * 60}")
        print(f"📥 步骤1: 采集商铺商品列表")
        print(f"{'=' * 60}\n")
        print(f"商铺: {store_url}\n")
        
        products = crawler.collect_store(store_url)
        
        print(f"\n✅ 商铺采集完成: {len(products)} 个商品\n")
        
        # 显示前5个商品
        print("📋 前5个商品预览:")
        for i, p in enumerate(products[:5], 1):
            print(f"  {i}. {p.get('product_name', 'N/A')}")
            print(f"     价格: ¥{p.get('product_price', 'N/A')}")
            print(f"     ID: {p.get('product_id')}")
            print()
        
        # 步骤2: 批量采集商品详情（取前10个商品测试）
        test_count = min(10, len(products))
        test_products = products[:test_count]
        product_urls = [p['product_url'] for p in test_products]
        
        # 创建商品名称映射（从商铺列表页获取）
        product_name_map = {p['product_id']: p.get('product_name') for p in products}
        
        print(f"\n{'=' * 60}")
        print(f"📦 步骤2: 批量采集 {test_count} 个商品详情")
        print(f"{'=' * 60}\n")
        
        results = crawler.collect_products(product_urls)
        
        # 步骤3: 合并数据并显示
        print(f"\n{'=' * 60}")
        print(f"📊 采集结果汇总")
        print(f"{'=' * 60}\n")
        
        success_results = [r for r in results if r.get('success')]
        print(f"✅ 成功: {len(success_results)}/{len(results)}\n")
        
        # 显示详细结果
        for i, result in enumerate(success_results, 1):
            data = result.get('data', {})
            product_id = data.get('product_id')
            
            # 从商铺列表页获取商品名称（如果商品详情页没有）
            product_name = data.get('product_name') or product_name_map.get(product_id)
            
            print(f"{'─' * 60}")
            print(f"商品 {i}:")
            print(f"  名称: {product_name}")
            print(f"  价格: ¥{data.get('product_price', 'N/A')}")
            print(f"  销量: {data.get('product_sales', 'N/A')}")
            print(f"  上架时间: {data.get('publish_time', 'N/A')}")
            print(f"  商铺: {data.get('store_name', 'N/A')}")
            print(f"  链接: {result.get('url', 'N/A')}")
            print()
        
        # 步骤4: 保存完整结果
        output_file = f'batch_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        # 合并商铺列表和详情数据
        merged_results = []
        for result in success_results:
            data = result.get('data', {})
            product_id = data.get('product_id')
            
            # 从商铺列表页获取商品名称（如果商品详情页没有）
            product_name = data.get('product_name') or product_name_map.get(product_id)
            
            merged_results.append({
                'product_id': product_id,
                'product_name': product_name,
                'product_price': data.get('product_price'),
                'product_sales': data.get('product_sales'),
                'publish_time': data.get('publish_time'),
                'store_name': data.get('store_name'),
                'store_sales': data.get('store_sales'),
                'product_url': result.get('url'),
                'collect_time': result.get('timestamp'),
            })
        
        crawler.results = merged_results
        crawler.save_results(output_file)
        
        # 统计信息
        print(f"\n{'=' * 60}")
        print(f"📈 统计信息")
        print(f"{'=' * 60}\n")
        
        prices = [r.get('product_price') for r in merged_results if r.get('product_price')]
        if prices:
            print(f"💰 价格统计:")
            print(f"   最低价: ¥{min(prices):.2f}")
            print(f"   最高价: ¥{max(prices):.2f}")
            print(f"   平均价: ¥{sum(prices)/len(prices):.2f}")
        
        sales = [r.get('product_sales') for r in merged_results if r.get('product_sales') is not None]
        if sales:
            print(f"\n📊 销量统计:")
            print(f"   最低销量: {min(sales)}")
            print(f"   最高销量: {max(sales)}")
            print(f"   平均销量: {sum(sales)/len(sales):.0f}")
        
        publish_times = [r.get('publish_time') for r in merged_results if r.get('publish_time')]
        if publish_times:
            print(f"\n📅 上架时间:")
            for pt in publish_times[:5]:
                print(f"   {pt}")
            if len(publish_times) > 5:
                print(f"   ... 共 {len(publish_times)} 个商品有上架时间")
        
        print(f"\n💾 结果已保存: {output_file}")
        print(f"📊 总计: {len(merged_results)} 个商品")
        print(f"{'=' * 60}\n")
        
    except Exception as e:
        print(f"\n❌ 失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        crawler.close()
        print("👋 采集系统已关闭")


if __name__ == '__main__':
    test_batch_collection()
