"""
小红书数据监控采集系统 1.0
主入口脚本
"""

import sys
import os
import argparse
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from multi_tab_crawler import MultiTabCrawler, MultiTabConfig


def collect_store(store_url, cookie_file=None):
    """采集商铺商品列表"""
    config = MultiTabConfig()
    if cookie_file:
        config.COOKIE_FILE = cookie_file
    
    crawler = MultiTabCrawler(config)
    
    try:
        crawler.init()
        products = crawler.collect_store(store_url)
        
        output_file = f'store_products_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 采集完成: {len(products)} 个商品")
        print(f"💾 结果已保存: {output_file}")
        
        return products
        
    finally:
        crawler.close()


def collect_products(product_urls, cookie_file=None, max_tabs=5):
    """多标签页并发采集商品详情"""
    config = MultiTabConfig()
    config.MAX_TABS = max_tabs
    if cookie_file:
        config.COOKIE_FILE = cookie_file
    
    crawler = MultiTabCrawler(config)
    
    try:
        crawler.init()
        results = crawler.collect_products_multi_tab(product_urls)
        crawler.save_results()
        
        success_count = len([r for r in results if r.get('success')])
        print(f"\n✅ 采集完成: {success_count}/{len(results)} 个商品")
        
        return results
        
    finally:
        crawler.close()


def main():
    parser = argparse.ArgumentParser(description='小红书数据监控采集系统')
    parser.add_argument('--mode', choices=['store', 'products', 'test'], required=True,
                       help='采集模式: store(商铺列表), products(商品详情), test(测试)')
    parser.add_argument('--store-url', help='商铺URL')
    parser.add_argument('--product-file', help='商品列表JSON文件')
    parser.add_argument('--cookie-file', help='Cookie文件路径')
    parser.add_argument('--max-tabs', type=int, default=5, help='最大标签页数')
    
    args = parser.parse_args()
    
    if args.mode == 'store':
        if not args.store_url:
            print("❌ 请提供商铺URL (--store-url)")
            return
        collect_store(args.store_url, args.cookie_file)
        
    elif args.mode == 'products':
        if not args.product_file:
            print("❌ 请提供商品列表文件 (--product-file)")
            return
        with open(args.product_file, 'r', encoding='utf-8') as f:
            products = json.load(f)
        collect_products(products, args.cookie_file, args.max_tabs)
        
    elif args.mode == 'test':
        from test_multi_tab import test_multi_tab_collection
        test_multi_tab_collection()


if __name__ == '__main__':
    main()
