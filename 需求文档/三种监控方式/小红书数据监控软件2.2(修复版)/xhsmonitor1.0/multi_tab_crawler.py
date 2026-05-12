"""
小红书多标签页并发采集器
单浏览器 + 多标签页并发采集
"""

import json
import logging
import os
import random
import re
import time
from datetime import datetime
from typing import Dict, List, Optional
from html import unescape
from concurrent.futures import ThreadPoolExecutor, as_completed

from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.errors import ElementNotFoundError, PageDisconnectedError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('multi_tab_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def infer_shelf_year(month_day_str: str, current_date: datetime = None) -> str:
    """
    根据月日字符串推断完整日期（含年份）
    
    逻辑：
    - 如果月份 > 当前月份 → 上一年
    - 如果月份 <= 当前月份 → 今年
    
    Args:
        month_day_str: 格式如 "09月20日" 或 "04月17日"
        current_date: 当前日期，默认为今天
    
    Returns:
        完整日期字符串，格式 "YYYY-MM-DD"
    """
    if current_date is None:
        current_date = datetime.now()
    
    try:
        match = re.search(r'(\d{1,2})月(\d{1,2})日', month_day_str)
        if not match:
            return month_day_str
        
        month = int(match.group(1))
        day = int(match.group(2))
        
        current_year = current_date.year
        current_month = current_date.month
        
        if month > current_month:
            year = current_year - 1
        else:
            year = current_year
        
        return f"{year}-{month:02d}-{day:02d}"
        
    except Exception as e:
        logger.debug(f"日期解析错误: {month_day_str}, 错误: {e}")
        return month_day_str


class MultiTabConfig:
    """多标签页采集配置"""
    
    BROWSER_PATH = None
    USER_DATA_DIR = './browser_profiles/multi_tab'
    DEBUG_PORT = 9300
    
    MAX_TABS = 5  # 最大标签页数
    PAGE_LOAD_TIMEOUT = 15
    ELEMENT_WAIT_TIMEOUT = 10
    RETRY_TIMES = 3
    RETRY_DELAY = 2
    
    MIN_DELAY = 0.5  # 标签页间延迟
    MAX_DELAY = 1.5
    SCROLL_PAUSE = 0.8
    MAX_SCROLLS = 15
    
    COOKIE_FILE = './cookies.json'


class MultiTabBrowser:
    """单浏览器多标签页管理器"""
    
    def __init__(self, config: MultiTabConfig):
        self.config = config
        self.browser: Optional[ChromiumPage] = None
        self.tabs: Dict[int, any] = {}  # tab_id -> page object
        self.success_count = 0
        self.fail_count = 0
    
    def init(self) -> bool:
        try:
            co = ChromiumOptions()
            
            if self.config.BROWSER_PATH:
                co.set_browser_path(self.config.BROWSER_PATH)
            
            os.makedirs(self.config.USER_DATA_DIR, exist_ok=True)
            co.set_user_data_path(self.config.USER_DATA_DIR)
            co.set_local_port(self.config.DEBUG_PORT)
            
            co.set_argument('--disable-gpu')
            co.set_argument('--disable-dev-shm-usage')
            co.set_argument('--no-sandbox')
            co.set_argument('--disable-blink-features=AutomationControlled')
            
            self.browser = ChromiumPage(addr_or_opts=co)
            
            logger.info(f"✅ 浏览器初始化成功 (端口: {self.config.DEBUG_PORT})")
            return True
            
        except Exception as e:
            logger.error(f"❌ 浏览器初始化失败: {e}")
            return False
    
    def load_cookies(self, cookie_file: str) -> bool:
        try:
            if not os.path.exists(cookie_file):
                logger.warning(f"⚠️ Cookie文件不存在: {cookie_file}")
                return False
            
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            if isinstance(cookies, list):
                for cookie in cookies:
                    self.browser.set.cookies(cookie)
            
            self.browser.refresh()
            time.sleep(2)
            logger.info(f"✅ Cookie 加载成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ Cookie 加载失败: {e}")
            return False
    
    def create_tab(self) -> Optional[any]:
        """创建新标签页"""
        try:
            new_tab = self.browser.new_tab()
            tab_id = new_tab.tab_id
            self.tabs[tab_id] = new_tab
            logger.info(f"✅ 创建标签页: {tab_id} (当前共 {len(self.tabs)} 个)")
            return new_tab
        except Exception as e:
            logger.error(f"❌ 创建标签页失败: {e}")
            return None
    
    def close_tab(self, tab_id: int):
        """关闭标签页"""
        try:
            if tab_id in self.tabs:
                self.browser.close_tabs(tab_id)
                del self.tabs[tab_id]
                logger.info(f"🔒 关闭标签页: {tab_id}")
        except Exception as e:
            logger.error(f"❌ 关闭标签页失败: {e}")
    
    def close(self):
        try:
            if self.browser:
                self.browser.quit()
                logger.info(f"🔒 浏览器已关闭")
        except Exception as e:
            logger.error(f"❌ 关闭浏览器失败: {e}")


class DOMParser:
    """DOM 数据解析器"""
    
    @staticmethod
    def extract_goods_id_from_eaglet(eaglet_str: str) -> Optional[str]:
        try:
            decoded = unescape(eaglet_str)
            data = json.loads(decoded)
            return data.get('mallGoodsTarget', {}).get('value', {}).get('goodsId')
        except:
            return None
    
    @staticmethod
    def parse_price(price_text: str) -> Optional[float]:
        try:
            if not price_text:
                return None
            price_text = price_text.replace('¥', '').replace(' ', '')
            match = re.search(r'(\d+\.?\d*)', price_text)
            return float(match.group(1)) if match else None
        except:
            return None
    
    @staticmethod
    def parse_sales(sales_text: str) -> Optional[int]:
        try:
            if not sales_text:
                return 0
            if '万' in sales_text:
                match = re.search(r'([\d.]+)万', sales_text)
                return int(float(match.group(1)) * 10000) if match else 0
            match = re.search(r'(\d+)', sales_text)
            return int(match.group(1)) if match else 0
        except:
            return 0


class StoreCollector:
    """商铺商品列表采集器"""
    
    def __init__(self, page, config: MultiTabConfig):
        self.page = page
        self.config = config
        self.parser = DOMParser()
    
    def collect(self, store_url: str) -> List[Dict]:
        logger.info(f"🏪 打开商铺: {store_url}")
        self.page.get(store_url)
        time.sleep(random.uniform(3, 5))
        
        try:
            product_tab = self.page.ele('text:商品', timeout=3)
            if product_tab:
                product_tab.click()
                time.sleep(random.uniform(2, 3))
        except:
            pass
        
        self._scroll_to_load()
        products = self._extract_products()
        
        logger.info(f"✅ 商铺采集完成: {len(products)} 个商品")
        return products
    
    def _scroll_to_load(self):
        for i in range(self.config.MAX_SCROLLS):
            old_height = self.page.run_js('return document.documentElement.scrollHeight')
            scroll_pixels = random.randint(300, 600)
            self.page.run_js(f'window.scrollBy(0, {scroll_pixels})')
            time.sleep(random.uniform(0.5, 1.2))
            
            new_height = self.page.run_js('return document.documentElement.scrollHeight')
            if new_height == old_height:
                logger.info(f"✅ 滚动加载完成 (第 {i+1} 次)")
                break
            
            if (i + 1) % 3 == 0:
                time.sleep(random.uniform(1, 2))
    
    def _extract_products(self) -> List[Dict]:
        products = []
        
        try:
            self.page.ele('.goods-title', timeout=self.config.ELEMENT_WAIT_TIMEOUT)
        except:
            logger.warning("⚠️ 未找到商品标题")
        
        # 查找所有 item-group 分组（包含日期标题）
        item_groups = self.page.eles('.item-group')
        logger.info(f"🔍 找到 {len(item_groups)} 个商品分组")
        
        for group in item_groups:
            # 提取分组日期（上架时间）
            shelf_date = None
            try:
                h1_elem = group.ele('tag:h1', timeout=1)
                if h1_elem and h1_elem.text.strip():
                    shelf_date = h1_elem.text.strip()
            except:
                pass
            
            # 提取该分组下的所有商品
            eaglet_elems = group.eles('@data-eaglet')
            
            for elem in eaglet_elems:
                try:
                    eaglet_str = elem.attr('data-eaglet')
                    if not eaglet_str or 'mallGoodsTarget' not in eaglet_str:
                        continue
                    
                    product = {}
                    
                    goods_id = self.parser.extract_goods_id_from_eaglet(eaglet_str)
                    if goods_id:
                        product['product_id'] = goods_id
                        product['product_url'] = f'https://www.xiaohongshu.com/goods-detail/{goods_id}'
                    
                    title_elem = elem.ele('.goods-title', timeout=1)
                    if title_elem:
                        product['product_name'] = title_elem.text.strip()
                    
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
                            product['product_price'] = self.parser.parse_price(''.join(price_parts))
                    
                    # 添加上架时间（智能推断年份）
                    if shelf_date:
                        product['shelf_date'] = shelf_date
                        product['shelf_date_full'] = infer_shelf_year(shelf_date)
                    
                    if product.get('product_id'):
                        products.append(product)
                        
                except Exception as e:
                    logger.debug(f"提取商品失败: {e}")
                    continue
        
        return products


class ProductCollector:
    """商品详情采集器 - 单标签页"""
    
    def __init__(self, page, config: MultiTabConfig):
        self.page = page
        self.config = config
        self.parser = DOMParser()
    
    def collect(self, product_url: str, product_name: str = None, shelf_date: str = None, shelf_date_full: str = None) -> Dict:
        result = {
            'success': False,
            'url': product_url,
            'timestamp': datetime.now().isoformat(),
            'data': {}
        }
        
        try:
            self.page.get(product_url)
            time.sleep(random.uniform(2, 4))
            
            data = result['data']
            
            match = re.search(r'goods-detail/(\w+)', product_url)
            data['product_id'] = match.group(1) if match else None
            
            # 使用传入的商品名称（从商铺列表获取）
            data['product_name'] = product_name or self._extract_product_name()
            data['product_price'] = self._extract_product_price()
            data['product_sales'] = self._extract_product_sales()
            
            # 使用传入的上架时间（含完整年月日）
            data['shelf_date'] = shelf_date
            data['shelf_date_full'] = shelf_date_full
            
            store_info = self._extract_store_info()
            data.update(store_info)
            
            if data.get('product_sales') is not None:
                result['success'] = True
                logger.info(f"✅ 商品采集成功: {data.get('product_name', 'N/A')}")
            else:
                result['error'] = '未找到商品数据'
            
        except PageDisconnectedError:
            result['error'] = '浏览器连接断开'
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"❌ 商品采集失败: {e}")
        
        return result
    
    def _extract_product_name(self) -> Optional[str]:
        try:
            title = self.page.title
            if title and title != '商品详情':
                return title
            return None
        except:
            return None
    
    def _extract_product_price(self) -> Optional[float]:
        try:
            price_container = self.page.ele('.price-container', timeout=2)
            if not price_container:
                return None
            
            full_text = price_container.text.strip()
            price_match = re.search(r'¥\s*([\d.]+)', full_text)
            return float(price_match.group(1)) if price_match else None
        except:
            return None
    
    def _extract_product_sales(self) -> Optional[int]:
        try:
            price_container = self.page.ele('.price-container', timeout=2)
            if price_container:
                full_text = price_container.text.strip()
                sales_match = re.search(r'已售\s*([\d.]+万?千?)', full_text)
                if sales_match:
                    return self.parser.parse_sales(sales_match.group(0))
            
            selectors = ['span.spu-text', '[class*="spu-text"]', '[class*="sales"]']
            for sel in selectors:
                try:
                    elem = self.page.ele(sel, timeout=1)
                    if elem and elem.states.is_displayed:
                        return self.parser.parse_sales(elem.text)
                except:
                    continue
            
            return 0
        except:
            return None
    
    def _extract_store_info(self) -> Dict:
        info = {'store_name': None, 'store_sales': None, 'store_followers': None}
        
        try:
            seller_container = self.page.ele('.seller-container', timeout=2)
            if seller_container:
                full_text = seller_container.text.strip()
                lines = full_text.split('\n')
                if lines:
                    info['store_name'] = lines[0].strip()
                
                followers_match = re.search(r'粉丝数\s*(\d+)', full_text)
                if followers_match:
                    info['store_followers'] = int(followers_match.group(1))
                
                store_sales_match = re.search(r'已售\s*(\d+)', full_text)
                if store_sales_match:
                    info['store_sales'] = int(store_sales_match.group(1))
        except:
            pass
        
        return info


class MultiTabCrawler:
    """多标签页并发采集器"""
    
    def __init__(self, config: MultiTabConfig = None):
        self.config = config or MultiTabConfig()
        self.browser_manager: Optional[MultiTabBrowser] = None
        self.results: List[Dict] = []
    
    def init(self):
        """初始化浏览器"""
        self.browser_manager = MultiTabBrowser(self.config)
        if not self.browser_manager.init():
            raise Exception("浏览器初始化失败")
        
        self.browser_manager.load_cookies(self.config.COOKIE_FILE)
        logger.info(f"✅ 多标签页采集器就绪")
    
    def collect_store(self, store_url: str) -> List[Dict]:
        """采集商铺商品列表"""
        collector = StoreCollector(self.browser_manager.browser, self.config)
        return collector.collect(store_url)
    
    def collect_products_multi_tab(self, product_urls: List[Dict]) -> List[Dict]:
        """多标签页并发采集商品详情
        
        Args:
            product_urls: 商品列表，每个元素包含 product_url 和 product_name
        """
        logger.info(f"🎯 开始多标签页并发采集 {len(product_urls)} 个商品")
        
        results = []
        max_tabs = self.config.MAX_TABS
        
        # 分批处理
        for batch_start in range(0, len(product_urls), max_tabs):
            batch = product_urls[batch_start:batch_start + max_tabs]
            logger.info(f"\n📦 处理批次 {batch_start//max_tabs + 1}: {len(batch)} 个商品")
            
            # 创建标签页
            tabs = []
            for i, product in enumerate(batch):
                tab = self.browser_manager.create_tab()
                if tab:
                    tabs.append((tab, product))
                time.sleep(random.uniform(self.config.MIN_DELAY, self.config.MAX_DELAY))
            
            # 并发采集
            with ThreadPoolExecutor(max_workers=len(tabs)) as executor:
                futures = {}
                for tab, product in tabs:
                    collector = ProductCollector(tab, self.config)
                    future = executor.submit(
                        collector.collect,
                        product['product_url'],
                        product.get('product_name'),
                        product.get('shelf_date'),
                        product.get('shelf_date_full')
                    )
                    futures[future] = product
                
                for future in as_completed(futures):
                    try:
                        result = future.result(timeout=30)
                        results.append(result)
                    except Exception as e:
                        logger.error(f"❌ 采集异常: {e}")
            
            # 关闭标签页
            for tab, _ in tabs:
                self.browser_manager.close_tab(tab.tab_id)
            
            time.sleep(random.uniform(1, 2))
        
        self.results = [r for r in results if r.get('success')]
        logger.info(f"✅ 多标签页采集完成: {len(self.results)}/{len(product_urls)}")
        
        return results
    
    def save_results(self, output_file: str = None):
        if not output_file:
            output_file = f'multi_tab_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 结果已保存: {output_file}")
    
    def close(self):
        logger.info("🔒 关闭浏览器...")
        if self.browser_manager:
            self.browser_manager.close()
