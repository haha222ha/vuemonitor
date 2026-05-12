/**
 * 流量蜂小红书数据监控助手 - 内容脚本
 * Content Script for Xiaohongshu Data Extraction
 */

class XiaohongshuExtractor {
    constructor() {
        this.isExtracting = false;
        this.retryCount = 0;
        this.maxRetries = 3;
        this.extractionTimeout = 10000; // 10秒超时

        // ultrathink: 违规页面检测配置
        this.violationPatterns = {
            // 文本特征（最快检测）
            text: ['当前商品违规，无法展示', '违规', '无法展示'],

            // 图片特征
            images: ['cd26a147dd1d76b85b5e7f98e514a0f35faed27d.png'],

            // CSS类名特征
            classes: ['R56mRx-4Ge0gIY-X+rCgnQ==', 'UlsxBd6RY8cMzYLlWJcwUw==']
        };

        this.init();
    }

    /**
     * 初始化内容脚本
     */
    init() {
        // 监听来自侧边栏的消息
        chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
            this.handleMessage(message, sender, sendResponse);
            return true; // 保持消息通道开放
        });

        // 监听页面变化
        this.observePageChanges();
        
        console.log('小红书数据提取器已初始化');
    }

    /**
     * 处理消息
     */
    async handleMessage(message, sender, sendResponse) {
        switch (message.action) {
            case 'extractData':
                try {
                    const data = await this.extractSalesData();
                    sendResponse({
                        success: true,
                        data: data
                    });
                } catch (error) {
                    console.error('数据提取失败:', error);
                    sendResponse({
                        success: false,
                        error: error.message
                    });
                }
                break;
            default:
                sendResponse({ success: false, error: '未知消息类型' });
        }
    }

    /**
     * 提取销量数据
     */
    async extractSalesData() {
        if (this.isExtracting) {
            throw new Error('正在提取中，请等待...');
        }

        this.isExtracting = true;
        this.retryCount = 0;

        try {
            // 等待页面完全加载
            await this.waitForPageLoad();
            
            // 开始提取数据
            const data = await this.performExtraction();
            
            this.isExtracting = false;
            return data;
            
        } catch (error) {
            this.isExtracting = false;
            throw error;
        }
    }

    /**
     * 执行数据提取
     */
    async performExtraction() {
        return new Promise((resolve, reject) => {
            const startTime = Date.now();
            
            const attemptExtraction = async () => {
                try {
                    // 检查是否超时
                    if (Date.now() - startTime > this.extractionTimeout) {
                        reject(new Error('提取超时'));
                        return;
                    }

                    console.log(`开始第 ${this.retryCount + 1} 次提取尝试`);

                    // 🚀 ultrathink: 违规检测 - 最高优先级
                    const violationCheck = this.quickViolationCheck();
                    if (violationCheck.isViolation) {
                        console.log(`⚠️ 检测到违规商品页面 (${violationCheck.duration.toFixed(2)}ms): ${violationCheck.reason}`);

                        resolve({
                            productSales: null,
                            storeSales: null,
                            url: window.location.href,
                            timestamp: new Date().toISOString(),
                            violation: true,
                            violationDetails: violationCheck,
                            message: '商品违规，已跳过'
                        });
                        return;
                    }

                    console.log(`✅ 违规检测通过 (${violationCheck.duration.toFixed(2)}ms)，开始数据提取`);

                    // 🆕 新增：从URL提取商品ID
                    const productId = this.extractProductIdFromUrl();

                    const result = {
                        // 🆕 基础信息
                        productId: productId,
                        productName: await this.extractProductName(),
                        productPrice: await this.extractProductPrice(),
                        storeName: await this.extractStoreName(),

                        // 现有字段
                        productSales: await this.extractProductSales(),
                        storeSales: await this.extractStoreSales(),

                        // 🆕 附加数据
                        storeFollowers: await this.extractStoreFollowers(),

                        // 元数据
                        url: window.location.href,
                        timestamp: new Date().toISOString(),
                        extractedData: {}
                    };

                    // 方法3: 从页面源码中正则提取（备用方案）
                    if (!result.productSales && !result.storeSales) {
                        const regexResults = await this.extractByRegex();
                        result.productSales = result.productSales || regexResults.productSales;
                        result.storeSales = result.storeSales || regexResults.storeSales;
                    }

                    // 方法4: 从JSON数据中提取（备用方案）
                    if (!result.productSales && !result.storeSales) {
                        const jsonResults = await this.extractFromJson();
                        result.productSales = result.productSales || jsonResults.productSales;
                        result.storeSales = result.storeSales || jsonResults.storeSales;
                    }

                    // 验证结果 - 至少有商品名称或销量数据
                    if (result.productName || result.productSales || result.storeSales) {
                        console.log('✅ 数据提取成功:', result);
                        resolve(result);
                    } else {
                        this.retryCount++;
                        if (this.retryCount < this.maxRetries) {
                            console.log(`第 ${this.retryCount} 次提取未找到足够数据，${1000}ms 后重试`);
                            setTimeout(attemptExtraction, 1000);
                        } else {
                            reject(new Error('未找到商品数据，请确认页面是否为商品详情页'));
                        }
                    }
                    
                } catch (error) {
                    console.error('提取过程出错:', error);
                    this.retryCount++;
                    if (this.retryCount < this.maxRetries) {
                        setTimeout(attemptExtraction, 1000);
                    } else {
                        reject(error);
                    }
                }
            };

            attemptExtraction();
        });
    }

    /**
     * 提取商品销量
     */
    async extractProductSales() {
        // ✅ 第一步：优先检查 .price-container 中是否存在 .spu-text 元素
        console.log('🔍 开始提取商品销量...');
        const priceContainer = document.querySelector('.price-container');

        if (priceContainer) {
            console.log('✅ 找到 .price-container 容器');
            const spuTextElement = priceContainer.querySelector('.spu-text, [class*="spu-text"]');

            if (spuTextElement) {
                // 有销量元素 - 正常提取
                const text = spuTextElement.textContent.trim();
                const salesNumber = this.extractSalesNumber(text);
                if (salesNumber !== null) {
                    console.log(`✅ 从 .price-container 提取到商品销量: "${text}" -> ${salesNumber}`);
                    return salesNumber;
                }
            } else {
                // ✅ 关键修复：没有销量元素 = 销量为0
                console.log('✅ .price-container 中未找到 .spu-text 元素，判定商品销量为 0');
                return 0;
            }
        } else {
            console.log('⚠️ 未找到 .price-container 容器，使用备用方案');
        }

        // 原有逻辑作为备用方案
        const selectors = [
            // 2024年最新小红书商品销量选择器（移除Vue动态属性依赖）
            'span.spu-text',
            '.spu-text',
            '[class*="spu-text"]',
            'span[class*="spu"]',

            // 基于属性模式的选择器（排除data-v动态属性和店铺相关）
            'span[class*="spu"]:not([class*="sub-title"]):not([class*="shop"]):not([class*="store"])',
            'div[class*="spu"]:not([class*="sub-title"]):not([class*="shop"]):not([class*="store"])',

            // 商品信息区域的销量选择器
            '.product-info [class*="spu"]',
            '.goods-info [class*="spu"]',
            '.item-info [class*="spu"]',
            '.detail-info [class*="spu"]',

            // 优化的通用销量选择器
            '[class*="product"][class*="sales"]',
            '[class*="goods"][class*="sales"]',
            '[class*="item"][class*="sales"]',
            '[class*="sold"]:not([class*="monthly"]):not([class*="month"]):not([class*="shop"])',

            // 结构化选择器 - 根据页面层级
            '.product-section [class*="sales"]',
            '.goods-section [class*="sales"]',
            '.item-section [class*="sales"]',

            // 基于位置的改进选择器
            '.product-detail [class*="sales"]:not([class*="monthly"])',
            '.goods-detail [class*="sales"]:not([class*="monthly"])',
            '.detail-wrapper [class*="spu"]',

            // 备用通用选择器（优化过滤条件）
            '[class*="sales"]:not([class*="sub-title"]):not([class*="monthly"]):not([class*="shop"]):not([class*="store"])',
            '[class*="sell"]:not([class*="sub-title"]):not([class*="monthly"]):not([class*="shop"]):not([class*="store"])',

            // 数据属性选择器
            'span[data-sales]',
            'div[data-sales]',
            'span[data-sold]',
            'div[data-sold]',
            '[data-product-sales]',
            '[data-goods-sales]',

            // 传统类名选择器
            '.goods-sales',
            '.product-sales',
            '.sales-count',
            '.sold-count',
            '.sale-num',
            '.sales-info',
            '.product-sold',
            '.goods-sold'
        ];

        for (const selector of selectors) {
            try {
                const elements = document.querySelectorAll(selector);
                console.log(`商品销量选择器 "${selector}" 匹配到 ${elements.length} 个元素`);

                for (const element of elements) {
                    // ✅ 新增：必须在 .price-container 内（避免提取到店铺销量）
                    if (!element.closest('.price-container')) {
                        console.log(`  - 跳过非 .price-container 区域的元素`);
                        continue;
                    }

                    // 检查元素可见性
                    if (!this.isElementVisible(element)) {
                        console.log(`  - 跳过隐藏元素: "${element.textContent?.trim() || ''}"`)
                        continue;
                    }

                    const text = element.textContent.trim();
                    console.log(`  - 元素文本: "${text}"`);
                    const salesNumber = this.extractSalesNumber(text);

                    if (salesNumber) {
                        console.log(`✅ 通过选择器 "${selector}" 找到商品销量: "${text}" -> ${salesNumber}`);
                        return salesNumber;
                    }
                }
            } catch (error) {
                console.error(`选择器 "${selector}" 执行失败:`, error);
            }
        }

        // ✅ 最终兜底：如果所有选择器都找不到，返回 0（而非 null）
        console.log('⚠️ 所有选择器均未找到商品销量元素，判定商品销量为 0');
        return 0;
    }

    /**
     * 提取店铺销量
     */
    async extractStoreSales() {
        console.log('🔍 开始提取店铺销量...');

        const selectors = [
            // ✅ 优先使用店铺区域选择器（提高精确度）
            '.seller-container .sub-title',
            '.shop-info .sub-title',
            '.store-info .sub-title',

            // 2024年最新小红书店铺销量选择器（移除Vue动态属性依赖）
            'span.sub-title',
            '.sub-title',
            '[class*="sub-title"]',
            'span[class*="sub-title"]',
            'div[class*="sub-title"]',

            // 月销量相关选择器（高优先级，优化匹配条件）
            '[class*="monthly"][class*="sales"]',
            '[class*="month"][class*="sales"]',
            '[class*="monthly"][class*="sold"]',
            '[class*="month"][class*="sold"]',

            // 店铺信息区域选择器（扩展匹配范围）
            '.shop-info [class*="sales"]',
            '.store-info [class*="sales"]',
            '.seller-info [class*="sales"]',
            '.merchant-info [class*="sales"]',
            '.shop-section [class*="sales"]',
            '.store-section [class*="sales"]',

            // 店铺相关的销量选择器（优化匹配精度）
            '[class*="shop"][class*="sales"]:not([class*="spu"])',
            '[class*="store"][class*="sales"]:not([class*="spu"])',
            '[class*="merchant"][class*="sales"]:not([class*="spu"])',
            '[class*="seller"][class*="sales"]:not([class*="spu"])',

            // 避免与商品销量混淆的选择器（加强过滤）
            '[class*="sales"]:not([class*="spu"]):not([class*="product"]):not([class*="goods"]):not([class*="item"])',
            '[class*="sold"]:not([class*="spu"]):not([class*="product"]):not([class*="goods"]):not([class*="item"])',

            // 基于位置的选择器（扩展匹配）
            '.shop-detail [class*="sales"]',
            '.store-detail [class*="sales"]',
            '.seller-detail [class*="sales"]',
            '.merchant-detail [class*="sales"]',
            '.shop-header [class*="sales"]',
            '.store-header [class*="sales"]',

            // 数据属性选择器（扩展属性匹配）
            'span[data-monthly-sales]',
            'div[data-monthly-sales]',
            'span[data-shop-sales]',
            'div[data-shop-sales]',
            '[data-store-sales]',
            '[data-monthly-sold]',
            '[data-shop-sold]',

            // 通用店铺销量选择器（优化类名匹配）
            '[class*="shop-sales"]',
            '[class*="store-sales"]',
            '[class*="monthly-sales"]',
            '[class*="seller-sales"]',
            '[class*="merchant-sales"]',
            '[class*="shop-sold"]',
            '[class*="store-sold"]',

            // 备用选择器（保持兼容性）
            '.shop-info [class*="sold"]',
            '.store-info [class*="sold"]',
            '.seller-info [class*="sold"]',
            '.merchant-info [class*="sold"]'
        ];

        for (const selector of selectors) {
            try {
                const elements = document.querySelectorAll(selector);
                console.log(`店铺销量选择器 "${selector}" 匹配到 ${elements.length} 个元素`);

                for (const element of elements) {
                    // ✅ 关键修复：排除商品价格区域（避免误提取商品销量）
                    if (element.closest('.price-container')) {
                        console.log(`  - 跳过商品价格区域的元素`);
                        continue;
                    }

                    // ✅ 新增：必须在店铺信息区域内
                    const inSellerArea = element.closest('.seller-container') ||
                                        element.closest('.shop-info') ||
                                        element.closest('.store-info') ||
                                        element.closest('.seller-info') ||
                                        element.closest('.merchant-info');

                    if (!inSellerArea) {
                        console.log(`  - 跳过非店铺信息区域的元素`);
                        continue;
                    }

                    // 检查元素可见性
                    if (!this.isElementVisible(element)) {
                        console.log(`  - 跳过隐藏元素: "${element.textContent?.trim() || ''}"`)
                        continue;
                    }

                    const text = element.textContent.trim();
                    console.log(`  - 元素文本: "${text}"`);

                    // 🔹 排除粉丝数元素
                    if (text.includes('粉丝数') || text.includes('粉丝')) {
                        console.log(`  - 跳过粉丝数元素: "${text}"`);
                        continue;
                    }

                    // 🔹 检查是否包含店铺销量关键字
                    if (text.includes('已售') || text.includes('月销') || text.includes('销量')) {
                        const salesNumber = this.extractSalesNumber(text);
                        if (salesNumber) {
                            console.log(`✅ 通过选择器 "${selector}" 找到店铺销量: "${text}" -> ${salesNumber}`);
                            return salesNumber;
                        }
                    }
                }
            } catch (error) {
                console.error(`选择器 "${selector}" 执行失败:`, error);
            }
        }

        console.log('⚠️ 未找到店铺销量');
        return null;
    }

    /**
     * 提取商品名称
     */
    async extractProductName() {
        const selectors = [
            // 基于用户提供的示例
            '.goods-name',
            'div.goods-name',
            '[class*="goods-name"]',

            // 通用商品标题选择器
            '.product-title',
            '.product-name',
            '.goods-title',
            '[class*="product-title"]',
            '[class*="product-name"]',
            '[class*="goods-title"]',

            // H1/H2标题标签
            'h1.product-title',
            'h1[class*="title"]',
            'h2[class*="product"]',
            'h1[class*="goods"]',

            // 数据属性
            '[data-product-name]',
            '[data-goods-name]',
            '[data-title]'
        ];

        for (const selector of selectors) {
            try {
                const elements = document.querySelectorAll(selector);
                console.log(`商品名称选择器 "${selector}" 匹配到 ${elements.length} 个元素`);

                for (const element of elements) {
                    if (!this.isElementVisible(element)) {
                        continue;
                    }

                    const text = element.textContent.trim();
                    // 商品名称通常较长（>5个字符），过滤掉无效结果
                    if (text && text.length > 5 && text.length < 500) {
                        console.log(`✅ 找到商品名称: "${text.substring(0, 50)}..."`);
                        return text;
                    }
                }
            } catch (error) {
                console.error(`选择器 "${selector}" 执行失败:`, error);
            }
        }

        console.warn('⚠️ 未找到商品名称');
        return null;
    }

    /**
     * 提取商品价格
     */
    async extractProductPrice() {
        // 策略1: 通过选择器提取
        const selectors = [
            // 基于用户提供的示例
            '[class*="price"] span',
            '[class*="Price"] span',
            '.priceDecimalPart_price2',

            // 通用价格选择器
            '.product-price',
            '.goods-price',
            '[class*="product-price"]',
            '[class*="goods-price"]',
            '[class*="sale-price"]',
            '[class*="current-price"]',
            '[class*="selling-price"]',

            // 数据属性
            '[data-price]',
            '[data-product-price]',
            '[data-goods-price]'
        ];

        for (const selector of selectors) {
            try {
                const elements = document.querySelectorAll(selector);

                for (const element of elements) {
                    if (!this.isElementVisible(element)) {
                        continue;
                    }

                    const text = element.textContent.trim();
                    const priceNumber = this.extractPriceNumber(text);

                    if (priceNumber !== null && priceNumber > 0 && priceNumber < 1000000) {
                        console.log(`✅ 找到商品价格: "${text}" -> ${priceNumber}`);
                        return priceNumber;
                    }
                }
            } catch (error) {
                console.error(`选择器 "${selector}" 执行失败:`, error);
            }
        }

        // 策略2: 正则表达式提取（备用方案）
        const pageText = document.body.textContent;
        const pricePatterns = [
            /¥\s*(\d+(?:\.\d+)?)/,
            /价格[\s:：]*¥?\s*(\d+(?:\.\d+)?)/,
            /售价[\s:：]*¥?\s*(\d+(?:\.\d+)?)/
        ];

        for (const pattern of pricePatterns) {
            const match = pageText.match(pattern);
            if (match) {
                const price = parseFloat(match[1]);
                if (price > 0 && price < 1000000) {
                    console.log(`✅ 正则提取到价格: ${price}`);
                    return price;
                }
            }
        }

        console.warn('⚠️ 未找到商品价格');
        return null;
    }

    /**
     * 从文本中提取价格数字
     * 支持格式: "97.4", "¥97.4", "97", "97元"
     */
    extractPriceNumber(text) {
        if (!text) return null;

        // 移除货币符号和单位
        const cleanText = text.replace(/[¥元]/g, '').trim();

        // 提取数字（支持小数）
        const match = cleanText.match(/(\d+(?:\.\d+)?)/);
        if (match) {
            const price = parseFloat(match[1]);
            return isNaN(price) ? null : price;
        }

        return null;
    }

    /**
     * 提取店铺名称
     */
    async extractStoreName() {
        const selectors = [
            // 基于用户提供的示例
            '.seller-name',
            'p.seller-name',
            '[class*="seller-name"]',

            // 通用店铺名称选择器
            '.shop-name',
            '.store-name',
            '.merchant-name',
            '[class*="shop-name"]',
            '[class*="store-name"]',
            '[class*="merchant-name"]',
            '[class*="seller"]',

            // 店铺信息区域
            '.shop-info [class*="name"]',
            '.store-info [class*="name"]',
            '.seller-info [class*="name"]',

            // 数据属性
            '[data-shop-name]',
            '[data-store-name]',
            '[data-seller-name]'
        ];

        for (const selector of selectors) {
            try {
                const elements = document.querySelectorAll(selector);
                console.log(`店铺名称选择器 "${selector}" 匹配到 ${elements.length} 个元素`);

                for (const element of elements) {
                    if (!this.isElementVisible(element)) {
                        continue;
                    }

                    const text = element.textContent.trim();
                    // 店铺名称通常较短但不空，排除过长的文本
                    if (text && text.length > 0 && text.length < 100) {
                        console.log(`✅ 找到店铺名称: "${text}"`);
                        return text;
                    }
                }
            } catch (error) {
                console.error(`选择器 "${selector}" 执行失败:`, error);
            }
        }

        console.warn('⚠️ 未找到店铺名称');
        return null;
    }

    /**
     * 提取店铺粉丝数
     */
    async extractStoreFollowers() {
        const selectors = [
            // 基于用户提供的示例 - sub-title包含"粉丝"文本
            '.sub-title',
            'span.sub-title',
            '[class*="sub-title"]',

            // 通用粉丝数选择器
            '.follower-count',
            '.fans-count',
            '[class*="follower"]',
            '[class*="fans"]',

            // 店铺信息区域
            '.shop-info [class*="follower"]',
            '.store-info [class*="fans"]',
            '.seller-info [class*="follower"]',

            // 数据属性
            '[data-follower-count]',
            '[data-fans-count]'
        ];

        for (const selector of selectors) {
            try {
                const elements = document.querySelectorAll(selector);

                for (const element of elements) {
                    if (!this.isElementVisible(element)) {
                        continue;
                    }

                    const text = element.textContent.trim();

                    // 检查文本是否包含"粉丝"关键字
                    if (text.includes('粉丝数') || text.includes('粉丝')) {
                        const followersNumber = this.extractSalesNumber(text);
                        if (followersNumber !== null) {
                            console.log(`✅ 找到粉丝数: "${text}" -> ${followersNumber}`);
                            return followersNumber;
                        }
                    }
                }
            } catch (error) {
                console.error(`选择器 "${selector}" 执行失败:`, error);
            }
        }

        console.warn('⚠️ 未找到店铺粉丝数');
        return null;
    }

    /**
     * 从URL提取商品ID
     */
    extractProductIdFromUrl(url = window.location.href) {
        // 小红书商品链接格式:
        // https://www.xiaohongshu.com/goods-detail/667ec161c06183000114d036?...

        const patterns = [
            /goods-detail\/([a-f0-9]+)/i,     // goods-detail/商品ID
            /goods\/([a-f0-9]+)/i,            // goods/商品ID
            /product\/([a-f0-9]+)/i,          // product/商品ID
            /item\/([a-f0-9]+)/i              // item/商品ID
        ];

        for (const pattern of patterns) {
            const match = url.match(pattern);
            if (match && match[1]) {
                console.log(`✅ 从URL提取商品ID: ${match[1]}`);
                return match[1];
            }
        }

        console.warn('⚠️ 无法从URL提取商品ID');
        return null;
    }

    /**
     * 通过正则表达式从页面源码提取
     */
    async extractByRegex() {
        const pageSource = document.documentElement.outerHTML;
        const result = {
            productSales: null,
            storeSales: null
        };

        // 商品销量匹配模式
        const productPatterns = [
            /已售[\s:：]*(\d+(?:\.\d+)?[万千百十]?)/gi,
            /销量[\s:：]*(\d+(?:\.\d+)?[万千百十]?)/gi,
            /售出[\s:：]*(\d+(?:\.\d+)?[万千百十]?)/gi,
            /"saleCount"[\s:：]*(\d+)/gi,
            /"soldCount"[\s:：]*(\d+)/gi,
            /"sales"[\s:：]*"(\d+(?:\.\d+)?[万千百十]?)"/gi
        ];

        // 店铺销量匹配模式
        const storePatterns = [
            /月销[\s:：]*(\d+(?:\.\d+)?[万千百十]?)/gi,
            /月售[\s:：]*(\d+(?:\.\d+)?[万千百十]?)/gi,
            /"monthlySales"[\s:：]*(\d+)/gi,
            /"shopSales"[\s:：]*(\d+)/gi,
            /"storeSales"[\s:：]*"(\d+(?:\.\d+)?[万千百十]?)"/gi
        ];

        // 提取商品销量
        for (const pattern of productPatterns) {
            const matches = [...pageSource.matchAll(pattern)];
            if (matches.length > 0) {
                const salesText = matches[0][1];
                result.productSales = this.formatSalesNumber(salesText);
                console.log(`正则提取到商品销量: ${result.productSales}`);
                break;
            }
        }

        // 提取店铺销量
        for (const pattern of storePatterns) {
            const matches = [...pageSource.matchAll(pattern)];
            if (matches.length > 0) {
                const salesText = matches[0][1];
                result.storeSales = this.formatSalesNumber(salesText);
                console.log(`正则提取到店铺销量: ${result.storeSales}`);
                break;
            }
        }

        return result;
    }

    /**
     * 从JSON数据中提取
     */
    async extractFromJson() {
        const result = {
            productSales: null,
            storeSales: null
        };

        try {
            // 查找页面中的JSON数据
            const scriptTags = document.querySelectorAll('script[type="application/json"], script:not([src])');
            
            for (const script of scriptTags) {
                try {
                    const jsonText = script.textContent.trim();
                    if (!jsonText || !jsonText.startsWith('{')) continue;
                    
                    const data = JSON.parse(jsonText);
                    
                    // 递归查找销量相关字段
                    const salesData = this.findSalesInObject(data);
                    if (salesData.productSales) result.productSales = salesData.productSales;
                    if (salesData.storeSales) result.storeSales = salesData.storeSales;
                    
                    if (result.productSales || result.storeSales) {
                        console.log('从JSON数据中提取到销量:', result);
                        break;
                    }
                    
                } catch (error) {
                    // JSON解析失败，跳过
                    continue;
                }
            }
        } catch (error) {
            console.error('从JSON提取数据失败:', error);
        }

        return result;
    }

    /**
     * 在对象中递归查找销量数据
     */
    findSalesInObject(obj, depth = 0) {
        if (depth > 10 || !obj || typeof obj !== 'object') return { productSales: null, storeSales: null };
        
        const result = { productSales: null, storeSales: null };
        
        const productKeys = ['saleCount', 'soldCount', 'sales', 'sellCount', 'productSales'];
        const storeKeys = ['monthlySales', 'shopSales', 'storeSales', 'monthlyCount'];
        
        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                const value = obj[key];
                
                // 检查产品销量字段
                if (productKeys.some(k => key.toLowerCase().includes(k.toLowerCase()))) {
                    if (typeof value === 'number' || typeof value === 'string') {
                        result.productSales = this.formatSalesNumber(value.toString());
                    }
                }
                
                // 检查店铺销量字段
                if (storeKeys.some(k => key.toLowerCase().includes(k.toLowerCase()))) {
                    if (typeof value === 'number' || typeof value === 'string') {
                        result.storeSales = this.formatSalesNumber(value.toString());
                    }
                }
                
                // 递归查找
                if (typeof value === 'object' && !result.productSales && !result.storeSales) {
                    const subResult = this.findSalesInObject(value, depth + 1);
                    if (subResult.productSales) result.productSales = subResult.productSales;
                    if (subResult.storeSales) result.storeSales = subResult.storeSales;
                }
            }
        }
        
        return result;
    }

    /**
     * 从文本中提取销量数字
     */
    extractSalesNumber(text) {
        if (!text || typeof text !== 'string') return null;

        // 清理文本
        text = text.replace(/\s+/g, ' ').trim();

        // 销量相关的正则模式
        const patterns = [
            // 粉丝数相关模式（优先匹配）
            /粉丝数[\s:：]*(\d+(?:\.\d+)?[万千百十]?)/i,
            /粉丝[\s:：]*(\d+(?:\.\d+)?[万千百十]?)/i,
            /(\d+(?:\.\d+)?[万千百十]?)[\s]*粉丝/i,

            // 销量相关模式
            /已售[\s:：]*(\d+(?:\.\d+)?[万千百十]?)/i,
            /销量[\s:：]*(\d+(?:\.\d+)?[万千百十]?)/i,
            /售出[\s:：]*(\d+(?:\.\d+)?[万千百十]?)/i,
            /月销[\s:：]*(\d+(?:\.\d+)?[万千百十]?)/i,
            /(\d+(?:\.\d+)?[万千百十]?)[\s]*已售/i,
            /(\d+(?:\.\d+)?[万千百十]?)[\s]*销量/i,
            /(\d+(?:\.\d+)?[万千百十]?)[\s]*售出/i,
            /(\d+(?:\.\d+)?[万千百十]?)[\s]*月销/i
        ];

        for (const pattern of patterns) {
            const match = text.match(pattern);
            if (match && match[1]) {
                return this.formatSalesNumber(match[1]);
            }
        }

        // 如果文本只包含数字和单位，直接提取
        const pureNumberMatch = text.match(/^(\d+(?:\.\d+)?[万千百十]?)$/);
        if (pureNumberMatch) {
            return this.formatSalesNumber(pureNumberMatch[1]);
        }

        return null;
    }

    /**
     * 检查元素是否可见
     */
    isElementVisible(element) {
        if (!element) return false;

        try {
            const style = window.getComputedStyle(element);
            const rect = element.getBoundingClientRect();

            return style.display !== 'none' &&
                   style.visibility !== 'hidden' &&
                   style.opacity !== '0' &&
                   element.offsetHeight > 0 &&
                   element.offsetWidth > 0 &&
                   rect.width > 0 &&
                   rect.height > 0;
        } catch (error) {
            console.warn('检查元素可见性失败:', error);
            return true; // 发生错误时假设元素可见，避免过度过滤
        }
    }

    /**
     * 格式化销量数字 - 转换为整数
     */
    formatSalesNumber(numberStr) {
        if (!numberStr) return null;
        
        // 清理字符串
        numberStr = numberStr.toString().trim();
        console.log(`🔄 格式化销量数字: "${numberStr}"`);
        
        // 转换中文数字单位为整数
        if (numberStr.includes('万')) {
            const baseNumber = parseFloat(numberStr.replace('万', ''));
            const result = Math.round(baseNumber * 10000);
            console.log(`  万单位转换: ${baseNumber}万 -> ${result}`);
            return result; // 1.2万 -> 12000
        } else if (numberStr.includes('千')) {
            const baseNumber = parseFloat(numberStr.replace('千', ''));
            const result = Math.round(baseNumber * 1000);
            console.log(`  千单位转换: ${baseNumber}千 -> ${result}`);
            return result; // 1.1千 -> 1100
        } else if (numberStr.includes('百')) {
            const baseNumber = parseFloat(numberStr.replace('百', ''));
            const result = Math.round(baseNumber * 100);
            console.log(`  百单位转换: ${baseNumber}百 -> ${result}`);
            return result; // 1.5百 -> 150
        } else if (numberStr.includes('十')) {
            const baseNumber = parseFloat(numberStr.replace('十', ''));
            const result = Math.round(baseNumber * 10);
            console.log(`  十单位转换: ${baseNumber}十 -> ${result}`);
            return result; // 1.2十 -> 12
        } else {
            // 纯数字，直接返回整数
            const number = parseInt(numberStr);
            const result = isNaN(number) ? null : number;
            console.log(`  纯数字转换: "${numberStr}" -> ${result}`);
            return result;
        }
    }

    /**
     * 等待页面加载完成和动态内容渲染
     */
    async waitForPageLoad() {
        return new Promise((resolve) => {
            console.log('⏳ 等待页面加载完成...');

            // 检查页面状态
            const checkPageReady = () => {
                const readyState = document.readyState;
                const hasContent = document.body && document.body.children.length > 0;
                const hasScripts = document.querySelectorAll('script').length > 0;

                console.log(`页面状态: ${readyState}, 内容数: ${document.body?.children.length || 0}, 脚本数: ${document.querySelectorAll('script').length}`);

                if (readyState === 'complete' && hasContent) {
                    // 页面基本加载完成，等待动态内容
                    this.waitForDynamicContent().then(resolve);
                } else {
                    setTimeout(checkPageReady, 500);
                }
            };

            if (document.readyState === 'complete') {
                this.waitForDynamicContent().then(resolve);
            } else {
                const checkReady = () => {
                    if (document.readyState === 'complete') {
                        this.waitForDynamicContent().then(resolve);
                    } else {
                        setTimeout(checkReady, 100);
                    }
                };
                checkReady();
            }
        });
    }

    /**
     * 等待动态内容加载
     */
    async waitForDynamicContent() {
        return new Promise((resolve) => {
            console.log('⏳ 等待动态内容加载...');

            let attempts = 0;
            const maxAttempts = 10;
            const checkInterval = 1000;

            const checkForContent = () => {
                attempts++;

                // 检查是否有销量相关的元素出现
                const hasProductElements = document.querySelectorAll('[class*="spu"], [class*="product"], [class*="goods"]').length > 0;
                const hasStoreElements = document.querySelectorAll('[class*="shop"], [class*="store"], [class*="sub-title"]').length > 0;
                const hasSalesText = document.body.textContent.includes('已售') ||
                                  document.body.textContent.includes('月销') ||
                                  document.body.textContent.includes('销量');

                console.log(`动态内容检查 ${attempts}/${maxAttempts}: 商品元素=${hasProductElements}, 店铺元素=${hasStoreElements}, 销量文本=${hasSalesText}`);

                if ((hasProductElements || hasStoreElements || hasSalesText) || attempts >= maxAttempts) {
                    console.log(`✅ 动态内容加载完成 (${attempts}次检查)`);
                    resolve();
                } else {
                    setTimeout(checkForContent, checkInterval);
                }
            };

            // 立即开始检查
            checkForContent();
        });
    }

    /**
     * 智能重试机制
     */
    async waitForElementsWithRetry(selectors, maxWaitTime = 10000) {
        return new Promise((resolve, reject) => {
            const startTime = Date.now();

            const checkElements = () => {
                for (const selector of selectors) {
                    try {
                        const elements = document.querySelectorAll(selector);
                        if (elements.length > 0) {
                            console.log(`✅ 找到元素: ${selector} (${elements.length}个)`);
                            resolve({ selector, elements: Array.from(elements) });
                            return;
                        }
                    } catch (error) {
                        console.warn(`选择器错误: ${selector}`, error);
                    }
                }

                const elapsed = Date.now() - startTime;
                if (elapsed < maxWaitTime) {
                    setTimeout(checkElements, 500);
                } else {
                    console.log(`⏰ 等待超时 (${maxWaitTime}ms)，未找到任何元素`);
                    resolve(null);
                }
            };

            checkElements();
        });
    }

    /**
     * 观察页面变化
     */
    observePageChanges() {
        let lastUrl = window.location.href;
        
        // 监听URL变化 (SPA应用)
        const observer = new MutationObserver(() => {
            if (window.location.href !== lastUrl) {
                lastUrl = window.location.href;
                console.log('页面URL变化:', lastUrl);
                
                // 通知侧边栏页面已变化
                chrome.runtime.sendMessage({
                    action: 'pageChanged',
                    url: lastUrl
                }).catch(error => {
                    // 忽略错误，可能是侧边栏未打开
                });
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // 监听浏览器前进/后退
        window.addEventListener('popstate', () => {
            console.log('页面popstate事件');
            chrome.runtime.sendMessage({
                action: 'pageChanged',
                url: window.location.href
            }).catch(error => {
                // 忽略错误
            });
        });
    }

    /**
     * 检查是否为商品页面
     */
    isProductPage() {
        const url = window.location.href;
        
        // 小红书商品页面URL模式
        const productUrlPatterns = [
            /xiaohongshu\.com\/goods-detail\//,
            /xiaohongshu\.com\/.*\/[a-f0-9]{24}/,
            /xiaohongshu\.com\/explore\//
        ];
        
        return productUrlPatterns.some(pattern => pattern.test(url));
    }

    /**
     * 获取页面调试信息
     */
    getDebugInfo() {
        return {
            url: window.location.href,
            title: document.title,
            isProductPage: this.isProductPage(),
            readyState: document.readyState,
            timestamp: new Date().toISOString()
        };
    }

    /**
     * ultrathink: 快速检测是否为违规商品页面
     * @returns {object} 检测结果
     */
    quickViolationCheck() {
        const startTime = performance.now();

        try {
            // 方法1: 文本快速检测 (最快)
            const bodyText = document.body.textContent || document.body.innerText || '';
            for (const violationText of this.violationPatterns.text) {
                if (bodyText.includes(violationText)) {
                    return {
                        isViolation: true,
                        method: 'text_detection',
                        duration: performance.now() - startTime,
                        reason: `检测到违规提示文本: "${violationText}"`,
                        matchedText: violationText
                    };
                }
            }

            // 方法2: 图片URL检测
            for (const imagePattern of this.violationPatterns.images) {
                const images = document.querySelectorAll(`img[src*="${imagePattern}"]`);
                if (images.length > 0) {
                    return {
                        isViolation: true,
                        method: 'image_detection',
                        duration: performance.now() - startTime,
                        reason: `检测到违规提示图片: "${imagePattern}"`,
                        matchedPattern: imagePattern,
                        imageCount: images.length
                    };
                }
            }

            // 方法3: CSS类名检测
            for (const className of this.violationPatterns.classes) {
                const elements = document.querySelectorAll(`.${className.replace(/[=+]/g, '\\$&')}`);
                if (elements.length > 0) {
                    return {
                        isViolation: true,
                        method: 'css_class_detection',
                        duration: performance.now() - startTime,
                        reason: `检测到违规页面CSS类: "${className}"`,
                        matchedClass: className,
                        elementCount: elements.length
                    };
                }
            }

            // 方法4: 特定DOM结构检测
            const violationContainer = document.querySelector('[data-v-634bf1de] p');
            if (violationContainer && violationContainer.textContent.includes('违规')) {
                return {
                    isViolation: true,
                    method: 'dom_structure',
                    duration: performance.now() - startTime,
                    reason: '检测到违规页面DOM结构',
                    elementText: violationContainer.textContent
                };
            }

            return {
                isViolation: false,
                duration: performance.now() - startTime,
                checksPerformed: ['text', 'image', 'css_class', 'dom_structure']
            };

        } catch (error) {
            console.warn('违规检测过程中出现错误:', error);
            return {
                isViolation: false,
                duration: performance.now() - startTime,
                error: error.message
            };
        }
    }
}

// 创建提取器实例
const extractor = new XiaohongshuExtractor();

// 导出到全局作用域供调试使用
window.xiaohongshuExtractor = extractor;
    /**
     * 改进的销量查找函数 - 使用多种策略
     */
    function findSalesWithFallback(selectors, textPattern, elementType = 'productSales') {
        console.log(`🔍 开始查找${elementType}，使用${selectors.length}个选择器`);

        // 策略1：尝试所有选择器
        for (let i = 0; i < selectors.length; i++) {
            const selector = selectors[i];
            try {
                const elements = document.querySelectorAll(selector);
                console.log(`📊 选择器 "${selector}" 找到 ${elements.length} 个元素`);

                for (let element of elements) {
                    const text = element.textContent?.trim();
                    if (text && textPattern.test(text)) {
                        console.log(`✅ 通过选择器找到${elementType}: "${text}"`);
                        const match = text.match(textPattern);
                        return match ? match[1] : null;
                    }
                }
            } catch (error) {
                console.log(`❌ 选择器 "${selector}" 执行失败: ${error.message}`);
            }
        }

        // 策略2：文本内容全局搜索
        console.log(`🔍 使用文本模式全局搜索${elementType}`);
        const allElements = document.querySelectorAll('*:not(script):not(style)');

        for (let element of allElements) {
            const text = element.textContent?.trim();
            if (text && text.length < 100 && textPattern.test(text)) {
                // 确保不是包含在更大文本中的片段
                const elementRect = element.getBoundingClientRect();
                if (elementRect.width > 0 && elementRect.height > 0) {
                    console.log(`✅ 通过文本搜索找到${elementType}: "${text}"`);
                    const match = text.match(textPattern);
                    return match ? match[1] : null;
                }
            }
        }

        // 策略3：Vue组件数据搜索
        console.log(`🔍 搜索Vue组件数据`);
        const vueElements = document.querySelectorAll('[data-v-*]');
        for (let element of vueElements) {
            const text = element.textContent?.trim();
            if (text && textPattern.test(text)) {
                console.log(`✅ 通过Vue元素找到${elementType}: "${text}"`);
                const match = text.match(textPattern);
                return match ? match[1] : null;
            }
        }

        console.log(`❌ 未找到${elementType}`);
        return null;
    }

    /**
     * 健康检查 - 验证选择器是否仍然有效
     */
    function validateSelectors(selectors, expectedText) {
        const results = {
            working: [],
            failed: [],
            suggestions: []
        };

        selectors.forEach(selector => {
            try {
                const elements = document.querySelectorAll(selector);
                if (elements.length > 0) {
                    let hasValidText = false;
                    Array.from(elements).forEach(el => {
                        const text = el.textContent?.trim();
                        if (text && (text.includes(expectedText) || /\d+/.test(text))) {
                            hasValidText = true;
                        }
                    });

                    if (hasValidText) {
                        results.working.push(selector);
                    } else {
                        results.failed.push(`${selector} (找到元素但文本不匹配)`);
                    }
                } else {
                    results.failed.push(`${selector} (未找到元素)`);
                }
            } catch (error) {
                results.failed.push(`${selector} (语法错误: ${error.message})`);
            }
        });

        return results;
    }