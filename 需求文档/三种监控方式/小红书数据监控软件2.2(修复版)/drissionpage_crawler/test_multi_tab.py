"""
多标签页并发采集测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from multi_tab_crawler import MultiTabCrawler, MultiTabConfig


def test_multi_tab_collection():
    print("=" * 60)
    print("多标签页并发采集测试")
    print("=" * 60)
    
    config = MultiTabConfig()
    config.MAX_TABS = 5  # 5个标签页并发
    
    crawler = MultiTabCrawler(config)
    
    try:
        print("\n🚀 初始化采集器...")
        crawler.init()
        
        # 步骤1: 采集商铺商品列表
        store_url = 'https://www.xiaohongshu.com/vendor/68c59952c095d90015b6c758'
        print(f"\n{'=' * 60}")
        print(f"📥 步骤1: 采集商铺商品列表")
        print(f"{'=' * 60}\n")
        
        products = crawler.collect_store(store_url)
        print(f"\n✅ 商铺采集完成: {len(products)} 个商品\n")
        
        # 显示前5个商品
        print("📋 前5个商品:")
        for i, p in enumerate(products[:5], 1):
            print(f"  {i}. {p.get('product_name')}")
            print(f"     价格: ¥{p.get('product_price')}")
            print(f"     上架时间: {p.get('shelf_date', 'N/A')} → {p.get('shelf_date_full', 'N/A')}")
            print(f"     ID: {p.get('product_id')}")
            print()
        
        # 步骤2: 多标签页并发采集商品详情
        test_count = min(15, len(products))
        test_products = products[:test_count]
        
        print(f"\n{'=' * 60}")
        print(f"📦 步骤2: 多标签页并发采集 {test_count} 个商品")
        print(f"{'=' * 60}\n")
        
        results = crawler.collect_products_multi_tab(test_products)
        
        # 步骤3: 显示结果
        print(f"\n{'=' * 60}")
        print(f"📊 采集结果汇总")
        print(f"{'=' * 60}\n")
        
        success_results = [r for r in results if r.get('success')]
        print(f"✅ 成功: {len(success_results)}/{len(results)}\n")
        
        for i, result in enumerate(success_results, 1):
            data = result.get('data', {})
            print(f"{'─' * 60}")
            print(f"商品 {i}:")
            print(f"  名称: {data.get('product_name', 'N/A')}")
            print(f"  价格: ¥{data.get('product_price', 'N/A')}")
            print(f"  销量: {data.get('product_sales', 'N/A')}")
            print(f"  上架时间: {data.get('shelf_date', 'N/A')} → {data.get('shelf_date_full', 'N/A')}")
            print(f"  商铺: {data.get('store_name', 'N/A')}")
            print(f"  链接: {result.get('url', 'N/A')}")
            print()
        
        # 保存结果
        crawler.save_results()
        
        # 统计信息
        print(f"\n{'=' * 60}")
        print(f"📈 统计信息")
        print(f"{'=' * 60}\n")
        
        prices = [r.get('data', {}).get('product_price') for r in success_results if r.get('data', {}).get('product_price')]
        if prices:
            print(f"💰 价格统计:")
            print(f"   最低价: ¥{min(prices):.2f}")
            print(f"   最高价: ¥{max(prices):.2f}")
            print(f"   平均价: ¥{sum(prices)/len(prices):.2f}")
        
        sales = [r.get('data', {}).get('product_sales') for r in success_results if r.get('data', {}).get('product_sales') is not None]
        if sales:
            print(f"\n📊 销量统计:")
            print(f"   最低销量: {min(sales)}")
            print(f"   最高销量: {max(sales)}")
            print(f"   平均销量: {sum(sales)/len(sales):.0f}")
        
        print(f"\n💾 结果已保存")
        print(f"📊 总计: {len(success_results)} 个商品")
        print(f"{'=' * 60}\n")
        
    except Exception as e:
        print(f"\n❌ 失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        crawler.close()
        print("👋 采集系统已关闭")


if __name__ == '__main__':
    test_multi_tab_collection()
