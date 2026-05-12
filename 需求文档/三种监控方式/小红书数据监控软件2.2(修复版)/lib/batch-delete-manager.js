/**
 * 批量删除管理器 - 小红书数据监控软件增强版
 * Batch Delete Manager for Xiaohongshu Monitor Extension
 *
 * 功能特色:
 * 1. 批量删除某分类下时间序列字段
 * 2. 基于24小时销量阈值的智能批量删除
 * 3. 安全的预览和确认机制
 * 4. 完整的操作日志和回滚支持
 */

class BatchDeleteManager {
    constructor(localDataManager) {
        this.localDataManager = localDataManager;
        this.operationLogs = [];
        this.backupData = new Map();

        console.log('🗑️ 批量删除管理器已初始化');
    }

    /**
     * ==================== 功能模块1: 时间序列字段清理 ====================
     */

    /**
     * 批量删除指定分类下商品的时间序列字段
     * @param {number} categoryId - 分类ID，null表示所有分类
     * @param {Object} options - 删除选项
     * @returns {Object} 删除结果
     */
    async cleanupTimeSeriesFieldsByCategory(categoryId, options = {}) {
        const {
            dateRange = null,           // 日期范围 {start, end}
            fieldTypes = ['all'],       // 字段类型 ['sales', 'store_sales', 'crawl_time', 'all']
            retainDays = null,          // 保留最近N天
            dryRun = false             // 预览模式
        } = options;

        console.log(`🧹 开始清理时间序列字段 - 分类: ${categoryId || '全部'}`);
        console.log('📋 清理选项:', options);

        try {
            // 1. 获取目标商品
            const targetProducts = await this.getProductsByCategory(categoryId);
            console.log(`📦 找到 ${targetProducts.length} 个商品`);

            if (targetProducts.length === 0) {
                return { success: true, message: '没有找到需要清理的商品', statistics: {} };
            }

            // 2. 分析时间序列字段
            const fieldAnalysis = this.analyzeTimeSeriesFields(targetProducts, options);
            console.log('📊 字段分析结果:', fieldAnalysis);

            if (dryRun) {
                return {
                    success: true,
                    isDryRun: true,
                    preview: fieldAnalysis,
                    message: `预览模式：将清理 ${fieldAnalysis.totalFieldsToDelete} 个时间序列字段`
                };
            }

            // 3. 创建备份
            const backupKey = await this.createBackup(targetProducts, 'timeseries_cleanup');
            console.log(`💾 备份已创建: ${backupKey}`);

            // 4. 执行字段删除
            const deleteResult = await this.executeTimeSeriesFieldDeletion(
                targetProducts,
                fieldAnalysis.fieldsToDelete
            );

            // 5. 记录操作日志
            this.logOperation({
                type: 'timeseries_cleanup',
                categoryId,
                options,
                result: deleteResult,
                backupKey,
                timestamp: new Date()
            });

            return {
                success: true,
                statistics: deleteResult,
                backupKey,
                message: `成功清理 ${deleteResult.totalFieldsDeleted} 个时间序列字段`
            };

        } catch (error) {
            console.error('❌ 时间序列字段清理失败:', error);
            return {
                success: false,
                error: error.message,
                message: '时间序列字段清理失败'
            };
        }
    }

    /**
     * 分析商品的时间序列字段
     * @param {Array} products - 商品列表
     * @param {Object} options - 分析选项
     * @returns {Object} 分析结果
     */
    analyzeTimeSeriesFields(products, options) {
        const { dateRange, fieldTypes, retainDays } = options;
        const fieldsToDelete = [];
        const fieldStatistics = {
            totalFields: 0,
            salesFields: 0,
            storeSalesFields: 0,
            crawlTimeFields: 0,
            dateBreakdown: new Map()
        };

        // 计算截止日期
        let cutoffDate = null;
        if (retainDays) {
            cutoffDate = new Date();
            cutoffDate.setDate(cutoffDate.getDate() - retainDays);
        }

        products.forEach(product => {
            const productFieldsToDelete = [];

            Object.keys(product).forEach(fieldName => {
                // 识别时间序列字段
                const timeSeriesMatch = this.isTimeSeriesField(fieldName);

                if (timeSeriesMatch) {
                    fieldStatistics.totalFields++;
                    const { type, dateStr } = timeSeriesMatch;

                    // 统计字段类型
                    if (type === 'sales') fieldStatistics.salesFields++;
                    else if (type === 'store_sales') fieldStatistics.storeSalesFields++;
                    else if (type === 'crawl_time') fieldStatistics.crawlTimeFields++;

                    // 统计日期分布
                    if (!fieldStatistics.dateBreakdown.has(dateStr)) {
                        fieldStatistics.dateBreakdown.set(dateStr, 0);
                    }
                    fieldStatistics.dateBreakdown.set(dateStr,
                        fieldStatistics.dateBreakdown.get(dateStr) + 1);

                    // 判断是否需要删除
                    let shouldDelete = false;

                    // 按字段类型过滤
                    if (!fieldTypes.includes('all') && !fieldTypes.includes(type)) {
                        return; // 跳过不匹配的字段类型
                    }

                    // 按日期范围过滤
                    if (dateRange) {
                        const fieldDate = new Date(dateStr);
                        if (fieldDate < dateRange.start || fieldDate > dateRange.end) {
                            shouldDelete = true;
                        }
                    }

                    // 按保留天数过滤
                    if (cutoffDate) {
                        const fieldDate = new Date(dateStr);
                        if (fieldDate < cutoffDate) {
                            shouldDelete = true;
                        }
                    }

                    if (shouldDelete) {
                        productFieldsToDelete.push(fieldName);
                    }
                }
            });

            if (productFieldsToDelete.length > 0) {
                fieldsToDelete.push({
                    productId: product.id,
                    product_id: product.product_id,
                    product_name: product.product_name,
                    fields: productFieldsToDelete
                });
            }
        });

        return {
            fieldsToDelete,
            fieldStatistics,
            totalFieldsToDelete: fieldsToDelete.reduce((sum, p) => sum + p.fields.length, 0),
            affectedProducts: fieldsToDelete.length,
            dateBreakdown: Object.fromEntries(fieldStatistics.dateBreakdown)
        };
    }

    /**
     * ==================== 功能模块2: 基于24小时销量阈值的批量删除 ====================
     */

    /**
     * 删除24小时新增销量低于阈值的商品记录
     * @param {number} threshold - 销量阈值
     * @param {number} categoryId - 分类ID，null表示所有分类
     * @param {Object} options - 删除选项
     * @returns {Object} 删除结果
     */
    async deleteProductsByDailySalesThreshold(threshold = 0, categoryId = null, options = {}) {
        const {
            consecutiveDays = 3,        // 连续天数
            analysisDateRange = 7,      // 分析最近N天的数据
            includeZeroSales = true,    // 包含零销量商品
            dryRun = false             // 预览模式
        } = options;

        console.log(`🎯 基于24小时销量阈值批量删除 - 阈值: ${threshold}, 分类: ${categoryId || '全部'}`);
        console.log('📋 删除选项:', options);

        try {
            // 1. 获取目标商品
            const targetProducts = await this.getProductsByCategory(categoryId);
            console.log(`📦 分析 ${targetProducts.length} 个商品`);

            if (targetProducts.length === 0) {
                return { success: true, message: '没有找到需要分析的商品', candidates: [] };
            }

            // 2. 分析符合删除条件的商品
            const deletionCandidates = this.analyzeDailySalesGrowth(
                targetProducts,
                threshold,
                consecutiveDays,
                analysisDateRange,
                includeZeroSales
            );

            console.log(`🔍 找到 ${deletionCandidates.length} 个删除候选商品`);

            if (dryRun) {
                return {
                    success: true,
                    isDryRun: true,
                    candidates: deletionCandidates,
                    message: `预览模式：将删除 ${deletionCandidates.length} 个商品记录`
                };
            }

            if (deletionCandidates.length === 0) {
                return {
                    success: true,
                    message: '没有找到符合删除条件的商品',
                    candidates: []
                };
            }

            // 3. 创建备份
            const productsToDelete = deletionCandidates.map(c => c.product);
            const backupKey = await this.createBackup(productsToDelete, 'threshold_deletion');
            console.log(`💾 备份已创建: ${backupKey}`);

            // 4. 执行商品删除
            const deleteResult = await this.executeProductDeletion(deletionCandidates);

            // 5. 记录操作日志
            this.logOperation({
                type: 'threshold_deletion',
                threshold,
                categoryId,
                options,
                result: deleteResult,
                backupKey,
                timestamp: new Date()
            });

            return {
                success: true,
                statistics: deleteResult,
                backupKey,
                deletedProducts: deletionCandidates.length,
                message: `成功删除 ${deleteResult.successCount} 个低增长商品`
            };

        } catch (error) {
            console.error('❌ 基于阈值的批量删除失败:', error);
            return {
                success: false,
                error: error.message,
                message: '基于阈值的批量删除失败'
            };
        }
    }

    /**
     * 分析商品的24小时销量增长情况
     * @param {Array} products - 商品列表
     * @param {number} threshold - 销量阈值
     * @param {number} consecutiveDays - 连续天数
     * @param {number} analysisDateRange - 分析天数
     * @param {boolean} includeZeroSales - 包含零销量
     * @returns {Array} 删除候选商品
     */
    analyzeDailySalesGrowth(products, threshold, consecutiveDays, analysisDateRange, includeZeroSales) {
        const candidates = [];
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(endDate.getDate() - analysisDateRange);

        console.log(`📊 分析日期范围: ${startDate.toISOString().split('T')[0]} 至 ${endDate.toISOString().split('T')[0]}`);

        products.forEach(product => {
            const dailySalesData = this.extractDailySalesData(product, startDate, endDate);

            if (dailySalesData.length === 0) {
                console.log(`⏭️ 跳过商品 ${product.product_id}: 无24小时销量数据`);
                return;
            }

            // 检查连续低增长天数
            const consecutiveLowGrowthDays = this.calculateConsecutiveLowGrowthDays(
                dailySalesData,
                threshold,
                includeZeroSales
            );

            if (consecutiveLowGrowthDays >= consecutiveDays) {
                candidates.push({
                    product: product,
                    reason: {
                        type: 'low_daily_sales_growth',
                        threshold: threshold,
                        consecutiveDays: consecutiveLowGrowthDays,
                        requiredDays: consecutiveDays,
                        dailySalesData: dailySalesData,
                        analysisRange: {
                            start: startDate.toISOString().split('T')[0],
                            end: endDate.toISOString().split('T')[0]
                        }
                    }
                });

                console.log(`🎯 删除候选: ${product.product_name || product.product_id} - 连续${consecutiveLowGrowthDays}天低增长`);
            }
        });

        return candidates;
    }

    /**
     * 提取商品的24小时销量数据
     * @param {Object} product - 商品记录
     * @param {Date} startDate - 开始日期
     * @param {Date} endDate - 结束日期
     * @returns {Array} 销量数据数组
     */
    extractDailySalesData(product, startDate, endDate) {
        const salesData = [];

        Object.keys(product).forEach(fieldName => {
            const match = fieldName.match(/^新增销量_(\d{4}-\d{2}-\d{2})$/);

            if (match) {
                const dateStr = match[1];
                const fieldDate = new Date(dateStr);

                if (fieldDate >= startDate && fieldDate <= endDate) {
                    salesData.push({
                        date: dateStr,
                        newSales: product[fieldName] || 0,
                        newRevenue: product[`新增销售额_${dateStr}`] || 0
                    });
                }
            }
        });

        // 按日期排序
        return salesData.sort((a, b) => new Date(a.date) - new Date(b.date));
    }

    /**
     * 计算连续低增长天数
     * @param {Array} dailySalesData - 销量数据
     * @param {number} threshold - 阈值
     * @param {boolean} includeZeroSales - 包含零销量
     * @returns {number} 连续低增长天数
     */
    calculateConsecutiveLowGrowthDays(dailySalesData, threshold, includeZeroSales) {
        let maxConsecutiveDays = 0;
        let currentConsecutiveDays = 0;

        dailySalesData.forEach(dayData => {
            const isLowGrowth = includeZeroSales ?
                dayData.newSales <= threshold :
                dayData.newSales < threshold;

            if (isLowGrowth) {
                currentConsecutiveDays++;
                maxConsecutiveDays = Math.max(maxConsecutiveDays, currentConsecutiveDays);
            } else {
                currentConsecutiveDays = 0;
            }
        });

        return maxConsecutiveDays;
    }

    /**
     * ==================== 核心执行方法 ====================
     */

    /**
     * 执行时间序列字段删除
     * @param {Array} products - 商品列表
     * @param {Array} fieldsToDelete - 要删除的字段信息
     * @returns {Object} 删除结果统计
     */
    async executeTimeSeriesFieldDeletion(products, fieldsToDelete) {
        const results = {
            totalProductsProcessed: 0,
            totalFieldsDeleted: 0,
            successCount: 0,
            errorCount: 0,
            errors: []
        };

        for (const productInfo of fieldsToDelete) {
            try {
                results.totalProductsProcessed++;

                // 获取完整的商品记录
                const product = products.find(p => p.id === productInfo.productId);
                if (!product) {
                    throw new Error(`商品 ID ${productInfo.productId} 不存在`);
                }

                // 删除指定字段
                productInfo.fields.forEach(fieldName => {
                    if (product.hasOwnProperty(fieldName)) {
                        delete product[fieldName];
                        results.totalFieldsDeleted++;
                    }
                });

                // 更新商品记录
                await this.localDataManager.updateProduct(product);
                results.successCount++;

                console.log(`✅ 商品 ${product.product_name || product.product_id}: 删除 ${productInfo.fields.length} 个时间序列字段`);

            } catch (error) {
                results.errorCount++;
                results.errors.push({
                    productId: productInfo.productId,
                    error: error.message
                });
                console.error(`❌ 删除字段失败 - 商品 ${productInfo.productId}:`, error);
            }
        }

        return results;
    }

    /**
     * 执行商品删除
     * @param {Array} deletionCandidates - 删除候选商品
     * @returns {Object} 删除结果统计
     */
    async executeProductDeletion(deletionCandidates) {
        const results = {
            totalCandidates: deletionCandidates.length,
            successCount: 0,
            errorCount: 0,
            errors: []
        };

        for (const candidate of deletionCandidates) {
            try {
                const product = candidate.product;

                // 删除商品及相关数据
                await this.localDataManager.deleteProduct(product.id);
                results.successCount++;

                console.log(`✅ 已删除商品: ${product.product_name || product.product_id} (${candidate.reason.type})`);

            } catch (error) {
                results.errorCount++;
                results.errors.push({
                    productId: candidate.product.id,
                    productName: candidate.product.product_name || candidate.product.product_id,
                    error: error.message
                });
                console.error(`❌ 删除商品失败 - ${candidate.product.product_id}:`, error);
            }
        }

        return results;
    }

    /**
     * ==================== 辅助工具方法 ====================
     */

    /**
     * 根据分类获取商品
     * @param {number|null} categoryId - 分类ID
     * @returns {Array} 商品列表
     */
    async getProductsByCategory(categoryId) {
        if (categoryId) {
            const result = await this.localDataManager.getProducts(
                categoryId,
                {},
                { page: 1, limit: 10000 }
            );
            return result.products || [];
        } else {
            return await this.localDataManager.getAllProducts();
        }
    }

    /**
     * 判断是否为时间序列字段
     * @param {string} fieldName - 字段名
     * @returns {Object|null} 匹配结果
     */
    isTimeSeriesField(fieldName) {
        // 商品销量字段: 商品销量（2025-09-20）
        let match = fieldName.match(/^商品销量（(\d{4}-\d{2}-\d{2})）$/);
        if (match) {
            return { type: 'sales', dateStr: match[1] };
        }

        // 店铺销量字段: 店铺销量（2025-09-20）
        match = fieldName.match(/^店铺销量（(\d{4}-\d{2}-\d{2})）$/);
        if (match) {
            return { type: 'store_sales', dateStr: match[1] };
        }

        // 爬取时间字段: 爬取时间（2025-09-20）
        match = fieldName.match(/^爬取时间（(\d{4}-\d{2}-\d{2})）$/);
        if (match) {
            return { type: 'crawl_time', dateStr: match[1] };
        }

        // 新增销量字段: 新增销量_2025-09-20
        match = fieldName.match(/^新增销量_(\d{4}-\d{2}-\d{2})$/);
        if (match) {
            return { type: 'daily_growth', dateStr: match[1] };
        }

        return null;
    }

    /**
     * 创建数据备份
     * @param {Array} products - 要备份的商品
     * @param {string} operationType - 操作类型
     * @returns {string} 备份键
     */
    async createBackup(products, operationType) {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const backupKey = `batch_delete_backup_${operationType}_${timestamp}`;

        const backupData = {
            timestamp: new Date(),
            operationType,
            products: products.map(p => ({ ...p })), // 深拷贝
            productCount: products.length
        };

        try {
            // 尝试保存到localStorage
            localStorage.setItem(backupKey, JSON.stringify(backupData));
            this.backupData.set(backupKey, backupData);

            console.log(`💾 备份已创建: ${backupKey} (${products.length} 个商品)`);
            return backupKey;

        } catch (error) {
            console.warn('⚠️ localStorage备份失败，仅保存到内存:', error);
            this.backupData.set(backupKey, backupData);
            return backupKey;
        }
    }

    /**
     * 记录操作日志
     * @param {Object} logEntry - 日志条目
     */
    logOperation(logEntry) {
        this.operationLogs.push(logEntry);
        console.log('📝 操作日志已记录:', logEntry);

        // 只保留最近100条日志
        if (this.operationLogs.length > 100) {
            this.operationLogs.shift();
        }
    }

    /**
     * 获取操作历史
     * @returns {Array} 操作日志列表
     */
    getOperationHistory() {
        return [...this.operationLogs].reverse(); // 最新的在前
    }

    /**
     * 获取备份列表
     * @returns {Array} 备份列表
     */
    getAvailableBackups() {
        return Array.from(this.backupData.entries()).map(([key, data]) => ({
            key,
            timestamp: data.timestamp,
            operationType: data.operationType,
            productCount: data.productCount
        }));
    }

    /**
     * 恢复备份数据
     * @param {string} backupKey - 备份键
     * @returns {Object} 恢复结果
     */
    async restoreFromBackup(backupKey) {
        try {
            let backupData = this.backupData.get(backupKey);

            if (!backupData) {
                // 尝试从localStorage恢复
                const stored = localStorage.getItem(backupKey);
                if (stored) {
                    backupData = JSON.parse(stored);
                } else {
                    throw new Error('备份数据不存在');
                }
            }

            console.log(`🔄 开始恢复备份: ${backupKey}`);

            let restoredCount = 0;
            const errors = [];

            for (const product of backupData.products) {
                try {
                    await this.localDataManager.updateProduct(product);
                    restoredCount++;
                } catch (error) {
                    errors.push({
                        productId: product.id,
                        error: error.message
                    });
                }
            }

            console.log(`✅ 备份恢复完成: ${restoredCount}/${backupData.products.length} 个商品`);

            return {
                success: true,
                restoredCount,
                totalCount: backupData.products.length,
                errors,
                message: `成功恢复 ${restoredCount} 个商品`
            };

        } catch (error) {
            console.error('❌ 备份恢复失败:', error);
            return {
                success: false,
                error: error.message,
                message: '备份恢复失败'
            };
        }
    }
}

// 导出到全局
if (typeof window !== 'undefined') {
    window.BatchDeleteManager = BatchDeleteManager;
}

// Node.js环境导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BatchDeleteManager;
}