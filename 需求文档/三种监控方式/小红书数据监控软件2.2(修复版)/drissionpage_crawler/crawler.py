"""
小红书高并发采集系统 - 基于 DrissionPage DOM
Xiaohongshu High-Concurrency Crawler System

独立系统，不依赖原有 Chrome 插件
采用 DOM 方式模拟真实用户操作，最安全
"""

import asyncio
import json
import logging
import os
import random
import re
import time
from datetime import datetime
from typing import Dict, List, Optional
from html import unescape

from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.errors import ElementNotFoundError, PageDisconnectedError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CrawlerConfig:
    """采集配置"""
    
    BROWSER_PATH = None
    USER_DATA_DIR = './browser_profiles'
    DEBUG_PORT_BASE = 9200
    
    MAX_CONCURRENCY = 5
    PAGE_LOAD_TIMEOUT = 15
    ELEMENT_WAIT_TIMEOUT = 10
    RETRY_TIMES = 3
    RETRY_DELAY = 2
    
    MIN_DELAY = 1.0
    MAX_DELAY = 3.0
    SCROLL_PAUSE = 0.8
    MAX_SCROLLS = 15
    
    COOKIE_FILE = './cookies.json'
    
    @classmethod
    def get_browser_port(cls, instance_id: int) -> int:
        return cls.DEBUG_PORT_BASE + instance_id


class BrowserManager:
    """浏览器实例管理器"""
    
    def __init__(self, instance_id: int):
        self.id = instance_id
        self.page: Optional[ChromiumPage] = None
        self.is_busy = False
        self.success_count = 0
        self.fail_count = 0
    
    def init(self, config: CrawlerConfig) -> bool:
        try:
            co = ChromiumOptions()
            
            if config.BROWSER_PATH:
                co.set_browser_path(config.BROWSER_PATH)
            
            profile_dir = f"{config.USER_DATA_DIR}/profile_{self.id}"
            os.makedirs(profile_dir, exist_ok=True)
            co.set_user_data_path(profile_dir)
            
            co.set_local_port(config.get_browser_port(self.id))
            
            co.set_argument('--disable-gpu')
            co.set_argument('--disable-dev-shm-usage')
            co.set_argument('--no-sandbox')
            co.set_argument('--disable-blink-features=AutomationControlled')
            co.set_argument('--disable-extensions')
            
            co.auto_port()
            
            self.page = ChromiumPage(addr_or_opts=co)
            
            logger.info(f"✅ 浏览器 {self.id} 初始化成功 (端口: {config.get_browser_port(self.id)})")
            return True
            
        except Exception as e:
            logger.error(f"❌ 浏览器 {self.id} 初始化失败: {e}")
            return False
    
    def load_cookies(self, cookie_file: str) -> bool:
        try:
            if not os.path.exists(cookie_file):
                return False
            
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            if isinstance(cookies, list):
                for cookie in cookies:
                    self.page.set.cookies(cookie)
            else:
                for name, value in cookies.items():
                    self.page.set.cookies({'name': name, 'value': value, 'domain': '.xiaohongshu.com'})
            
            self.page.refresh()
            time.sleep(2)
            logger.info(f"✅ 浏览器 {self.id} Cookie 加载成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 浏览器 {self.id} Cookie 加载失败: {e}")
            return False
    
    def close(self):
        try:
            if self.page:
                self.page.quit()
                logger.info(f"🔒 浏览器 {self.id} 已关闭")
        except Exception as e:
            logger.error(f"❌ 关闭浏览器 {self.id} 失败: {e}")


class DOMParser:
    """DOM 数据解析器"""
    
    @staticmethod
    def extract_goods_id_from_eaglet(eaglet_str: str) -> Optional[str]:
        """从 data-eaglet 属性提取商品ID"""
        try:
            decoded = unescape(eaglet_str)
            data = json.loads(decoded)
            return data.get('mallGoodsTarget', {}).get('value', {}).get('goodsId')
        except:
            return None
    
    @staticmethod
    def parse_price(price_text: str) -> Optional[float]:
        """解析价格：从 price-text2 和 price-text3 组合"""
        try:
            if not price_text:
                return None
            price_text = price_text.strip().replace('\n', '').replace(' ', '')
            match = re.search(r'([\d.]+)', price_text)
            return float(match.group(1)) if match else None
        except:
            return None
    
    @staticmethod
    def parse_sales(text: str) -> Optional[int]:
        """解析销量"""
        if not text:
            return None
        
        text = text.strip()
        
        match = re.search(r'([\d.]+)(万|千)?\+?', text)
        if match:
            num = float(match.group(1))
            unit = match.group(2)
            if unit == '万':
                num *= 10000
            elif unit == '千':
                num *= 1000
            return int(num)
        
        match = re.search(r'(\d+)', text)
        return int(match.group(1)) if match else None


class StoreCollector:
    """商铺商品列表采集器"""
    
    def __init__(self, browser: BrowserManager, config: CrawlerConfig):
        self.browser = browser
        self.config = config
        self.parser = DOMParser()
    
    def collect(self, store_url: str) -> List[Dict]:
        """采集商铺商品列表"""
        products = []
        
        try:
            logger.info(f"🏪 打开商铺: {store_url}")
            self.browser.page.get(store_url)
            time.sleep(random.uniform(3, 5))
            
            self._scroll_to_load()
            
            products = self._extract_products()
            
            logger.info(f"✅ 商铺采集完成: {len(products)} 个商品")
            
        except Exception as e:
            logger.error(f"❌ 商铺采集失败: {e}")
        
        return products
    
    def _scroll_to_load(self):
        """模拟用户滚动加载"""
        for i in range(self.config.MAX_SCROLLS):
            old_height = self.browser.page.run_js('return document.documentElement.scrollHeight')
            
            scroll_pixels = random.randint(300, 600)
            self.browser.page.run_js(f'window.scrollBy(0, {scroll_pixels})')
            time.sleep(random.uniform(0.5, 1.2))
            
            new_height = self.browser.page.run_js('return document.documentElement.scrollHeight')
            
            if new_height == old_height:
                logger.info(f"✅ 滚动加载完成 (第 {i+1} 次)")
                break
            
            if (i + 1) % 3 == 0:
                time.sleep(random.uniform(1, 2))
    
    def _extract_products(self) -> List[Dict]:
        """提取商品列表 - DOM 方式"""
        products = []
        
        # 等待商品标题加载完成
        try:
            self.browser.page.ele('.goods-title', timeout=self.config.ELEMENT_WAIT_TIMEOUT)
            logger.info("✅ 商品标题已加载")
        except:
            logger.warning("⚠️ 未找到商品标题，尝试继续提取...")
        
        # 使用 DrissionPage 原生方法获取所有包含 data-eaglet 的元素
        eaglet_elems = self.browser.page.eles('@data-eaglet')
        logger.info(f"🔍 找到 {len(eaglet_elems)} 个 data-eaglet 元素")
        
        # 过滤出包含 mallGoodsTarget 的商品卡片
        for elem in eaglet_elems:
            try:
                eaglet_str = elem.attr('data-eaglet')
                if not eaglet_str or 'mallGoodsTarget' not in eaglet_str:
                    continue
                
                product = {}
                
                # 从 data-eaglet 提取商品ID
                goods_id = self.parser.extract_goods_id_from_eaglet(eaglet_str)
                if goods_id:
                    product['product_id'] = goods_id
                    product['product_url'] = f'https://www.xiaohongshu.com/goods-detail/{goods_id}'
                
                # 从子元素中提取商品名称
                title_elem = elem.ele('.goods-title', timeout=1)
                if title_elem:
                    product['product_name'] = title_elem.text.strip()
                
                # 提取价格信息
                price_container = elem.ele('.price-container', timeout=1)
                if price_container:
                    deal_price = price_container.ele('.deal-price', timeout=1)
                    if deal_price:
                        price_parts = []
                        price_text2 = deal_price.ele('.price-text2', timeout=1)
                        price_text3 = deal_price.ele('.price-text3', timeout=1)
                        if price_text2:
                            price_parts.append(price_text2.text.strip())
                        if price_text3:
                            price_parts.append(price_text3.text.strip())
                        price_text = ''.join(price_parts)
                        product['product_price'] = self.parser.parse_price(price_text)
                    
                    original_price = price_container.ele('.price-text4', timeout=1)
                    if original_price:
                        product['original_price'] = self.parser.parse_price(original_price.text)
                
                # 提取标签
                tag_wrapper = elem.ele('.tag-wrapper', timeout=1)
                if tag_wrapper:
                    tags = []
                    tag_texts = tag_wrapper.eles('.text')
                    for tag in tag_texts:
                        tags.append(tag.text.strip())
                    if tags:
                        product['tags'] = tags
                
                if product.get('product_id'):
                    products.append(product)
                    
            except Exception as e:
                logger.debug(f"提取商品失败: {e}")
                continue
        
        return products


class ProductCollector:
    """商品详情采集器"""
    
    def __init__(self, browser: BrowserManager, config: CrawlerConfig):
        self.browser = browser
        self.config = config
        self.parser = DOMParser()
    
    def collect(self, product_url: str) -> Dict:
        """采集商品详情"""
        result = {
            'success': False,
            'url': product_url,
            'timestamp': datetime.now().isoformat(),
            'data': {}
        }
        
        try:
            logger.info(f"📦 打开商品: {product_url}")
            self.browser.page.get(product_url)
            time.sleep(random.uniform(3, 5))
            
            data = result['data']
            
            data['product_id'] = self._extract_product_id(product_url)
            data['product_name'] = self._extract_product_name()
            data['product_price'] = self._extract_product_price()
            data['product_sales'] = self._extract_product_sales()
            data['publish_time'] = self._extract_publish_time()
            
            store_info = self._extract_store_info()
            data.update(store_info)
            
            if data.get('product_name') or data.get('product_sales') is not None:
                result['success'] = True
                self.browser.success_count += 1
                logger.info(f"✅ 商品采集成功: {data.get('product_name', 'N/A')}")
            else:
                result['error'] = '未找到商品数据'
                self.browser.fail_count += 1
            
        except PageDisconnectedError:
            result['error'] = '浏览器连接断开'
            self.browser.fail_count += 1
        except Exception as e:
            result['error'] = str(e)
            self.browser.fail_count += 1
            logger.error(f"❌ 商品采集失败: {e}")
        
        return result
    
    def _extract_product_id(self, url: str) -> Optional[str]:
        match = re.search(r'goods-detail/(\w+)', url)
        return match.group(1) if match else None
    
    def _extract_product_name(self) -> Optional[str]:
        try:
            selectors = [
                'div.goods-name',
                '[class*="goods-name"]',
                'h1[class*="title"]',
                '[class*="product-name"]',
            ]
            for sel in selectors:
                elem = self.browser.page.ele(sel, timeout=2)
                if elem and elem.text.strip():
                    return elem.text.strip()
            
            # 尝试从页面标题获取
            title = self.browser.page.title
            if title and title != '商品详情':
                return title
            
            return None
        except:
            return None
    
    def _extract_product_price(self) -> Optional[float]:
        try:
            price_container = self.browser.page.ele('.price-container', timeout=2)
            if not price_container:
                return None
            
            # 获取整个价格容器的文本
            full_text = price_container.text.strip()
            
            # 从文本中提取价格（例如："¥4.99 已售177"）
            price_match = re.search(r'¥\s*([\d.]+)', full_text)
            if price_match:
                return float(price_match.group(1))
            
            return None
        except:
            return None
    
    def _extract_product_sales(self) -> Optional[int]:
        try:
            # 尝试从价格容器中提取销量
            price_container = self.browser.page.ele('.price-container', timeout=2)
            if price_container:
                full_text = price_container.text.strip()
                # 从 "已售177" 这样的文本中提取
                sales_match = re.search(r'已售\s*([\d.]+万?千?)', full_text)
                if sales_match:
                    return self.parser.parse_sales(sales_match.group(0))
            
            # 尝试其他选择器
            selectors = ['span.spu-text', '[class*="spu-text"]', '[class*="sales"]']
            for sel in selectors:
                try:
                    elem = self.browser.page.ele(sel, timeout=1)
                    if elem and elem.states.is_displayed:
                        return self.parser.parse_sales(elem.text)
                except:
                    continue
            
            return 0
        except:
            return None
    
    def _extract_publish_time(self) -> Optional[str]:
        """提取商品上架时间"""
        try:
            selectors = [
                '[class*="publish-time"]',
                '[class*="release-time"]',
                '[class*="create-time"]',
                'span[class*="time"]',
                '[class*="time-info"]',
            ]
            for sel in selectors:
                try:
                    elem = self.browser.page.ele(sel, timeout=1)
                    if elem and elem.text.strip():
                        time_text = elem.text.strip()
                        # 检查是否包含时间信息
                        if re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', time_text):
                            return time_text
                except:
                    continue
            
            # 尝试从页面文本中查找时间模式
            page_text = self.browser.page.text
            time_patterns = [
                r'上架时间[：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
                r'发布时间[：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
            ]
            for pattern in time_patterns:
                match = re.search(pattern, page_text)
                if match:
                    return match.group(1)
            
            return None
        except:
            return None
    
    def _extract_store_info(self) -> Dict:
        info = {'store_name': None, 'store_sales': None, 'store_followers': None}
        
        try:
            # 尝试从 .seller-container 提取商铺信息
            seller_container = self.browser.page.ele('.seller-container', timeout=2)
            if seller_container:
                full_text = seller_container.text.strip()
                
                # 提取商铺名称（通常是第一行）
                lines = full_text.split('\n')
                if lines:
                    info['store_name'] = lines[0].strip()
                
                # 提取粉丝数
                followers_match = re.search(r'粉丝数\s*(\d+)', full_text)
                if followers_match:
                    info['store_followers'] = int(followers_match.group(1))
                
                # 提取商铺总销量
                store_sales_match = re.search(r'已售\s*(\d+)', full_text)
                if store_sales_match:
                    info['store_sales'] = int(store_sales_match.group(1))
            
            # 备用方案：尝试其他选择器
            if not info['store_name']:
                for sel in ['.shop-info [class*="name"]', '[class*="shop-name"]', '[class*="store-name"]']:
                    try:
                        elem = self.browser.page.ele(sel, timeout=1)
                        if elem and elem.text.strip():
                            info['store_name'] = elem.text.strip()
                            break
                    except:
                        continue
            
        except:
            pass
        
        return info


class HighConcurrencyCrawler:
    """高并发采集调度器"""
    
    def __init__(self, config: CrawlerConfig = None):
        self.config = config or CrawlerConfig()
        self.browsers: List[BrowserManager] = []
        self.results: List[Dict] = []
    
    def init(self, concurrency: int = None):
        """初始化浏览器池"""
        concurrency = concurrency or self.config.MAX_CONCURRENCY
        logger.info(f"🚀 初始化采集器，并发数: {concurrency}")
        
        for i in range(concurrency):
            browser = BrowserManager(i)
            if browser.init(self.config):
                browser.load_cookies(self.config.COOKIE_FILE)
                self.browsers.append(browser)
        
        if not self.browsers:
            raise Exception("没有可用的浏览器实例")
        
        logger.info(f"✅ 浏览器池就绪: {len(self.browsers)} 个实例")
    
    def collect_store(self, store_url: str) -> List[Dict]:
        """采集商铺商品列表"""
        browser = self.browsers[0]
        collector = StoreCollector(browser, self.config)
        return collector.collect(store_url)
    
    def collect_products(self, product_urls: List[str]) -> List[Dict]:
        """高并发采集商品详情"""
        logger.info(f"🎯 开始采集 {len(product_urls)} 个商品")
        
        results = []
        
        for i, url in enumerate(product_urls):
            browser = self.browsers[i % len(self.browsers)]
            collector = ProductCollector(browser, self.config)
            
            result = self._collect_with_retry(collector, url)
            results.append(result)
            
            if i < len(product_urls) - 1:
                time.sleep(random.uniform(self.config.MIN_DELAY, self.config.MAX_DELAY))
            
            progress = (i + 1) / len(product_urls) * 100
            logger.info(f"📊 进度: {i+1}/{len(product_urls)} ({progress:.1f}%)")
        
        self.results.extend([r for r in results if r.get('success')])
        logger.info(f"✅ 采集完成: {len(self.results)}/{len(product_urls)}")
        
        return results
    
    def _collect_with_retry(self, collector: ProductCollector, url: str) -> Dict:
        """带重试的采集"""
        last_error = None
        
        for attempt in range(self.config.RETRY_TIMES):
            try:
                result = collector.collect(url)
                if result.get('success'):
                    return result
                last_error = result.get('error', '未知错误')
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"⚠️ 失败 (尝试 {attempt+1}/{self.config.RETRY_TIMES}): {e}")
            
            if attempt < self.config.RETRY_TIMES - 1:
                time.sleep(self.config.RETRY_DELAY * (attempt + 1))
        
        return {
            'success': False,
            'url': url,
            'error': last_error,
            'timestamp': datetime.now().isoformat()
        }
    
    def save_results(self, output_file: str = None):
        """保存结果"""
        if not output_file:
            output_file = f'results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 结果已保存: {output_file}")
    
    def close(self):
        """关闭所有浏览器"""
        logger.info("🔒 关闭所有浏览器...")
        for browser in self.browsers:
            browser.close()
        self.browsers.clear()
