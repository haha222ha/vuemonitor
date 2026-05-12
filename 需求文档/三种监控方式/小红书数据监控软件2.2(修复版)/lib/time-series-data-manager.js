/**
 * 时间序列数据管理器
 * 负责管理商品记录中的动态时间序列字段
 */
class TimeSeriesDataManager {
    constructor() {
        this.fieldPrefixes = DateFormatter.getTimeSeriesFieldPrefixes();
        // 初始化简化增长计算器
        this.growthCalculator = new SimpleGrowthCalculator();
        console.log('📊 时间序列数据管理器已初始化，包含增长计算功能');
    }
    
    /**
     * 智能更新/创建时间序列字段
     * @param {Object} productRecord - 商品记录对象
     * @param {Object} newData - 新的爬取数据
     * @param {Date} crawlDate - 爬取日期，默认为当前日期
     * @returns {Object} 操作结果
     */
    async upsertTimeSeriesData(productRecord, newData, crawlDate = new Date()) {
        try {
            const fieldNames = DateFormatter.generateFieldNames(crawlDate);
            const dateStr = DateFormatter.getChineseDateFormat(crawlDate);
            console.log(`⏰ [时间序列] 爬取时间: ${crawlDate.toLocaleString()}`);
            
            // 1. 检查是否已有当天字段
            const hasFields = this.hasDateFields(productRecord, fieldNames);
            
            if (hasFields) {
                // 当天多次爬取：更新现有字段
                console.log(`📝 [当天更新] ${dateStr}`);
                console.log(`   ├─ 商品销量: ${productRecord[fieldNames.productSales]} → ${newData.productSales}`);
                console.log(`   └─ 店铺销量: ${productRecord[fieldNames.storeSales]} → ${newData.storeSales}`);
                
                if (newData.productSales !== undefined) {
                    productRecord[fieldNames.productSales] = newData.productSales;
                }
                if (newData.storeSales !== undefined) {
                    productRecord[fieldNames.storeSales] = newData.storeSales;
                }
                productRecord[fieldNames.crawlTime] = crawlDate.toISOString();
                
            } else {
                // 新一天爬取：创建新字段
                console.log(`✨ [新建字段] ${dateStr}`);
                console.log(`   ├─ 商品销量: ${newData.productSales || 0}`);
                console.log(`   └─ 店铺销量: ${newData.storeSales || 0}`);
                
                productRecord[fieldNames.productSales] = newData.productSales || 0;
                productRecord[fieldNames.storeSales] = newData.storeSales || 0;
                productRecord[fieldNames.crawlTime] = crawlDate.toISOString();
            }
            
            // 2. 更新全局时间戳
            productRecord.last_crawled_at = crawlDate;
            productRecord.updated_at = new Date();
            
            // 3. 统计时间序列字段数量
            const seriesCount = this.getTimeSeriesCount(productRecord);
            
            // 4. 自动计算24小时增长数据
            const growthResult = await this.growthCalculator.updateGrowthFields(productRecord, newData, crawlDate);
            console.log('🚀 24小时增长计算完成:', growthResult.success ? 
                `销量+${growthResult.sales24h}, 销售额+${growthResult.revenue24h}` : 
                growthResult.error);
            
            return {
                success: true,
                operation: hasFields ? 'updated_day' : 'created_day',
                dateStr: dateStr,
                fields: fieldNames,
                timeSeriesCount: seriesCount,
                productSales: newData.productSales,
                storeSales: newData.storeSales,
                crawlTime: crawlDate.toISOString(),
                growthCalculation: growthResult
            };
            
        } catch (error) {
            console.error('❌ 时间序列数据更新失败:', error);
            return {
                success: false,
                error: error.message,
                operation: 'failed'
            };
        }
    }
    
    /**
     * 检查是否已有指定日期的字段
     * @param {Object} record - 商品记录
     * @param {Object} fieldNames - 字段名对象
     * @returns {boolean} 是否已有字段
     */
    hasDateFields(record, fieldNames) {
        return record.hasOwnProperty(fieldNames.productSales) || 
               record.hasOwnProperty(fieldNames.storeSales) ||
               record.hasOwnProperty(fieldNames.crawlTime);
    }
    
    /**
     * 获取商品的销量历史数据
     * @param {Object} productRecord - 商品记录
     * @returns {Array} 按时间排序的销量历史数组
     */
    getSalesHistory(productRecord) {
        const history = [];
        const allKeys = Object.keys(productRecord);
        
        // 找出所有销量字段
        const salesFields = allKeys.filter(key => key.startsWith('商品销量（') && key.endsWith('）'));
        
        salesFields.forEach(field => {
            const dateStr = DateFormatter.extractDateFromFieldName(field);
            if (dateStr) {
                const storeSalesField = `店铺销量（${dateStr}）`;
                const crawlTimeField = `爬取时间（${dateStr}）`;
                
                history.push({
                    date: dateStr,
                    productSales: productRecord[field] || 0,
                    storeSales: productRecord[storeSalesField] || 0,
                    crawlTime: productRecord[crawlTimeField] || null
                });
            }
        });
        
        // 按爬取时间排序
        return history.sort((a, b) => {
            if (!a.crawlTime || !b.crawlTime) return 0;
            return new Date(a.crawlTime) - new Date(b.crawlTime);
        });
    }
    
    /**
     * 获取时间序列字段数量统计
     * @param {Object} productRecord - 商品记录
     * @returns {Object} 统计信息
     */
    getTimeSeriesCount(productRecord) {
        const allKeys = Object.keys(productRecord);
        const timeSeriesFields = allKeys.filter(key => DateFormatter.isTimeSeriesField(key));
        
        const stats = {
            total: timeSeriesFields.length,
            salesFields: 0,
            priceFields: 0,
            timeFields: 0,
            uniqueDays: 0
        };
        
        const uniqueDates = new Set();
        
        timeSeriesFields.forEach(field => {
            if (field.startsWith('商品销量（')) {
                stats.salesFields++;
                const dateStr = DateFormatter.extractDateFromFieldName(field);
                if (dateStr) uniqueDates.add(dateStr);
            } else if (field.startsWith('爬取时间（')) {
                stats.timeFields++;
            }
        });
        
        stats.uniqueDays = uniqueDates.size;
        return stats;
    }
    
    /**
     * 获取最新的销量数据
     * @param {Object} productRecord - 商品记录
     * @returns {Object|null} 最新销量数据
     */
    getLatestSalesData(productRecord) {
        const history = this.getSalesHistory(productRecord);
        return history.length > 0 ? history[history.length - 1] : null;
    }
    
    /**
     * 计算销量增长趋势
     * @param {Object} productRecord - 商品记录
     * @param {number} days - 计算天数，默认7天
     * @returns {Object} 增长趋势分析
     */
    calculateSalesGrowthTrend(productRecord, days = 7) {
        const history = this.getSalesHistory(productRecord);
        if (history.length < 2) {
            return {
                trend: 'insufficient_data',
                message: '数据不足，无法计算趋势'
            };
        }
        
        // 取最近N天的数据
        const recentHistory = history.slice(-days);
        const firstDay = recentHistory[0];
        const lastDay = recentHistory[recentHistory.length - 1];
        
        const productGrowth = lastDay.productSales - firstDay.productSales;
        const storeGrowth = lastDay.storeSales - firstDay.storeSales;
        
        const productGrowthRate = firstDay.productSales > 0 ? 
            ((productGrowth / firstDay.productSales) * 100) : 0;
        const storeGrowthRate = firstDay.storeSales > 0 ? 
            ((storeGrowth / firstDay.storeSales) * 100) : 0;
        
        return {
            period: `${recentHistory.length}天`,
            productGrowth: {
                absolute: productGrowth,
                percentage: productGrowthRate.toFixed(2) + '%',
                from: firstDay.productSales,
                to: lastDay.productSales
            },
            storeGrowth: {
                absolute: storeGrowth,
                percentage: storeGrowthRate.toFixed(2) + '%',
                from: firstDay.storeSales,
                to: lastDay.storeSales
            },
            trend: productGrowthRate > 10 ? 'strong_growth' : 
                   productGrowthRate > 0 ? 'growth' : 
                   productGrowthRate < -10 ? 'strong_decline' : 'decline',
            dailyAverage: {
                productSales: Math.round(productGrowth / recentHistory.length),
                storeSales: Math.round(storeGrowth / recentHistory.length)
            }
        };
    }
    
    /**
     * 检测销量异常
     * @param {Object} productRecord - 商品记录
     * @returns {Array} 异常检测结果
     */
    detectSalesAnomalies(productRecord) {
        const history = this.getSalesHistory(productRecord);
        const anomalies = [];
        
        if (history.length < 3) {
            return anomalies; // 数据不足，无法检测异常
        }
        
        // 计算平均日增长量
        const dailyGrowths = [];
        for (let i = 1; i < history.length; i++) {
            const growth = history[i].productSales - history[i-1].productSales;
            dailyGrowths.push(growth);
        }
        
        const avgGrowth = dailyGrowths.reduce((sum, g) => sum + g, 0) / dailyGrowths.length;
        const stdDev = Math.sqrt(dailyGrowths.reduce((sum, g) => sum + Math.pow(g - avgGrowth, 2), 0) / dailyGrowths.length);
        
        // 检测异常波动
        for (let i = 1; i < history.length; i++) {
            const growth = history[i].productSales - history[i-1].productSales;
            const deviation = Math.abs(growth - avgGrowth);
            
            if (deviation > stdDev * 2.5) { // 2.5倍标准差视为异常
                anomalies.push({
                    type: growth > avgGrowth ? 'sudden_increase' : 'sudden_decrease',
                    date: history[i].date,
                    value: history[i].productSales,
                    previousValue: history[i-1].productSales,
                    change: growth,
                    severity: deviation > stdDev * 3 ? 'high' : 'medium',
                    message: `${history[i].date}销量${growth > 0 ? '激增' : '骤降'} ${Math.abs(growth)}`
                });
            }
        }
        
        return anomalies;
    }
    
    /**
     * 清理过期的时间序列字段（可选功能）
     * @param {Object} productRecord - 商品记录
     * @param {number} retainDays - 保留天数，默认90天
     * @returns {Object} 清理结果
     */
    cleanupOldTimeSeriesFields(productRecord, retainDays = 90) {
        const allKeys = Object.keys(productRecord);
        const timeSeriesFields = allKeys.filter(key => DateFormatter.isTimeSeriesField(key));
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - retainDays);
        
        const fieldsToDelete = [];
        
        timeSeriesFields.forEach(field => {
            const dateStr = DateFormatter.extractDateFromFieldName(field);
            if (dateStr) {
                const fieldDate = DateFormatter.parseChineseDateString(dateStr);
                if (fieldDate && fieldDate < cutoffDate) {
                    fieldsToDelete.push(field);
                }
            }
        });
        
        // 删除过期字段
        fieldsToDelete.forEach(field => {
            delete productRecord[field];
        });
        
        return {
            deletedCount: fieldsToDelete.length,
            deletedFields: fieldsToDelete,
            retainDays: retainDays
        };
    }
}

// 如果在Node.js环境中运行，导出模块
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TimeSeriesDataManager;
}

// 在浏览器环境中，添加到全局对象
if (typeof window !== 'undefined') {
    window.TimeSeriesDataManager = TimeSeriesDataManager;
}