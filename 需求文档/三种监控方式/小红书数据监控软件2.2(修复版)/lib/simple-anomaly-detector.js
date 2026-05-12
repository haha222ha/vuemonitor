/**
 * 简化异常检测器
 * 基于24小时增长数据进行简单阈值检测
 */
class SimpleAnomalyDetector {
    constructor() {
        // 异常检测阈值配置
        this.thresholds = {
            销量: 50,      // 24小时新增销量超过50件视为异常
            销售额: 500    // 24小时新增销售额超过500元视为异常
        };

        // 检测规则配置（兼容旧接口）
        this.detectionRules = {
            salesSurge: {
                enabled: true,
                threshold: this.thresholds.销量,
                minBaseSales: 5
            },
            revenueSurge: {
                enabled: true,
                threshold: this.thresholds.销售额
            },
            priceAnomaly: {
                enabled: true,
                changeThreshold: 50
            }
        };

        this.localDataManager = null;
        this.componentBridge = null;

        console.log('🔍 简化异常检测器已初始化', this.thresholds);
    }

    /**
     * 检测单个商品是否异常
     * @param {Object} product - 商品对象
     * @returns {Object} 检测结果
     */
    detectProductAnomaly(product) {
        try {
            // 获取24小时增长数据
            const sales24h = product['新增销量'] || 0;
            const revenue24h = product['新增销售额'] || 0;

            // 简单阈值检测
            const salesAnomaly = sales24h > this.thresholds.销量;
            const revenueAnomaly = revenue24h > this.thresholds.销售额;
            const isAnomaly = salesAnomaly || revenueAnomaly;

            const result = {
                productId: product.id,
                productName: product.title || product.name || '未知商品',
                isAnomaly: isAnomaly,
                sales24h: sales24h,
                revenue24h: revenue24h,
                triggers: [],
                confidence: product['增长置信度'] || 'unknown',
                checkTime: new Date().toISOString()
            };

            // 记录触发的异常类型
            if (salesAnomaly) {
                result.triggers.push({
                    type: 'sales_spike',
                    threshold: this.thresholds.销量,
                    actual: sales24h,
                    message: `24小时新增销量${sales24h}件，超过阈值${this.thresholds.销量}件`
                });
            }

            if (revenueAnomaly) {
                result.triggers.push({
                    type: 'revenue_spike',
                    threshold: this.thresholds.销售额,
                    actual: revenue24h,
                    message: `24小时新增销售额${revenue24h}元，超过阈值${this.thresholds.销售额}元`
                });
            }

            return result;

        } catch (error) {
            console.error('❌ 商品异常检测失败:', error);
            return {
                productId: product.id,
                productName: product.title || product.name || '未知商品',
                isAnomaly: false,
                error: error.message,
                checkTime: new Date().toISOString()
            };
        }
    }

    /**
     * 批量检测商品异常
     * @param {Array} products - 商品列表
     * @param {Array} categoryIds - 可选的分类ID过滤
     * @returns {Object} 批量检测结果
     */
    async detectBatchAnomalies(products, categoryIds = null) {
        console.log(`🔍 开始批量异常检测，商品数量: ${products.length}`);

        try {
            // 过滤指定分类的商品（如果指定了分类）
            let targetProducts = products;
            if (categoryIds && categoryIds.length > 0) {
                targetProducts = products.filter(product =>
                    categoryIds.includes(product.category_id)
                );
                console.log(`📊 按分类过滤后商品数量: ${targetProducts.length}`);
            }

            const results = {
                total: targetProducts.length,
                checked: 0,
                anomalies: [],
                normal: [],
                errors: [],
                summary: {
                    anomalyCount: 0,
                    salesAnomalyCount: 0,
                    revenueAnomalyCount: 0,
                    bothAnomalyCount: 0
                },
                checkTime: new Date().toISOString(),
                categoryFilter: categoryIds
            };

            // 逐个检测商品
            for (const product of targetProducts) {
                const detection = this.detectProductAnomaly(product);
                results.checked++;

                if (detection.error) {
                    results.errors.push(detection);
                } else if (detection.isAnomaly) {
                    results.anomalies.push(detection);
                    results.summary.anomalyCount++;

                    // 统计异常类型
                    const hasSalesAnomaly = detection.triggers.some(t => t.type === 'sales_spike');
                    const hasRevenueAnomaly = detection.triggers.some(t => t.type === 'revenue_spike');

                    if (hasSalesAnomaly) results.summary.salesAnomalyCount++;
                    if (hasRevenueAnomaly) results.summary.revenueAnomalyCount++;
                    if (hasSalesAnomaly && hasRevenueAnomaly) results.summary.bothAnomalyCount++;

                } else {
                    results.normal.push(detection);
                }
            }

            console.log(`✅ 批量异常检测完成: ${results.summary.anomalyCount}/${results.total} 异常`);
            return results;

        } catch (error) {
            console.error('❌ 批量异常检测失败:', error);
            return {
                total: products.length,
                checked: 0,
                anomalies: [],
                normal: [],
                errors: [{ error: error.message, checkTime: new Date().toISOString() }],
                summary: { anomalyCount: 0, salesAnomalyCount: 0, revenueAnomalyCount: 0, bothAnomalyCount: 0 }
            };
        }
    }

    /**
     * 更新异常检测阈值
     * @param {Object} newThresholds - 新的阈值配置
     */
    updateThresholds(newThresholds) {
        this.thresholds = { ...this.thresholds, ...newThresholds };
        console.log('🔧 异常检测阈值已更新:', this.thresholds);
    }

    /**
     * 获取当前阈值配置
     * @returns {Object} 阈值配置
     */
    getThresholds() {
        return { ...this.thresholds };
    }

    /**
     * 验证商品数据完整性
     * @param {Object} product - 商品对象
     * @returns {Object} 验证结果
     */
    validateProductData(product) {
        const validation = {
            valid: true,
            missing: [],
            warnings: []
        };

        // 检查必需字段
        if (!product.id) {
            validation.valid = false;
            validation.missing.push('id');
        }

        if (product['新增销量'] === undefined) {
            validation.warnings.push('缺少24小时新增销量数据');
        }

        if (product['新增销售额'] === undefined) {
            validation.warnings.push('缺少24小时新增销售额数据');
        }

        if (!product.title && !product.name) {
            validation.warnings.push('缺少商品名称');
        }

        return validation;
    }

    /**
     * 生成异常检测报告
     * @param {Object} batchResults - 批量检测结果
     * @returns {String} 格式化报告
     */
    generateReport(batchResults) {
        const { total, summary, checkTime, categoryFilter } = batchResults;
        const anomalyRate = ((summary.anomalyCount / total) * 100).toFixed(1);

        let report = `📊 异常检测报告\n`;
        report += `检测时间: ${new Date(checkTime).toLocaleString()}\n`;
        report += `商品总数: ${total}\n`;

        if (categoryFilter && categoryFilter.length > 0) {
            report += `分类筛选: ${categoryFilter.join(', ')}\n`;
        }

        report += `异常商品: ${summary.anomalyCount} (${anomalyRate}%)\n`;
        report += `销量异常: ${summary.salesAnomalyCount}\n`;
        report += `销售额异常: ${summary.revenueAnomalyCount}\n`;
        report += `双重异常: ${summary.bothAnomalyCount}\n`;

        report += `\n检测阈值:\n`;
        report += `- 销量阈值: ${this.thresholds.销量}件\n`;
        report += `- 销售额阈值: ${this.thresholds.销售额}元\n`;

        return report;
    }

    /**
     * 设置依赖服务
     * @param {Object} localDataManager - 本地数据管理器
     * @param {Object} componentBridge - 组件桥梁
     */
    setDependencies(localDataManager, componentBridge) {
        this.localDataManager = localDataManager;
        this.componentBridge = componentBridge;
    }

    /**
     * 运行完整异常检测
     * @param {Object} options - 检测选项
     * @returns {Object} 检测结果
     */
    async runFullDetection(options = {}) {
        console.log('🔍 开始运行完整异常检测...');

        try {
            // 获取所有商品数据
            const allProducts = this.localDataManager ?
                await this.localDataManager.getAllProducts() : [];

            if (allProducts.length === 0) {
                return {
                    success: false,
                    error: '没有找到商品数据',
                    anomaliesFound: 0
                };
            }

            // 获取选择的分类（如果有分类选择器）
            let selectedCategories = null;
            if (window.getSelectedAnomalyCategories) {
                selectedCategories = window.getSelectedAnomalyCategories();
            } else if (window.xiaohongShuMonitor?.getSelectedAnomalyCategories) {
                selectedCategories = window.xiaohongShuMonitor.getSelectedAnomalyCategories();
            }

            // 执行批量检测
            const batchResults = await this.detectBatchAnomalies(allProducts, selectedCategories);

            // 更新数据库中的异常状态
            if (this.localDataManager) {
                for (const anomaly of batchResults.anomalies) {
                    await this.localDataManager.updateProductAnomalyStatus(anomaly.productId, true);
                }

                for (const normal of batchResults.normal) {
                    await this.localDataManager.updateProductAnomalyStatus(normal.productId, false);
                }
            }

            // 发送进度更新
            if (options.onProgress) {
                options.onProgress({
                    stage: 'completed',
                    progress: 100,
                    message: `检测完成，发现 ${batchResults.summary.anomalyCount} 个异常`
                });
            }

            return {
                success: true,
                anomaliesFound: batchResults.summary.anomalyCount,
                batchResults: batchResults,
                report: this.generateReport(batchResults)
            };

        } catch (error) {
            console.error('❌ 完整异常检测失败:', error);
            return {
                success: false,
                error: error.message,
                anomaliesFound: 0
            };
        }
    }

    /**
     * 检测单个商品异常
     * @param {string} productId - 商品ID
     * @param {Object} newData - 新数据
     * @returns {Object|null} 异常信息或null
     */
    async checkProductAnomaly(productId, newData) {
        try {
            // 构造商品对象进行检测
            const productToCheck = {
                id: productId,
                title: newData.title || newData.name,
                '新增销量': newData['新增销量'] || 0,
                '新增销售额': newData['新增销售额'] || 0,
                ...newData
            };

            const detection = this.detectProductAnomaly(productToCheck);

            if (detection.isAnomaly) {
                // 更新数据库异常状态
                if (this.localDataManager) {
                    await this.localDataManager.updateProductAnomalyStatus(productId, true);
                }

                return {
                    productId: productId,
                    description: detection.triggers.map(t => t.message).join('; '),
                    triggers: detection.triggers,
                    confidence: detection.confidence || 'high'
                };
            }

            return null;

        } catch (error) {
            console.error('❌ 单个商品异常检测失败:', error);
            return null;
        }
    }

    /**
     * 获取异常统计信息
     * @param {number} days - 统计天数
     * @returns {Object} 异常统计
     */
    async getAnomalyStats(days = 7) {
        try {
            if (!this.localDataManager) {
                return {
                    critical: 0,
                    warning: 0,
                    info: 0,
                    total: 0
                };
            }

            // 获取异常商品
            const anomalyProducts = await this.localDataManager.getAnomalyProducts();

            // 简化统计 - 根据触发条件数量分级
            let critical = 0, warning = 0, info = 0;

            for (const product of anomalyProducts) {
                const detection = this.detectProductAnomaly(product);

                if (detection.triggers.length >= 2) {
                    critical++; // 多重异常视为严重
                } else if (detection.triggers.length === 1) {
                    warning++; // 单一异常视为警告
                } else {
                    info++; // 其他视为信息
                }
            }

            return {
                critical,
                warning,
                info,
                total: anomalyProducts.length
            };

        } catch (error) {
            console.error('❌ 获取异常统计失败:', error);
            return { critical: 0, warning: 0, info: 0, total: 0 };
        }
    }

    /**
     * 更新检测规则
     * @param {Object} newRules - 新规则
     */
    updateDetectionRules(newRules) {
        try {
            this.detectionRules = { ...this.detectionRules, ...newRules };

            // 同步更新阈值配置
            if (newRules.salesSurge) {
                this.thresholds.销量 = newRules.salesSurge.threshold || this.thresholds.销量;
            }
            if (newRules.revenueSurge) {
                this.thresholds.销售额 = newRules.revenueSurge.threshold || this.thresholds.销售额;
            }

            console.log('🔧 异常检测规则已更新:', this.detectionRules);
        } catch (error) {
            console.error('❌ 更新检测规则失败:', error);
        }
    }

    /**
     * 重置为默认规则
     */
    resetToDefaultRules() {
        this.thresholds = {
            销量: 50,
            销售额: 500
        };

        this.detectionRules = {
            salesSurge: {
                enabled: true,
                threshold: this.thresholds.销量,
                minBaseSales: 5
            },
            revenueSurge: {
                enabled: true,
                threshold: this.thresholds.销售额
            },
            priceAnomaly: {
                enabled: true,
                changeThreshold: 50
            }
        };

        console.log('🔄 异常检测规则已重置为默认值');
    }

    /**
     * 发送批量异常通知
     * @param {Object} result - 检测结果
     */
    notifyAnomalies(result) {
        try {
            if (this.componentBridge) {
                this.componentBridge.sendMessage('data-manager', 'ANOMALY_DETECTION_COMPLETED', {
                    success: result.success,
                    anomaliesFound: result.anomaliesFound,
                    timestamp: Date.now(),
                    batchResults: result.batchResults
                });
            }

            console.log(`📢 异常检测通知已发送: ${result.anomaliesFound} 个异常`);
        } catch (error) {
            console.error('❌ 发送异常通知失败:', error);
        }
    }

    /**
     * 发送单个异常通知
     * @param {Object} anomaly - 异常信息
     */
    notifySingleAnomaly(anomaly) {
        try {
            if (this.componentBridge) {
                this.componentBridge.sendMessage('data-manager', 'SINGLE_ANOMALY_DETECTED', {
                    anomaly: anomaly,
                    timestamp: Date.now()
                });
            }

            console.log(`🚨 单个异常通知已发送: ${anomaly.description}`);
        } catch (error) {
            console.error('❌ 发送单个异常通知失败:', error);
        }
    }

    /**
     * 使用自定义阈值运行异常检测
     * @param {Object} customThresholds - 自定义阈值 {sales: number, revenue: number}
     * @param {Array} selectedCategoryIds - 选中的分类ID
     * @returns {Object} 检测结果
     */
    async runAnomalyDetectionWithCustomThresholds(customThresholds, selectedCategoryIds = null) {
        console.log('🔍 使用自定义阈值运行异常检测...', customThresholds);

        try {
            // 更新阈值
            if (customThresholds) {
                const newThresholds = {};
                if (customThresholds.sales) newThresholds.销量 = customThresholds.sales;
                if (customThresholds.revenue) newThresholds.销售额 = customThresholds.revenue;
                this.updateThresholds(newThresholds);
            }

            // 获取所有商品数据
            const allProducts = this.localDataManager ?
                await this.localDataManager.getAllProducts() : [];

            if (allProducts.length === 0) {
                return {
                    success: false,
                    error: '没有找到商品数据',
                    anomaliesFound: 0,
                    checkedCount: 0
                };
            }

            // 执行批量检测
            const batchResults = await this.detectBatchAnomalies(allProducts, selectedCategoryIds);

            // 更新数据库中的异常状态
            if (this.localDataManager) {
                for (const anomaly of batchResults.anomalies) {
                    await this.localDataManager.updateProductAnomalyStatus(anomaly.productId, true);
                }

                for (const normal of batchResults.normal) {
                    await this.localDataManager.updateProductAnomalyStatus(normal.productId, false);
                }
            }

            return {
                success: true,
                anomaliesFound: batchResults.summary.anomalyCount,
                checkedCount: batchResults.total,
                batchResults: batchResults,
                report: this.generateReport(batchResults),
                thresholds: this.getThresholds()
            };

        } catch (error) {
            console.error('❌ 自定义阈值异常检测失败:', error);
            return {
                success: false,
                error: error.message,
                anomaliesFound: 0,
                checkedCount: 0
            };
        }
    }

    /**
     * 初始化方法，确保依赖正确设置
     * @param {Object} localDataManager - 本地数据管理器
     * @param {Object} componentBridge - 组件桥接器
     */
    async init(localDataManager = null, componentBridge = null) {
        try {
            this.localDataManager = localDataManager;
            this.componentBridge = componentBridge;
            console.log('✅ SimpleAnomalyDetector 初始化完成');
            return true;
        } catch (error) {
            console.error('❌ SimpleAnomalyDetector 初始化失败:', error);
            return false;
        }
    }
}

// 浏览器环境导出
if (typeof window !== 'undefined') {
    window.SimpleAnomalyDetector = SimpleAnomalyDetector;
}

// Node.js环境导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SimpleAnomalyDetector;
}