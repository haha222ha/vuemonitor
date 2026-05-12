"""
小红书高并发采集系统 - 主入口
Xiaohongshu High-Concurrency Crawler System - Main Entry

功能：
1. 商铺商品列表采集
2. 商品详情高并发采集
3. 结果自动保存为 JSON

用法：
  python main.py                    # 使用默认配置
  python main.py --concurrency 3    # 设置并发数为3
"""

import argparse
import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from crawler import HighConcurrencyCrawler, CrawlerConfig


def main():
    parser = argparse.ArgumentParser(description='小红书高并发采集系统')
    parser.add_argument('--concurrency', type=int, default=5, help='并发数 (默认: 5)')
    parser.add_argument('--store', type=str, help='商铺URL')
    parser.add_argument('--products', type=str, nargs='+', help='商品URL列表')
    parser.add_argument('--cookie', type=str, default='./cookies.json', help='Cookie文件路径')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("小红书高并发采集系统")
    print("=" * 60)
    
    # 配置
    config = CrawlerConfig()
    config.MAX_CONCURRENCY = args.concurrency
    config.COOKIE_FILE = args.cookie
    
    crawler = HighConcurrencyCrawler(config)
    
    try:
        # 初始化
        print(f"\n🚀 初始化采集器 (并发数: {args.concurrency})...")
        crawler.init()
        
        all_products = []
        
        # 1. 采集商铺商品列表
        if args.store:
            print(f"\n{'=' * 60}")
            print(f"📥 采集商铺: {args.store}")
            print(f"{'=' * 60}\n")
            
            products = crawler.collect_store(args.store)
            all_products.extend(products)
            
            print(f"\n✅ 商铺采集完成: {len(products)} 个商品")
        
        # 2. 采集商品详情
        if args.products:
            print(f"\n{'=' * 60}")
            print(f"🎯 采集 {len(args.products)} 个商品详情")
            print(f"{'=' * 60}\n")
            
            results = crawler.collect_products(args.products)
            
            success_count = sum(1 for r in results if r.get('success'))
            print(f"\n✅ 商品详情采集完成: {success_count}/{len(args.products)}")
        
        # 3. 保存结果
        if all_products:
            output_file = f'results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            crawler.results = all_products
            crawler.save_results(output_file)
            
            print(f"\n{'=' * 60}")
            print(f"💾 结果已保存: {output_file}")
            print(f"📊 总计: {len(all_products)} 个商品")
            print(f"{'=' * 60}\n")
            
            # 显示统计信息
            prices = [p.get('product_price') for p in all_products if p.get('product_price')]
            if prices:
                print(f"💰 价格统计:")
                print(f"   最低价: ¥{min(prices):.2f}")
                print(f"   最高价: ¥{max(prices):.2f}")
                print(f"   平均价: ¥{sum(prices)/len(prices):.2f}")
            
            tags_count = {}
            for p in all_products:
                for tag in p.get('tags', []):
                    tags_count[tag] = tags_count.get(tag, 0) + 1
            
            if tags_count:
                print(f"\n🏷️  标签统计:")
                for tag, count in sorted(tags_count.items(), key=lambda x: x[1], reverse=True):
                    print(f"   {tag}: {count} 个商品")
        
    except Exception as e:
        print(f"\n❌ 失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        crawler.close()
        print("\n👋 采集系统已关闭")


if __name__ == '__main__':
    main()
