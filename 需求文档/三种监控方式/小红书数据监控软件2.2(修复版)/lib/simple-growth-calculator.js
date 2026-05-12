/**
 * 简化增长计算器
 * 专门处理固定字段的24小时增长计算：新增销量、新增销售额
 */
class SimpleGrowthCalculator {
    constructor() {
        this.GROWTH_FIELDS = {
            SALES_GROWTH: '新增销量',
            REVENUE_GROWTH: '新增销售额', 
            CALC_TIME: '增长计算时间',
            CALC_INTERVAL: '增长计算间隔',
            CONFIDENCE: '增长置信度'
        };
        console.log('📊 简化增长计算器已初始化');
    }
    
    /**
     * 计算并更新增长字段
     * @param {Object} productRecord - 商品记录
     * @param {Object} newSalesData - 新的销量数据
     * @param {Date} crawlTime - 爬取时间，默认为当前时间
     * @returns {Object} 计算结果
     */
    async updateGrowthFields(productRecord, newSalesData, crawlTime = new Date()) {
        try {
            console.log(`\n🧮 [增长计算] 开始处理: ${productRecord.product_name || productRecord.product_id}`);
            console.log(`🔍 [增长计算] 产品当前数据:`, {
                product_sales: productRecord.product_sales,
                时间序列字段: Object.keys(productRecord).filter(k => k.includes('商品销量（')).length
            });

            // 1. 获取对比数据 - 优先使用历史数据，如果没有则使用基准数据
            let previousData = this.getLatestHistoryData(productRecord, crawlTime);
            let isFirstTimeCalculation = !this.hasGrowthFields(productRecord);

            if (previousData) {
                console.log(`✅ [增长计算] 成功获取历史数据: 销量=${previousData.productSales}, 来源=${previousData.date}`);
            } else {
                console.log('⚠️ [增长计算] 未找到历史数据，尝试获取最新的时间序列数据作为基准...');
            }

            // 如果没有历史数据，检查是否应该使用基准数据
            if (!previousData) {
                console.log('🔍 [基准数据] 未找到历史时间序列字段，检查是否使用基准数据...');

                // 🔥 关键：验证确实没有历史字段（只有当天或无字段）
                const allKeys = Object.keys(productRecord);
                const allSalesFields = allKeys.filter(key => key.startsWith('商品销量（') && key.endsWith('）'));
                const currentDateStr = DateFormatter.getChineseDateFormat(crawlTime);

                const hasOnlyTodayFields = allSalesFields.every(field => {
                    const dateStr = DateFormatter.extractDateFromFieldName(field);
                    return dateStr === currentDateStr; // 只有当天字段
                });

                if (allSalesFields.length === 0 || hasOnlyTodayFields) {
                    // ✅ 确实无历史字段，使用基准数据
                    console.log('📋 [基准数据] 确认无历史时间序列字段，使用extracted_at基准数据');

                    previousData = {
                        date: '基准数据(extracted_at)',
                        productSales: productRecord.product_sales || 0,
                        storeSales: productRecord.store_sales || 0,
                        crawlTime: productRecord.extracted_at || productRecord.created_at || new Date().toISOString(),
                        productPrice: productRecord.product_price || 50
                    };

                    console.log(`📋 [基准数据] 销量: ${previousData.productSales}, 基准时间: ${previousData.crawlTime}`);
                } else {
                    console.warn('❌ [数据异常] 应该有历史字段但获取失败，可能存在数据问题');
                }
            }
            
            // 如果完全没有可对比的数据，使用当前数据作为基准（首次监控，增长为0）
            if (!previousData) {
                console.log('🔄 [首次监控] 使用当前数据作为基准，增长为0');

                // 创建虚拟的历史时间点（24小时前），确保时间间隔不为0
                const simulatedHistoryTime = new Date(crawlTime.getTime() - 24 * 60 * 60 * 1000);

                previousData = {
                    date: '首次监控基准',
                    productSales: newSalesData.productSales || 0,
                    storeSales: newSalesData.storeSales || 0,
                    crawlTime: simulatedHistoryTime.toISOString(), // 使用24小时前的时间
                    productPrice: newSalesData.productPrice || productRecord.product_price || 50
                };
                console.log('📋 [首次监控基准] 销量:', previousData.productSales, '店铺销量:', previousData.storeSales);
                console.log('⏰ [首次监控基准] 虚拟历史时间:', simulatedHistoryTime.toISOString(), '(24小时前)');
            }
            
            // 3. 计算时间间隔
            const currentTime = new Date(crawlTime);
            const previousTime = new Date(previousData.crawlTime);
            const hoursInterval = (currentTime - previousTime) / (1000 * 60 * 60);
            
            console.log('🕒 [时间计算] 当前时间:', currentTime.toISOString());
            console.log('🕒 [时间计算] 历史时间:', previousTime.toISOString());
            console.log('🕒 [时间计算] 时间间隔:', hoursInterval.toFixed(2) + '小时');
            
            // 4. 计算实际增长
            const salesGrowth = (newSalesData.productSales || 0) - (previousData.productSales || 0);
            const currentPrice = newSalesData.productPrice || productRecord.product_price || productRecord.price || 50;
            const revenueGrowth = salesGrowth * currentPrice;

            // 📈 详细的增长计算日志
            console.log(`🔢 [增长计算详情] ${productRecord.product_name || productRecord.product_id}`);
            console.log(`   ├─ 📊 数据源类型: ${previousData.date}`);
            console.log(`   ├─ 📈 历史销量: ${previousData.productSales}`);
            console.log(`   ├─ 📋 当前销量: ${newSalesData.productSales}`);
            console.log(`   ├─ 📈 实际增长: ${salesGrowth}`);
            console.log(`   ├─ ⏱️ 时间间隔: ${hoursInterval.toFixed(1)}小时`);
            console.log(`   └─ 💰 商品价格: ${currentPrice}`);

            // 检查是否使用了错误的基准数据
            if (previousData.date === '传统基准数据' && previousData.productSales === productRecord.product_sales) {
                console.log(`⚠️ [数据源警告] 使用了传统基准数据 (${previousData.productSales})，可能存在时间序列数据但未被正确识别`);

                // 重新检查是否有时间序列数据被忽略
                const timeSeriesFields = Object.keys(productRecord).filter(k => k.startsWith('商品销量（') && k.endsWith('）'));
                if (timeSeriesFields.length > 0) {
                    console.log(`❌ [数据源错误] 发现 ${timeSeriesFields.length} 个时间序列字段但未使用:`, timeSeriesFields);
                    timeSeriesFields.forEach(field => {
                        console.log(`   - ${field}: ${productRecord[field]}`);
                    });
                }
            }

            // 5. 换算到24小时 - 特殊处理不同数据源
            let sales24h, revenue24h;
            if (previousData.date === '首次监控基准') {
                // 首次监控，增长为0
                sales24h = 0;
                revenue24h = 0;
                console.log(`   🆕 首次监控，增长为0`);
            } else if (previousData.date === '传统基准数据') {
                // 使用基准数据时，也需要按时间间隔换算到24小时
                sales24h = this.extrapolateTo24Hours(salesGrowth, hoursInterval);
                revenue24h = this.extrapolateTo24Hours(revenueGrowth, hoursInterval);
                console.log(`   📋 传统基准数据对比，按时间间隔换算到24h增长`);
            } else {
                // 使用历史数据时，按时间间隔换算
                sales24h = this.extrapolateTo24Hours(salesGrowth, hoursInterval);
                revenue24h = this.extrapolateTo24Hours(revenueGrowth, hoursInterval);
                console.log(`   ✅ 时间序列数据对比，按时间间隔换算到24h增长`);
            }

            console.log(`   ├─ 📊 24h预估销量增长: ${sales24h}`);
            console.log(`   └─ 💰 24h预估销售额增长: ${revenue24h}`);
            
            // 6. 计算置信度 - 特殊处理不同数据源
            let confidence;
            if (previousData.date === '首次监控基准') {
                // 首次监控，置信度为100%（因为增长为0是确定的）
                confidence = 100;
                console.log(`   🆕 首次监控，置信度为100%`);
            } else if (previousData.date === '基准数据') {
                // 使用基准数据时，给予80%置信度（较高但不是100%）
                confidence = 80;
                console.log(`   📋 基准数据对比，设置置信度为80%`);
            } else {
                confidence = this.calculateConfidence(hoursInterval);
            }
            
            // 7. 更新字段
            productRecord[this.GROWTH_FIELDS.SALES_GROWTH] = sales24h;
            productRecord[this.GROWTH_FIELDS.REVENUE_GROWTH] = revenue24h;
            productRecord[this.GROWTH_FIELDS.CALC_TIME] = currentTime.toISOString();
            productRecord[this.GROWTH_FIELDS.CALC_INTERVAL] = Math.round(hoursInterval * 100) / 100;
            productRecord[this.GROWTH_FIELDS.CONFIDENCE] = confidence;
            
            console.log(`📊 增长计算: 销量+${sales24h}, 销售额+${revenue24h} (间隔:${hoursInterval.toFixed(1)}h, 置信度:${confidence}%)`);
            
            return {
                success: true,
                sales24h,
                revenue24h,
                confidence,
                interval: hoursInterval,
                isFirstTime: isFirstTimeCalculation,
                actualSalesGrowth: salesGrowth,
                actualRevenueGrowth: revenueGrowth,
                usedBaseline: previousData.date === '基准数据'
            };
            
        } catch (error) {
            console.error('❌ 增长字段更新失败:', error);
            return {
                success: false,
                error: error.message,
                isFirstTime: false
            };
        }
    }
    
    /**
     * 创建初始增长字段
     * @param {Object} productRecord - 商品记录
     * @returns {Object} 创建结果
     */
    createInitialGrowthFields(productRecord) {
        const currentTime = new Date();
        
        productRecord[this.GROWTH_FIELDS.SALES_GROWTH] = 0;
        productRecord[this.GROWTH_FIELDS.REVENUE_GROWTH] = 0;
        productRecord[this.GROWTH_FIELDS.CALC_TIME] = currentTime.toISOString();
        productRecord[this.GROWTH_FIELDS.CALC_INTERVAL] = 0;
        productRecord[this.GROWTH_FIELDS.CONFIDENCE] = 0;
        
        // 🆕 首次创建增长字段日志
        console.log(`🆕 [首次监控] ${productRecord.product_name || productRecord.product_id}`);
        console.log(`   ├─ 新增销量: 0 (首次监控)`);
        console.log(`   ├─ 新增销售额: 0 (首次监控)`);
        console.log(`   └─ 增长置信度: 0% (需要历史数据)`);
        
        return {
            success: true,
            sales24h: 0,
            revenue24h: 0,
            confidence: 0,
            interval: 0,
            isFirstTime: true
        };
    }
    
    /**
     * 检查是否已有增长字段
     * @param {Object} productRecord - 商品记录
     * @returns {boolean} 是否有增长字段
     */
    hasGrowthFields(productRecord) {
        return productRecord.hasOwnProperty(this.GROWTH_FIELDS.SALES_GROWTH) ||
               productRecord.hasOwnProperty(this.GROWTH_FIELDS.REVENUE_GROWTH);
    }
    
    /**
     * 获取最新的历史数据用于对比（修复版）
     * @param {Object} productRecord - 商品记录
     * @param {Date} currentCrawlTime - 当前爬取时间，用于排除同时间的数据
     * @returns {Object|null} 历史数据
     */
    getLatestHistoryData(productRecord, currentCrawlTime = null) {
        try {
            const allKeys = Object.keys(productRecord);
            const salesFields = allKeys.filter(key => key.startsWith('商品销量（') && key.endsWith('）'));

            if (salesFields.length === 0) {
                console.log('🔍 [历史数据] 未找到任何时间序列字段');
                return null;
            }

            // ✅ 获取当天日期字符串，用于排除当天数据
            const currentDateStr = currentCrawlTime ?
                DateFormatter.getChineseDateFormat(currentCrawlTime) :
                DateFormatter.getChineseDateFormat(new Date());

            console.log(`🔍 [历史数据] 当前日期: ${currentDateStr}，需要排除当天数据`);
            console.log(`🔍 [历史数据] 找到 ${salesFields.length} 个时间序列字段:`, salesFields);

            let historicalFields = [];

            // ✅ 核心修复：只收集历史字段，严格排除当天字段
            for (const field of salesFields) {
                const dateStr = DateFormatter.extractDateFromFieldName(field);
                if (!dateStr) continue;

                // 🔥 关键修复：排除当天字段
                if (dateStr === currentDateStr) {
                    console.log(`⏰ [历史数据] 排除当天数据: ${field} (${dateStr})`);
                    continue;
                }

                const crawlTimeField = `爬取时间（${dateStr}）`;
                const crawlTime = productRecord[crawlTimeField];

                if (crawlTime) {
                    historicalFields.push({
                        field: field,
                        dateStr: dateStr,
                        crawlTime: crawlTime,
                        fieldDate: new Date(crawlTime)
                    });
                    console.log(`✅ [历史数据] 发现历史字段: ${field} (${dateStr})`);
                } else {
                    console.log(`⚠️ [历史数据] 无爬取时间，跳过: ${field}`);
                }
            }

            if (historicalFields.length === 0) {
                console.log('🔍 [历史数据] 未找到历史时间序列字段（只有当天或无时间戳）');
                return null;
            }

            // ✅ 选择最新的历史数据（不包括当天）
            historicalFields.sort((a, b) => b.fieldDate - a.fieldDate);
            const selectedHistory = historicalFields[0];

            console.log(`✅ [历史数据] 选择最新历史数据: ${selectedHistory.field} (${selectedHistory.dateStr})`);

            const dateStr = selectedHistory.dateStr;
            const storeSalesField = `店铺销量（${dateStr}）`;
            const crawlTimeField = `爬取时间（${dateStr}）`;
            const priceField = `商品价格（${dateStr}）`;

            return {
                date: dateStr,
                productSales: productRecord[selectedHistory.field] || 0,
                storeSales: productRecord[storeSalesField] || 0,
                crawlTime: selectedHistory.crawlTime,
                productPrice: productRecord[priceField]
            };

        } catch (error) {
            console.warn('获取历史数据失败:', error);
            return null;
        }
    }
    
    /**
     * 换算到24小时
     * @param {number} actualGrowth - 实际增长
     * @param {number} actualHours - 实际小时数
     * @returns {number} 24小时预估增长
     */
    extrapolateTo24Hours(actualGrowth, actualHours) {
        if (actualHours <= 0) return 0;
        
        const extrapolated = actualGrowth * (24 / actualHours);
        return Math.round(extrapolated);
    }
    
    /**
     * 计算置信度
     * @param {number} hours - 时间间隔(小时)
     * @returns {number} 置信度百分比(0-100)
     */
    calculateConfidence(hours) {
        // 理想时间间隔为20-28小时，置信度最高
        if (hours >= 20 && hours <= 28) {
            return 100;
        }
        
        // 时间过短，置信度急剧下降
        if (hours < 6) {
            return Math.max(20, 100 - (6 - hours) * 15);
        }
        
        // 时间过长，置信度逐渐下降
        if (hours > 48) {
            return Math.max(40, 100 - (hours - 48) * 5);
        }
        
        // 中等时间间隔，线性递减
        return Math.max(60, Math.round(100 - Math.abs(hours - 24) * 3));
    }
    
    
    /**
     * 获取增长统计信息
     * @param {Object} productRecord - 商品记录
     * @returns {Object} 统计信息
     */
    getGrowthStats(productRecord) {
        if (!this.hasGrowthFields(productRecord)) {
            return {
                hasGrowthData: false,
                message: '暂无增长数据'
            };
        }
        
        return {
            hasGrowthData: true,
            currentSalesGrowth: productRecord[this.GROWTH_FIELDS.SALES_GROWTH] || 0,
            currentRevenueGrowth: productRecord[this.GROWTH_FIELDS.REVENUE_GROWTH] || 0,
            lastCalculationTime: productRecord[this.GROWTH_FIELDS.CALC_TIME],
            calculationInterval: productRecord[this.GROWTH_FIELDS.CALC_INTERVAL] || 0,
            confidence: productRecord[this.GROWTH_FIELDS.CONFIDENCE] || 0,
            confidenceLevel: this.getConfidenceLevel(productRecord[this.GROWTH_FIELDS.CONFIDENCE] || 0)
        };
    }
    
    /**
     * 获取置信度等级描述
     * @param {number} confidence - 置信度百分比
     * @returns {string} 等级描述
     */
    getConfidenceLevel(confidence) {
        if (confidence >= 90) return '高置信度';
        if (confidence >= 70) return '中等置信度';
        if (confidence >= 50) return '低置信度';
        return '极低置信度';
    }
    
    /**
     * 批量获取增长统计
     * @param {Array} productRecords - 商品记录数组
     * @returns {Object} 批量统计结果
     */
    getBatchGrowthStats(productRecords) {
        const stats = {
            totalProducts: productRecords.length,
            withGrowthData: 0,
            totalSalesGrowth: 0,
            totalRevenueGrowth: 0,
            averageConfidence: 0,
            topGrowers: [],
            confidenceDistribution: {
                high: 0,    // >=90%
                medium: 0,  // 70-89%
                low: 0,     // 50-69%
                veryLow: 0  // <50%
            }
        };
        
        const confidenceSum = [];
        
        productRecords.forEach(record => {
            const growthStats = this.getGrowthStats(record);
            
            if (growthStats.hasGrowthData) {
                stats.withGrowthData++;
                stats.totalSalesGrowth += growthStats.currentSalesGrowth;
                stats.totalRevenueGrowth += growthStats.currentRevenueGrowth;
                confidenceSum.push(growthStats.confidence);
                
                // 统计置信度分布
                if (growthStats.confidence >= 90) stats.confidenceDistribution.high++;
                else if (growthStats.confidence >= 70) stats.confidenceDistribution.medium++;
                else if (growthStats.confidence >= 50) stats.confidenceDistribution.low++;
                else stats.confidenceDistribution.veryLow++;
                
                // 收集增长最快的商品
                if (growthStats.currentSalesGrowth > 0) {
                    stats.topGrowers.push({
                        productName: record.product_name || record.product_id,
                        salesGrowth: growthStats.currentSalesGrowth,
                        revenueGrowth: growthStats.currentRevenueGrowth,
                        confidence: growthStats.confidence
                    });
                }
            }
        });
        
        // 计算平均值
        if (confidenceSum.length > 0) {
            stats.averageConfidence = Math.round(
                confidenceSum.reduce((sum, c) => sum + c, 0) / confidenceSum.length
            );
        }
        
        // 排序增长最快的商品
        stats.topGrowers.sort((a, b) => b.salesGrowth - a.salesGrowth);
        stats.topGrowers = stats.topGrowers.slice(0, 10); // 只保留前10名
        
        return stats;
    }
}

// 如果在Node.js环境中运行，导出模块
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SimpleGrowthCalculator;
}

// 在浏览器环境中，添加到全局对象
if (typeof window !== 'undefined') {
    window.SimpleGrowthCalculator = SimpleGrowthCalculator;
}