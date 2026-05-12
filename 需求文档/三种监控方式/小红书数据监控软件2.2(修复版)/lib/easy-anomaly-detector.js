/**
 * 超简化异常检测器 - 只关注核心功能
 *
 * 功能特点：
 * 1. 简单的是/否异常判断
 * 2. 自定义销量和销售额阈值
 * 3. 只更新商品的is_anomaly字段
 * 4. 检测结果用于界面展示
 */
class EasyAnomalyDetector {
    constructor(localDataManager, categoryManager) {
        this.localDataManager = localDataManager;
        this.categoryManager = categoryManager;

        // 阈值设置
        this.thresholds = {
            sales: 50,    // 24小时新增销量阈值（件）
            revenue: 500  // 24小时新增销售额阈值（元）
        };

        this.lastResults = [];
        console.log('🔍 EasyAnomalyDetector 初始化完成');
    }

    /**
     * 设置检测阈值
     */
    setThresholds(salesThreshold, revenueThreshold) {
        this.thresholds.sales = salesThreshold;
        this.thresholds.revenue = revenueThreshold;
        console.log('🔧 阈值已更新:', this.thresholds);
    }

    /**
     * 执行异常检测
     */
    async detectAllAnomalies() {
        console.log('🔍 开始执行异常检测...');

        try {
            // 1. 获取所有商品
            const products = await this.localDataManager.getAllProducts();
            console.log(`📦 获取到 ${products.length} 个商品`);

            // ultrathink: 调试商品数据结构
            if (products.length > 0) {
                const sampleProduct = products[0];
                console.log('🔍 [DEBUG] 样本商品数据结构:', sampleProduct);
                console.log('🔍 [DEBUG] 商品字段列表:', Object.keys(sampleProduct));
                console.log('🔍 [DEBUG] 商品价格字段:', {
                    product_price: sampleProduct.product_price,
                    price: sampleProduct.price,
                    商品价格: sampleProduct['商品价格']
                });
                console.log('🔍 [DEBUG] 商品名称字段:', {
                    product_name: sampleProduct.product_name,
                    title: sampleProduct.title,
                    name: sampleProduct.name,
                    商品名称: sampleProduct['商品名称']
                });
            }

            // 2. 获取分类映射
            const categoryMap = await this.buildCategoryMap();

            // 3. 检测异常商品
            const anomalies = [];
            let checkedCount = 0;

            for (const product of products) {
                const anomalyData = this.detectSingleProduct(product, categoryMap);

                if (anomalyData) {
                    // 有异常：更新数据库并添加到结果
                    await this.localDataManager.updateProductAnomalyStatus(product.id, true);
                    anomalies.push(anomalyData);
                } else {
                    // 无异常：更新数据库
                    await this.localDataManager.updateProductAnomalyStatus(product.id, false);
                }

                checkedCount++;
            }

            // 4. 保存结果
            this.lastResults = anomalies;

            const result = {
                success: true,
                checkedCount,
                anomaliesFound: anomalies.length,
                anomalies,
                thresholds: { ...this.thresholds },
                detectionTime: new Date()
            };

            console.log(`✅ 检测完成: ${checkedCount}个商品，${anomalies.length}个异常`);
            return result;

        } catch (error) {
            console.error('❌ 异常检测失败:', error);
            return {
                success: false,
                error: error.message,
                checkedCount: 0,
                anomaliesFound: 0
            };
        }
    }

    /**
     * 检测单个商品
     */
    detectSingleProduct(product, categoryMap) {
        const sales24h = product['新增销量'] || 0;
        const revenue24h = product['新增销售额'] || 0;

        // ultrathink: 调试异常检测数据
        console.log(`🔍 [DEBUG] 检测商品 ${product.id}:`, {
            商品名称: product.product_name,
            商品价格: product.product_price,
            新增销量: sales24h,
            新增销售额: revenue24h,
            完整数据: product
        });

        // 简单的阈值判断
        const isSalesAnomaly = sales24h >= this.thresholds.sales;
        const isRevenueAnomaly = revenue24h >= this.thresholds.revenue;
        const isAnomaly = isSalesAnomaly || isRevenueAnomaly;

        if (!isAnomaly) {
            return null; // 没有异常
        }

        // 获取最新时间序列数据
        const latestData = this.getLatestTimeSeriesData(product);

        // ultrathink: 获取实际的数据库字段名称
        const fieldNames = this.getProductFieldNames(product);
        console.log(`🔍 [DEBUG] 商品 ${product.id} 的字段名称:`, fieldNames);

        // 构建展示数据 - 完整商品信息
        return {
            product_id: product.id,
            productId: product.id,  // 兼容性字段
            product_name: product.product_name || product.title || product.name || '未知商品',
            productName: product.product_name || product.title || product.name || '未知商品',  // 兼容性字段
            product_url: product.product_url || product.url || '#',
            productUrl: product.product_url || product.url || '#',  // 兼容性字段
            product_price: product.product_price || product.price || 0,
            productPrice: product.product_price || product.price || 0,  // 兼容性字段
            category_name: categoryMap.get(product.category_id) || '未分类',
            categoryName: categoryMap.get(product.category_id) || '未分类',  // 兼容性字段
            product_sales: latestData.sales,
            currentSales: latestData.sales,  // 兼容性字段
            store_sales: latestData.store_sales,
            storeSales: latestData.store_sales,  // 兼容性字段
            store_name: product.store_name || product.storeName || '未知店铺',
            storeName: product.store_name || product.storeName || '未知店铺',  // 兼容性字段
            store_followers: (product.additional_data?.store_followers !== undefined ? product.additional_data.store_followers : product.store_followers || 0),
            storeFollowers: (product.additional_data?.store_followers !== undefined ? product.additional_data.store_followers : product.store_followers || 0),  // 兼容性字段
            recent_sales: (product.additional_data?.recent_sales !== undefined ? product.additional_data.recent_sales : product.recent_sales || 0),
            recentSales: (product.additional_data?.recent_sales !== undefined ? product.additional_data.recent_sales : product.recent_sales || 0),  // 兼容性字段
            crawl_time: product.crawl_time || latestData.crawl_time || product.extracted_at,
            extracted_at: product.extracted_at,
            sales_24h: sales24h,
            revenue_24h: revenue24h,
            is_sales_anomaly: isSalesAnomaly,
            is_revenue_anomaly: isRevenueAnomaly,
            sales_threshold: this.thresholds.sales,
            revenue_threshold: this.thresholds.revenue,
            // ultrathink: 包含字段名称信息
            fieldNames: fieldNames
        };
    }

    /**
     * 获取商品的实际数据库字段名称 - ultrathink
     */
    getProductFieldNames(product) {
        const fieldNames = {
            salesField: null,
            salesValue: null,
            storeSalesField: null,
            storeSalesValue: null,
            crawlTimeField: null,
            crawlTimeValue: null
        };

        // 查找销量相关字段
        const salesFieldPatterns = [
            /^商品销量（(.+?)）$/,
            /^销量（(.+?)）$/,
            /^product_sales_(.+)$/,
            /^sales_(.+)$/
        ];

        // 查找店铺销量相关字段
        const storeSalesFieldPatterns = [
            /^店铺销量（(.+?)）$/,
            /^店铺总销量（(.+?)）$/,
            /^store_sales_(.+)$/
        ];

        // 查找爬取时间相关字段
        const crawlTimeFieldPatterns = [
            /^爬取时间（(.+?)）$/,
            /^采集时间（(.+?)）$/,
            /^crawl_time_(.+)$/,
            /^extracted_at_(.+)$/
        ];

        let latestDate = null;

        // 遍历商品所有字段，查找时间序列字段
        Object.keys(product).forEach(key => {
            // 检查销量字段
            for (const pattern of salesFieldPatterns) {
                const match = key.match(pattern);
                if (match) {
                    const dateStr = match[1];
                    const date = new Date(dateStr);
                    if (!latestDate || date > latestDate) {
                        latestDate = date;
                        fieldNames.salesField = key;
                        fieldNames.salesValue = product[key];
                    }
                    break;
                }
            }

            // 检查店铺销量字段
            for (const pattern of storeSalesFieldPatterns) {
                const match = key.match(pattern);
                if (match) {
                    const dateStr = match[1];
                    const date = new Date(dateStr);
                    if (!latestDate || date > latestDate) {
                        fieldNames.storeSalesField = key;
                        fieldNames.storeSalesValue = product[key];
                    }
                    break;
                }
            }

            // 检查爬取时间字段
            for (const pattern of crawlTimeFieldPatterns) {
                const match = key.match(pattern);
                if (match) {
                    const dateStr = match[1];
                    const date = new Date(dateStr);
                    if (!latestDate || date > latestDate) {
                        fieldNames.crawlTimeField = key;
                        fieldNames.crawlTimeValue = product[key];
                    }
                    break;
                }
            }
        });

        // 如果没有找到时间序列字段，使用基础字段
        if (!fieldNames.salesField) {
            fieldNames.salesField = 'product_sales';
            fieldNames.salesValue = product.product_sales || product.sales || 0;
        }

        if (!fieldNames.storeSalesField) {
            fieldNames.storeSalesField = 'store_sales';
            fieldNames.storeSalesValue = product.store_sales || 0;
        }

        if (!fieldNames.crawlTimeField) {
            fieldNames.crawlTimeField = 'extracted_at';
            fieldNames.crawlTimeValue = product.extracted_at;
        }

        console.log(`🔍 [DEBUG] 商品 ${product.id} 字段名称分析结果:`, fieldNames);
        return fieldNames;
    }

    /**
     * 获取最新时间序列数据
     */
    getLatestTimeSeriesData(product) {
        // 查找最新的时间序列数据
        let latestDate = null;
        let latestSales = product.sales || 0;
        let latestStoreSales = product.store_sales || 0;
        let latestCrawlTime = product.extracted_at || new Date().toISOString();

        // 遍历产品的所有属性，查找时间序列格式的字段
        Object.keys(product).forEach(key => {
            // 检查是否是时间序列格式的字段 (例如: "sales_2024-01-15", "store_sales_2024-01-15")
            const timeSeriesMatch = key.match(/^(sales|store_sales)_(\d{4}-\d{2}-\d{2})$/);
            if (timeSeriesMatch) {
                const [, fieldType, dateStr] = timeSeriesMatch;
                const date = new Date(dateStr);

                // 如果这是最新的日期，更新对应的数据
                if (!latestDate || date > latestDate) {
                    latestDate = date;

                    if (fieldType === 'sales') {
                        latestSales = product[key] || 0;
                    } else if (fieldType === 'store_sales') {
                        latestStoreSales = product[key] || 0;
                    }

                    // 爬取时间使用该日期
                    latestCrawlTime = date.toISOString();
                }
            }
        });

        return {
            sales: latestSales,
            store_sales: latestStoreSales,
            crawl_time: latestCrawlTime
        };
    }

    /**
     * 构建分类映射
     */
    async buildCategoryMap() {
        try {
            const categories = await this.categoryManager.getAllCategories();
            const categoryMap = new Map();
            categories.forEach(category => {
                categoryMap.set(category.id, category.name);
            });
            return categoryMap;
        } catch (error) {
            console.warn('构建分类映射失败:', error);
            return new Map();
        }
    }

    /**
     * 获取上次检测结果
     */
    getLastResults() {
        return {
            results: this.lastResults,
            thresholds: { ...this.thresholds }
        };
    }

    /**
     * 获取阈值
     */
    getThresholds() {
        return { ...this.thresholds };
    }
}

// 浏览器环境导出
if (typeof window !== 'undefined') {
    window.EasyAnomalyDetector = EasyAnomalyDetector;
}

// Node.js环境导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EasyAnomalyDetector;
}