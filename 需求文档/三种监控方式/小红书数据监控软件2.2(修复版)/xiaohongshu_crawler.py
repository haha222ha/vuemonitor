"""
小红书高并发采集器 - 基于 DrissionPage DOM
Xiaohongshu High-Concurrency Crawler using DrissionPage

核心特性:
1. 基于 DrissionPage 的 DOM 解析，无需注入 JS
2. 多浏览器实例并发采集
3. 自动重试和异常处理
4. 支持商铺商品列表和商品详情采集
"""

import asyncio
import json
import logging
import os
import random
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.errors import ElementNotFoundError, PageDisconnectedError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('xiaohongshu_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class XiaohongshuCrawlerConfig:
    """采集配置类"""
    
    # 浏览器配置
    BROWSER_PATH = None  # Chrome/Edge 可执行文件路径，None 则自动检测
    USER_DATA_DIR = './browser_data'  # 浏览器用户数据目录
    DEBUG_PORT = 9222  # 浏览器调试端口
    
    # 并发配置
    MAX_CONCURRENCY = 5  # 最大并发数
    MIN_CONCURRENCY = 2  # 最小并发数
    
    # 超时配置
    PAGE_LOAD_TIMEOUT = 15  # 页面加载超时（秒）
    ELEMENT_WAIT_TIMEOUT = 10  # 元素等待超时（秒）
    RETRY_TIMES = 3  # 重试次数
    RETRY_DELAY = 2  # 重试延迟（秒）
    
    # 延迟配置（防封禁）
    MIN_REQUEST_DELAY = 1.0  # 最小请求延迟
    MAX_REQUEST_DELAY = 3.0  # 最大请求延迟
    BATCH_DELAY = 5.0  # 批次间延迟
    
    # 采集配置
    SCROLL_PAUSE_TIME = 0.5  # 滚动暂停时间
    MAX_SCROLL_TIMES = 10  # 最大滚动次数
    
    # Cookie 配置
    COOKIE_FILE = './cookies.json'  # Cookie 文件路径


class BrowserInstance:
    """浏览器实例管理器"""
    
    def __init__(self, instance_id: int):
        self.instance_id = instance_id
        self.page: Optional[ChromiumPage] = None
        self.is_busy = False
        self.last_used_time = 0
        self.success_count = 0
        self.error_count = 0
        
    async def initialize(self, config: XiaohongshuCrawlerConfig):
        """初始化浏览器实例"""
        try:
            co = ChromiumOptions()
            
            # 设置浏览器路径
            if config.BROWSER_PATH:
                co.set_browser_path(config.BROWSER_PATH)
            
            # 设置用户数据目录
            co.set_user_data_path(f"{config.USER_DATA_DIR}/instance_{self.instance_id}")
            
            # 设置调试端口
            co.set_local_port(config.DEBUG_PORT + self.instance_id)
            
            # 优化配置
            co.set_argument('--disable-gpu')
            co.set_argument('--disable-dev-shm-usage')
            co.set_argument('--no-sandbox')
            co.set_argument('--disable-extensions')
            co.set_argument('--disable-images')  # 禁用图片加载提升速度
            
            # 创建页面对象
            self.page = ChromiumPage(addr_or_opts=co)
            
            # 设置超时（DrissionPage 4.x API）
            self.page.set.timeouts(base=config.PAGE_LOAD_TIMEOUT)
            
            logger.info(f"✅ 浏览器实例 {self.instance_id} 初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 浏览器实例 {self.instance_id} 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def load_cookie(self, cookie_file: str):
        """加载 Cookie"""
        try:
            if os.path.exists(cookie_file):
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                
                if isinstance(cookies, list):
                    for cookie in cookies:
                        self.page.set.cookies(cookie)
                else:
                    self.page.set.cookies(cookies)
                
                self.page.refresh()
                await asyncio.sleep(2)
                logger.info(f"✅ 浏览器实例 {self.instance_id} Cookie 加载成功")
                return True
            else:
                logger.warning(f"⚠️ Cookie 文件不存在: {cookie_file}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 加载 Cookie 失败: {e}")
            return False
    
    async def close(self):
        """关闭浏览器实例"""
        try:
            if self.page:
                self.page.quit()
                logger.info(f"🔒 浏览器实例 {self.instance_id} 已关闭")
        except Exception as e:
            logger.error(f"❌ 关闭浏览器实例 {self.instance_id} 失败: {e}")


class XiaohongshuDOMParser:
    """小红书 DOM 解析器 - 基于 DrissionPage"""
    
    @staticmethod
    def extract_product_id_from_url(url: str) -> Optional[str]:
        """从 URL 提取商品 ID"""
        patterns = [
            r'goods-detail/(\w+)',
            r'id=(\w+)',
            r'/item/(\w+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    @staticmethod
    def parse_sales_number(text: str) -> Optional[int]:
        """解析销量数字"""
        if not text:
            return None
        
        text = text.strip()
        
        # 匹配 "已售1.9万+" 格式
        match = re.search(r'已售([\d.]+)(万|千)?', text)
        if match:
            number = float(match.group(1))
            unit = match.group(2)
            
            if unit == '万':
                number *= 10000
            elif unit == '千':
                number *= 1000
            
            return int(number)
        
        # 匹配纯数字
        match = re.search(r'(\d+)', text)
        if match:
            return int(match.group(1))
        
        return None
    
    @staticmethod
    def parse_price(text: str) -> Optional[float]:
        """解析价格"""
        if not text:
            return None
        
        text = text.strip()
        
        # 匹配价格格式 ¥58 或 58.00
        match = re.search(r'¥?\s*([\d.]+)', text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        
        return None
    
    @staticmethod
    def parse_followers(text: str) -> Optional[int]:
        """解析粉丝数"""
        if not text:
            return None
        
        text = text.strip()
        
        # 匹配 "16.1万" 格式
        match = re.search(r'([\d.]+)(万|千)?', text)
        if match:
            number = float(match.group(1))
            unit = match.group(2)
            
            if unit == '万':
                number *= 10000
            elif unit == '千':
                number *= 1000
            
            return int(number)
        
        return None


class ProductDetailCollector:
    """商品详情采集器"""
    
    def __init__(self, browser: BrowserInstance, config: XiaohongshuCrawlerConfig):
        self.browser = browser
        self.config = config
        self.parser = XiaohongshuDOMParser()
    
    async def collect(self, product_url: str) -> Dict:
        """采集单个商品详情"""
        result = {
            'success': False,
            'url': product_url,
            'timestamp': datetime.now().isoformat(),
            'data': {}
        }
        
        try:
            # 导航到商品页面
            self.browser.page.get(product_url)
            await asyncio.sleep(random.uniform(2, 4))
            
            # 等待页面加载
            try:
                self.browser.page.wait.doc_loaded(timeout=self.config.ELEMENT_WAIT_TIMEOUT)
            except:
                logger.warning(f"⚠️ 页面加载超时: {product_url}")
            
            # 提取商品 ID
            product_id = self.parser.extract_product_id_from_url(product_url)
            result['data']['product_id'] = product_id
            
            # 提取商品名称
            result['data']['product_name'] = await self._extract_product_name()
            
            # 提取商品价格
            result['data']['product_price'] = await self._extract_product_price()
            
            # 提取商品销量
            result['data']['product_sales'] = await self._extract_product_sales()
            
            # 提取店铺信息
            store_info = await self._extract_store_info()
            result['data'].update(store_info)
            
            # 验证数据
            if result['data'].get('product_name') or result['data'].get('product_sales'):
                result['success'] = True
                self.browser.success_count += 1
                logger.info(f"✅ 商品采集成功: {result['data'].get('product_name', 'N/A')}")
            else:
                result['error'] = '未找到商品数据'
                self.browser.error_count += 1
                logger.warning(f"⚠️ 商品数据为空: {product_url}")
            
        except PageDisconnectedError:
            result['error'] = '浏览器连接断开'
            self.browser.error_count += 1
            logger.error(f"❌ 浏览器连接断开: {product_url}")
            
        except Exception as e:
            result['error'] = str(e)
            self.browser.error_count += 1
            logger.error(f"❌ 商品采集失败: {product_url}, 错误: {e}")
        
        return result
    
    async def _extract_product_name(self) -> Optional[str]:
        """提取商品名称"""
        try:
            selectors = [
                'div.goods-name',
                '[class*="goods-name"]',
                'h1[class*="title"]',
                'div[class*="product-title"]',
            ]
            
            for selector in selectors:
                try:
                    elem = self.browser.page.ele(selector, timeout=2)
                    if elem and elem.text.strip():
                        return elem.text.strip()
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"提取商品名称失败: {e}")
            return None
    
    async def _extract_product_price(self) -> Optional[float]:
        """提取商品价格"""
        try:
            # 查找价格容器
            price_container = self.browser.page.ele('.price-container', timeout=2)
            if not price_container:
                return None
            
            # 查找价格元素
            price_selectors = [
                '[class*="price"] span',
                '.priceDecimalPart_price2',
                'span[class*="price"]',
            ]
            
            for selector in price_selectors:
                try:
                    elem = price_container.ele(selector, timeout=1)
                    if elem:
                        return self.parser.parse_price(elem.text)
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"提取商品价格失败: {e}")
            return None
    
    async def _extract_product_sales(self) -> Optional[int]:
        """提取商品销量"""
        try:
            # 优先检查 .price-container 中的 .spu-text
            price_container = self.browser.page.ele('.price-container', timeout=2)
            if price_container:
                try:
                    spu_text = price_container.ele('.spu-text', timeout=1)
                    if spu_text:
                        return self.parser.parse_sales_number(spu_text.text)
                except:
                    # 没有 .spu-text 元素，销量为 0
                    return 0
            
            # 备用选择器
            sales_selectors = [
                'span.spu-text',
                '[class*="spu-text"]',
                'span[class*="spu"]',
            ]
            
            for selector in sales_selectors:
                try:
                    elem = self.browser.page.ele(selector, timeout=1)
                    if elem and elem.states.is_displayed:
                        return self.parser.parse_sales_number(elem.text)
                except:
                    continue
            
            # 所有选择器都找不到，返回 0
            return 0
            
        except Exception as e:
            logger.debug(f"提取商品销量失败: {e}")
            return None
    
    async def _extract_store_info(self) -> Dict:
        """提取店铺信息"""
        store_info = {
            'store_name': None,
            'store_sales': None,
            'store_followers': None
        }
        
        try:
            # 提取店铺名称
            store_name_selectors = [
                '.seller-container [class*="name"]',
                '.shop-info [class*="name"]',
                '[class*="store-name"]',
                '[class*="shop-name"]',
            ]
            
            for selector in store_name_selectors:
                try:
                    elem = self.browser.page.ele(selector, timeout=2)
                    if elem and elem.text.strip():
                        store_info['store_name'] = elem.text.strip()
                        break
                except:
                    continue
            
            # 提取店铺销量
            store_sales_selectors = [
                '.seller-container .sub-title',
                '.shop-info .sub-title',
                '[class*="sub-title"]',
            ]
            
            for selector in store_sales_selectors:
                try:
                    elems = self.browser.page.eles(selector)
                    for elem in elems:
                        text = elem.text.strip()
                        if any(keyword in text for keyword in ['已售', '月销', '销量']):
                            # 确保不在价格容器内
                            if not elem.parent(2).ele('.price-container', timeout=0.5):
                                sales = self.parser.parse_sales_number(text)
                                if sales:
                                    store_info['store_sales'] = sales
                                    break
                except:
                    continue
            
            # 提取店铺粉丝数
            try:
                follower_elem = self.browser.page.ele('[class*="follower"]', timeout=2)
                if follower_elem:
                    store_info['store_followers'] = self.parser.parse_followers(follower_elem.text)
            except:
                pass
            
        except Exception as e:
            logger.debug(f"提取店铺信息失败: {e}")
        
        return store_info


class StoreProductListCollector:
    """商铺商品列表采集器"""
    
    def __init__(self, browser: BrowserInstance, config: XiaohongshuCrawlerConfig):
        self.browser = browser
        self.config = config
        self.parser = XiaohongshuDOMParser()
    
    async def collect(self, store_url: str) -> List[Dict]:
        """采集商铺商品列表"""
        products = []
        
        try:
            # 导航到商铺页面
            self.browser.page.get(store_url)
            await asyncio.sleep(random.uniform(3, 5))
            
            # 滚动加载所有商品
            await self._scroll_to_load_all()
            
            # 提取商品列表
            products = await self._extract_product_list()
            
            logger.info(f"✅ 商铺商品列表采集成功: {len(products)} 个商品")
            
        except Exception as e:
            logger.error(f"❌ 商铺商品列表采集失败: {e}")
        
        return products
    
    async def _scroll_to_load_all(self):
        """滚动加载所有内容"""
        scroll_count = 0
        
        while scroll_count < self.config.MAX_SCROLL_TIMES:
            # 获取当前页面高度
            old_height = self.browser.page.run_js('return document.body.scrollHeight')
            
            # 滚动到底部
            self.browser.page.scroll.to_bottom()
            await asyncio.sleep(self.config.SCROLL_PAUSE_TIME)
            
            # 获取新高度
            new_height = self.browser.page.run_js('return document.body.scrollHeight')
            
            # 如果高度没有变化，说明已经加载完所有内容
            if new_height == old_height:
                logger.info(f"✅ 滚动加载完成，共滚动 {scroll_count + 1} 次")
                break
            
            scroll_count += 1
    
    async def _extract_product_list(self) -> List[Dict]:
        """提取商品列表"""
        products = []
        
        try:
            # 使用 .goods-card 选择器（商铺页面的商品卡片）
            product_items = self.browser.page.eles('.goods-card')
            
            if not product_items:
                product_items = self.browser.page.eles('[class*="goods-card"]')
            
            logger.info(f"🔍 找到 {len(product_items)} 个商品卡片")
            
            for item in product_items:
                try:
                    product_data = {}
                    
                    # 从 data-eaglet 属性中提取 goodsId
                    eaglet_attr = item.attr('data-eaglet')
                    if eaglet_attr:
                        import json as json_module
                        try:
                            eaglet_data = json_module.loads(eaglet_attr.replace('&quot;', '"'))
                            mall_goods = eaglet_data.get('mallGoodsTarget', {}).get('value', {})
                            goods_id = mall_goods.get('goodsId')
                            if goods_id:
                                product_data['product_id'] = goods_id
                                product_data['product_url'] = f'https://www.xiaohongshu.com/goods-detail/{goods_id}'
                        except:
                            pass
                    
                    # 提取商品名称
                    name_elem = item.ele('.goods-title', timeout=0.5)
                    if name_elem:
                        product_data['product_name'] = name_elem.text.strip()
                    
                    # 提取商品价格
                    price_container = item.ele('.price-container', timeout=0.5)
                    if price_container:
                        deal_price = price_container.ele('.deal-price', timeout=0.5)
                        if deal_price:
                            price_text = deal_price.text.strip()
                            product_data['product_price'] = self.parser.parse_price(price_text)
                    
                    # 提取销量（如果有）
                    sales_elem = item.ele('[class*="sold"]', timeout=0.5)
                    if not sales_elem:
                        sales_elem = item.ele('[class*="sales"]', timeout=0.5)
                    if sales_elem:
                        product_data['product_sales'] = self.parser.parse_sales_number(sales_elem.text)
                    
                    if product_data.get('product_id'):
                        products.append(product_data)
                        
                except Exception as e:
                    logger.debug(f"提取单个商品信息失败: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"提取商品列表失败: {e}")
        
        return products


class XiaohongshuHighConcurrencyCrawler:
    """小红书高并发采集器主类"""
    
    def __init__(self, config: XiaohongshuCrawlerConfig = None):
        self.config = config or XiaohongshuCrawlerConfig()
        self.browsers: List[BrowserInstance] = []
        self.results: List[Dict] = []
        self.is_running = False
    
    async def initialize(self, concurrency: int = None):
        """初始化采集器"""
        concurrency = concurrency or self.config.MAX_CONCURRENCY
        
        logger.info(f"🚀 初始化高并发采集器，并发数: {concurrency}")
        
        # 创建浏览器实例
        for i in range(concurrency):
            browser = BrowserInstance(i)
            success = await browser.initialize(self.config)
            
            if success:
                # 加载 Cookie
                await browser.load_cookie(self.config.COOKIE_FILE)
                self.browsers.append(browser)
            else:
                logger.error(f"❌ 浏览器实例 {i} 初始化失败")
        
        if not self.browsers:
            raise Exception("没有可用的浏览器实例")
        
        logger.info(f"✅ 采集器初始化完成，可用浏览器实例: {len(self.browsers)}")
    
    async def collect_product_details(self, product_urls: List[str]) -> List[Dict]:
        """高并发采集商品详情"""
        self.is_running = True
        results = []
        
        logger.info(f"🎯 开始采集 {len(product_urls)} 个商品详情")
        
        # 创建任务队列
        tasks = []
        for i, url in enumerate(product_urls):
            browser = self.browsers[i % len(self.browsers)]
            collector = ProductDetailCollector(browser, self.config)
            task = self._collect_with_retry(collector, url, browser)
            tasks.append(task)
            
            # 添加随机延迟
            if i > 0:
                await asyncio.sleep(random.uniform(self.config.MIN_REQUEST_DELAY, self.config.MAX_REQUEST_DELAY))
        
        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"❌ 采集异常: {result}")
            elif result.get('success'):
                valid_results.append(result)
        
        self.results.extend(valid_results)
        self.is_running = False
        
        logger.info(f"✅ 商品详情采集完成，成功: {len(valid_results)}/{len(product_urls)}")
        return valid_results
    
    async def collect_store_products(self, store_url: str) -> List[Dict]:
        """采集商铺商品列表"""
        logger.info(f"🏪 开始采集商铺商品列表: {store_url}")
        
        # 使用第一个浏览器实例
        browser = self.browsers[0]
        collector = StoreProductListCollector(browser, self.config)
        
        products = await collector.collect(store_url)
        
        logger.info(f"✅ 商铺商品列表采集完成，共 {len(products)} 个商品")
        return products
    
    async def _collect_with_retry(self, collector: ProductDetailCollector, url: str, browser: BrowserInstance) -> Dict:
        """带重试的采集"""
        last_error = None
        
        for attempt in range(self.config.RETRY_TIMES):
            try:
                browser.is_busy = True
                result = await collector.collect(url)
                
                if result.get('success'):
                    return result
                
                last_error = result.get('error', '未知错误')
                logger.warning(f"⚠️ 采集失败 (尝试 {attempt + 1}/{self.config.RETRY_TIMES}): {last_error}")
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"❌ 采集异常 (尝试 {attempt + 1}/{self.config.RETRY_TIMES}): {e}")
            
            finally:
                browser.is_busy = False
            
            # 重试延迟
            if attempt < self.config.RETRY_TIMES - 1:
                await asyncio.sleep(self.config.RETRY_DELAY * (attempt + 1))
        
        return {
            'success': False,
            'url': url,
            'error': last_error,
            'timestamp': datetime.now().isoformat()
        }
    
    async def save_results(self, output_file: str = None):
        """保存采集结果"""
        if not output_file:
            output_file = f'xiaohongshu_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 采集结果已保存: {output_file}")
            
        except Exception as e:
            logger.error(f"❌ 保存结果失败: {e}")
    
    async def close(self):
        """关闭所有浏览器实例"""
        logger.info("🔒 关闭所有浏览器实例...")
        
        tasks = [browser.close() for browser in self.browsers]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        self.browsers.clear()
        logger.info("✅ 所有浏览器实例已关闭")


async def main():
    """主函数示例"""
    # 创建配置
    config = XiaohongshuCrawlerConfig()
    config.MAX_CONCURRENCY = 3
    
    # 创建采集器
    crawler = XiaohongshuHighConcurrencyCrawler(config)
    
    try:
        # 初始化
        await crawler.initialize()
        
        # 示例 1: 采集单个商品详情
        product_urls = [
            'https://www.xiaohongshu.com/goods-detail/67bbc5bfeef1820001f83a2d'
        ]
        
        results = await crawler.collect_product_details(product_urls)
        
        # 示例 2: 采集商铺商品列表
        store_url = 'https://www.xiaohongshu.com/vendor/66c9df4702383e001535d18a'
        store_products = await crawler.collect_store_products(store_url)
        
        # 保存结果
        await crawler.save_results()
        
    except Exception as e:
        logger.error(f"❌ 采集过程失败: {e}")
    
    finally:
        await crawler.close()


if __name__ == '__main__':
    asyncio.run(main())
