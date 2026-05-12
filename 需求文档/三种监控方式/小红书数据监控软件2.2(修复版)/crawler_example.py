"""
小红书采集器 - 使用示例和配置
Xiaohongshu Crawler - Usage Examples and Configuration

使用方式:
1. 安装依赖: pip install DrissionPage
2. 配置 Cookie（可选）
3. 运行采集脚本
"""

import asyncio
import json
import os
from xiaohongshu_crawler import (
    XiaohongshuHighConcurrencyCrawler,
    XiaohongshuCrawlerConfig
)


async def example_1_single_product():
    """示例 1: 采集单个商品详情"""
    print("=" * 60)
    print("示例 1: 采集单个商品详情")
    print("=" * 60)
    
    config = XiaohongshuCrawlerConfig()
    config.MAX_CONCURRENCY = 1
    
    crawler = XiaohongshuHighConcurrencyCrawler(config)
    
    try:
        await crawler.initialize()
        
        product_url = 'https://www.xiaohongshu.com/goods-detail/67bbc5bfeef1820001f83a2d'
        results = await crawler.collect_product_details([product_url])
        
        if results:
            print("\n✅ 采集结果:")
            for result in results:
                data = result.get('data', {})
                print(f"  商品名称: {data.get('product_name', 'N/A')}")
                print(f"  商品价格: {data.get('product_price', 'N/A')}")
                print(f"  商品销量: {data.get('product_sales', 'N/A')}")
                print(f"  店铺名称: {data.get('store_name', 'N/A')}")
                print(f"  店铺销量: {data.get('store_sales', 'N/A')}")
                print(f"  店铺粉丝: {data.get('store_followers', 'N/A')}")
                print()
        
        await crawler.save_results('single_product_result.json')
        
    finally:
        await crawler.close()


async def example_2_batch_products():
    """示例 2: 批量采集商品详情"""
    print("=" * 60)
    print("示例 2: 批量采集商品详情")
    print("=" * 60)
    
    config = XiaohongshuCrawlerConfig()
    config.MAX_CONCURRENCY = 3
    
    crawler = XiaohongshuHighConcurrencyCrawler(config)
    
    try:
        await crawler.initialize()
        
        # 多个商品链接
        product_urls = [
            'https://www.xiaohongshu.com/goods-detail/67bbc5bfeef1820001f83a2d',
            # 添加更多商品链接...
        ]
        
        results = await crawler.collect_product_details(product_urls)
        
        print(f"\n✅ 采集完成: {len(results)}/{len(product_urls)}")
        
        await crawler.save_results('batch_products_result.json')
        
    finally:
        await crawler.close()


async def example_3_store_products():
    """示例 3: 采集商铺商品列表"""
    print("=" * 60)
    print("示例 3: 采集商铺商品列表")
    print("=" * 60)
    
    config = XiaohongshuCrawlerConfig()
    config.MAX_CONCURRENCY = 1
    
    crawler = XiaohongshuHighConcurrencyCrawler(config)
    
    try:
        await crawler.initialize()
        
        store_url = 'https://www.xiaohongshu.com/vendor/66c9df4702383e001535d18a'
        products = await crawler.collect_store_products(store_url)
        
        print(f"\n✅ 采集到 {len(products)} 个商品:")
        for i, product in enumerate(products, 1):
            print(f"  {i}. {product.get('product_name', 'N/A')}")
            print(f"     价格: {product.get('product_price', 'N/A')}")
            print(f"     销量: {product.get('product_sales', 'N/A')}")
            print(f"     链接: {product.get('product_url', 'N/A')}")
            print()
        
        # 保存商铺商品列表
        with open('store_products.json', 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        print(f"💾 商铺商品列表已保存: store_products.json")
        
    finally:
        await crawler.close()


async def example_4_full_workflow():
    """示例 4: 完整工作流 - 采集商铺所有商品详情"""
    print("=" * 60)
    print("示例 4: 完整工作流 - 采集商铺所有商品详情")
    print("=" * 60)
    
    config = XiaohongshuCrawlerConfig()
    config.MAX_CONCURRENCY = 5
    
    crawler = XiaohongshuHighConcurrencyCrawler(config)
    
    try:
        await crawler.initialize()
        
        # 步骤 1: 采集商铺商品列表
        store_url = 'https://www.xiaohongshu.com/vendor/66c9df4702383e001535d18a'
        print(f"\n📥 步骤 1: 采集商铺商品列表...")
        store_products = await crawler.collect_store_products(store_url)
        print(f"✅ 采集到 {len(store_products)} 个商品")
        
        # 步骤 2: 提取所有商品链接
        product_urls = [p['product_url'] for p in store_products if p.get('product_url')]
        print(f"\n📥 步骤 2: 批量采集 {len(product_urls)} 个商品详情...")
        
        # 步骤 3: 高并发采集商品详情
        results = await crawler.collect_product_details(product_urls)
        print(f"✅ 成功采集 {len(results)} 个商品详情")
        
        # 步骤 4: 保存结果
        await crawler.save_results('full_workflow_result.json')
        
        # 统计信息
        print("\n📊 统计信息:")
        print(f"  总商品数: {len(store_products)}")
        print(f"  成功采集: {len(results)}")
        print(f"  失败数量: {len(product_urls) - len(results)}")
        
        # 浏览器实例统计
        for browser in crawler.browsers:
            print(f"  浏览器 {browser.instance_id}: 成功 {browser.success_count}, 失败 {browser.error_count}")
        
    finally:
        await crawler.close()


async def example_5_custom_config():
    """示例 5: 自定义配置"""
    print("=" * 60)
    print("示例 5: 自定义配置")
    print("=" * 60)
    
    config = XiaohongshuCrawlerConfig()
    
    # 自定义配置
    config.MAX_CONCURRENCY = 10  # 高并发
    config.PAGE_LOAD_TIMEOUT = 20  # 增加超时时间
    config.RETRY_TIMES = 5  # 增加重试次数
    config.MIN_REQUEST_DELAY = 0.5  # 减少延迟
    config.MAX_REQUEST_DELAY = 1.5
    config.BATCH_DELAY = 3.0
    
    # 设置浏览器路径（如果使用非默认浏览器）
    # config.BROWSER_PATH = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    
    crawler = XiaohongshuHighConcurrencyCrawler(config)
    
    try:
        await crawler.initialize()
        
        # 你的采集逻辑...
        print("✅ 自定义配置采集器已就绪")
        
    finally:
        await crawler.close()


def setup_cookie():
    """设置 Cookie 的辅助函数"""
    print("=" * 60)
    print("Cookie 设置指南")
    print("=" * 60)
    
    print("""
1. 手动获取 Cookie:
   - 打开浏览器，登录小红书
   - 按 F12 打开开发者工具
   - 切换到 Network 标签
   - 刷新页面，找到任意请求
   - 查看 Request Headers 中的 Cookie 字段
   - 复制 Cookie 值

2. 保存 Cookie:
   - 将 Cookie 保存为 cookies.json 文件
   - 格式可以是字符串或 Cookie 数组
   
   示例格式 1 (字符串):
   {
     "cookie1": "value1",
     "cookie2": "value2"
   }
   
   示例格式 2 (数组):
   [
     {"name": "cookie1", "value": "value1", "domain": ".xiaohongshu.com"},
     {"name": "cookie2", "value": "value2", "domain": ".xiaohongshu.com"}
   ]

3. 放置位置:
   - 将 cookies.json 放在脚本同目录下
   - 或在配置中指定路径: config.COOKIE_FILE = './your_cookies.json'
""")


if __name__ == '__main__':
    import sys
    
    print("小红书高并发采集器")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        example_name = sys.argv[1]
    else:
        print("\n请选择要运行的示例:")
        print("1. 采集单个商品详情")
        print("2. 批量采集商品详情")
        print("3. 采集商铺商品列表")
        print("4. 完整工作流（推荐）")
        print("5. 自定义配置")
        print("6. Cookie 设置指南")
        print()
        
        example_name = input("请输入示例编号 (1-6): ").strip()
    
    examples = {
        '1': example_1_single_product,
        '2': example_2_batch_products,
        '3': example_3_store_products,
        '4': example_4_full_workflow,
        '5': example_5_custom_config,
        '6': setup_cookie,
    }
    
    if example_name in examples:
        if example_name == '6':
            setup_cookie()
        else:
            asyncio.run(examples[example_name]())
    else:
        print("❌ 无效的示例编号")
