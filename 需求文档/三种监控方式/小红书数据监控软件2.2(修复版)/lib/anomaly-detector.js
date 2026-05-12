/**
 * 异常检测系统
 * 用于检测小红书商品数据的销量、价格等异常变化
 */
class AnomalyDetector {
    constructor(localDataManager) {
        this.dataManager = localDataManager;
        this.detectionRules = this.getDefaultDetectionRules();
        this.isRunning = false;
        this.lastDetectionTime = null;
        this.detectionInterval = null;
        
        // 异步加载保存的规则
        this.loadRulesFromStorage();
    }

    /**
     * 获取默认检测规则
     */
    getDefaultDetectionRules() {
        return {
            // 销量异常检测规则 (按文档要求: 日销量增长 > 50 件)
            salesSurge: {
                enabled: true,
                // 24小时销量增长超过50件为异常 (文档要求)
                threshold: 50, // 绝对值增长
                timeWindow: 24, // 24小时检测周期
                // 最小基础销量（避免从0增长的误报）
                minBaseSales: 5
            },
            
            // 营收异常检测规则 (按文档要求: 日营收增长 > 500 元)
            revenueSurge: {
                enabled: true,
                // 24小时营收增长超过500元为异常 (文档要求)
                threshold: 500, // 营收增长 = 销量变化 × 商品价格
                timeWindow: 24, // 24小时检测周期
                // 最小商品价格 (避免低价商品误报)
                minPrice: 1
            },
            
            // 价格异常检测规则 (额外增强功能)
            priceAnomaly: {
                enabled: true,
                // 价格变化超过50%为异常
                changeThreshold: 50, // 百分比
                // 价格绝对变化超过100元为风险
                absoluteThreshold: 100
            },
            
            // 数据缺失异常
            dataLossAnomaly: {
                enabled: true,
                // 连续多少天无数据更新算异常
                maxDaysWithoutUpdate: 3
            }
        };
    }

    /**
     * 运行全量异常检测
     * @param {Object} options 检测选项
     */
    async runFullDetection(options = {}) {
        console.log('🔍 开始全量异常检测...');
        const startTime = Date.now();
        
        try {
            this.isRunning = true;
            
            // 获取所有商品
            const products = await this.dataManager.getAllProducts();
            console.log(`📦 开始检测 ${products.length} 个商品的异常情况`);
            
            const detectionResults = {
                totalProducts: products.length,
                checkedProducts: 0,
                anomaliesFound: 0,
                criticalAnomalies: 0,
                warningAnomalies: 0,
                infoAnomalies: 0,
                errors: []
            };

            // 并发检测（限制并发数以免影响性能）
            const batchSize = 10;
            for (let i = 0; i < products.length; i += batchSize) {
                const batch = products.slice(i, i + batchSize);
                const batchPromises = batch.map(product => 
                    this.detectProductAnomalies(product).catch(error => {
                        console.warn(`⚠️ 商品 ${product.title} 检测失败:`, error);
                        detectionResults.errors.push({
                            productId: product.id,
                            error: error.message
                        });
                        return [];
                    })
                );

                const batchResults = await Promise.all(batchPromises);
                
                // 统计结果
                for (const anomalies of batchResults) {
                    detectionResults.checkedProducts++;
                    detectionResults.anomaliesFound += anomalies.length;
                    
                    for (const anomaly of anomalies) {
                        switch (anomaly.severity) {
                            case 'critical':
                                detectionResults.criticalAnomalies++;
                                break;
                            case 'warning':
                                detectionResults.warningAnomalies++;
                                break;
                            case 'info':
                                detectionResults.infoAnomalies++;
                                break;
                        }
                    }
                }

                // 进度反馈
                if (options.onProgress) {
                    options.onProgress({
                        current: Math.min(i + batchSize, products.length),
                        total: products.length,
                        percentage: Math.round((Math.min(i + batchSize, products.length) / products.length) * 100)
                    });
                }
            }

            const endTime = Date.now();
            const duration = endTime - startTime;

            console.log(`✅ 异常检测完成! 耗时: ${duration}ms`);
            console.log(`📊 检测统计:`, detectionResults);

            this.lastDetectionTime = new Date();
            
            return {
                success: true,
                duration,
                ...detectionResults
            };

        } catch (error) {
            console.error('❌ 异常检测失败:', error);
            return {
                success: false,
                error: error.message
            };
        } finally {
            this.isRunning = false;
        }
    }

    /**
     * 检测单个商品的异常
     * @param {Object} product 商品数据
     */
    async detectProductAnomalies(product) {
        const anomalies = [];
        
        try {
            // 获取商品最近的快照数据（用于对比）
            const snapshots = await this.getProductRecentSnapshots(product.id, 7); // 获取7天内的数据
            
            if (snapshots.length < 2) {
                // 数据不足，无法进行对比分析
                return anomalies;
            }

            // 按时间排序（最新的在前）
            snapshots.sort((a, b) => new Date(b.snapshot_date) - new Date(a.snapshot_date));
            
            const latestSnapshot = snapshots[0];
            const previousSnapshot = snapshots[1];

            // 1. 销量异常检测
            if (this.detectionRules.salesSurge.enabled) {
                const salesAnomaly = this.detectSalesAnomaly(product, latestSnapshot, previousSnapshot);
                if (salesAnomaly) {
                    anomalies.push(salesAnomaly);
                }
            }
            
            // 2. 营收异常检测
            if (this.detectionRules.revenueSurge.enabled) {
                const revenueAnomaly = this.detectRevenueSurge(product, latestSnapshot, previousSnapshot);
                if (revenueAnomaly) {
                    anomalies.push(revenueAnomaly);
                }
            }

            // 3. 价格异常检测
            if (this.detectionRules.priceAnomaly.enabled) {
                const priceAnomaly = this.detectPriceAnomaly(product, latestSnapshot, previousSnapshot);
                if (priceAnomaly) {
                    anomalies.push(priceAnomaly);
                }
            }

            // 4. 数据更新异常检测
            if (this.detectionRules.dataLossAnomaly.enabled) {
                const dataLossAnomaly = this.detectDataLossAnomaly(product, snapshots);
                if (dataLossAnomaly) {
                    anomalies.push(dataLossAnomaly);
                }
            }

            // 保存发现的异常
            for (const anomaly of anomalies) {
                await this.dataManager.saveAnomaly(anomaly);
            }

            return anomalies;

        } catch (error) {
            console.error(`❌ 检测商品 ${product.title} 异常时发生错误:`, error);
            throw error;
        }
    }

    /**
     * 检测销量异常 - 按文档要求：日销量增长 > 50 件
     */
    detectSalesAnomaly(product, latestSnapshot, previousSnapshot) {
        const rules = this.detectionRules.salesSurge;
        
        const currentSales = this.extractSalesValue(latestSnapshot);
        const previousSales = this.extractSalesValue(previousSnapshot);

        // 跳过无效数据
        if (currentSales === null || previousSales === null) {
            return null;
        }

        // 跳过基础销量过低的情况
        if (previousSales < rules.minBaseSales) {
            return null;
        }

        // 计算销量变化
        const salesChange = currentSales - previousSales;

        // 判断是否为异常 - 按文档要求：增长超过50件
        let isAnomaly = false;
        let severity = 'info';

        if (salesChange > rules.threshold) {
            isAnomaly = true;
            
            // 根据变化幅度确定严重程度
            if (salesChange > rules.threshold * 3) {
                severity = 'critical'; // 增长超过150件为严重
            } else if (salesChange > rules.threshold * 2) {
                severity = 'warning';  // 增长超过100件为警告
            } else {
                severity = 'info';     // 增长50-100件为信息
            }
        }

        if (!isAnomaly) {
            return null;
        }

        return {
            product_id: product.id,
            detected_at: new Date().toISOString(),
            type: 'sales_anomaly',
            severity: severity,
            description: `销量激增异常: +${salesChange}件 (${previousSales} → ${currentSales})`,
            data: {
                current_sales: currentSales,
                previous_sales: previousSales,
                change: salesChange,
                threshold: rules.threshold,
                snapshot_date: latestSnapshot.snapshot_date
            }
        };
    }
    
    /**
     * 检测营收异常 - 按文档要求：日营收增长 > 500 元
     */
    detectRevenueSurge(product, latestSnapshot, previousSnapshot) {
        const rules = this.detectionRules.revenueSurge;
        
        const currentSales = this.extractSalesValue(latestSnapshot);
        const previousSales = this.extractSalesValue(previousSnapshot);
        const currentPrice = this.extractPriceValue(latestSnapshot);

        // 跳过无效数据
        if (currentSales === null || previousSales === null || currentPrice === null) {
            return null;
        }

        // 跳过价格过低的商品
        if (currentPrice < rules.minPrice) {
            return null;
        }

        // 计算营收变化 = 销量变化 × 商品价格
        const salesChange = currentSales - previousSales;
        const revenueChange = salesChange * currentPrice;

        // 判断是否为异常 - 按文档要求：营收增长超过500元
        let isAnomaly = false;
        let severity = 'info';

        if (revenueChange > rules.threshold) {
            isAnomaly = true;
            
            // 根据变化幅度确定严重程度
            if (revenueChange > rules.threshold * 5) {
                severity = 'critical'; // 增长超过2500元为严重
            } else if (revenueChange > rules.threshold * 2) {
                severity = 'warning';  // 增长超过1000元为警告
            } else {
                severity = 'info';     // 增长500-1000元为信息
            }
        }

        if (!isAnomaly) {
            return null;
        }

        return {
            product_id: product.id,
            detected_at: new Date().toISOString(),
            type: 'revenue_anomaly',
            severity: severity,
            description: `营收激增异常: +¥${revenueChange.toFixed(2)} (销量+${salesChange}件 × ¥${currentPrice})`,
            data: {
                current_sales: currentSales,
                previous_sales: previousSales,
                sales_change: salesChange,
                price: currentPrice,
                revenue_change: revenueChange,
                threshold: rules.threshold,
                snapshot_date: latestSnapshot.snapshot_date
            }
        };
    }

    /**
     * 检测价格异常
     */
    detectPriceAnomaly(product, latestSnapshot, previousSnapshot) {
        const rules = this.detectionRules.priceAnomaly;
        
        const currentPrice = this.extractPriceValue(latestSnapshot);
        const previousPrice = this.extractPriceValue(previousSnapshot);

        // 跳过无效数据
        if (currentPrice === null || previousPrice === null || previousPrice === 0) {
            return null;
        }

        // 计算价格变化
        const priceChange = currentPrice - previousPrice;
        const priceChangeRate = (priceChange / previousPrice) * 100;

        // 判断是否为异常
        let isAnomaly = false;
        let severity = 'info';

        if (Math.abs(priceChangeRate) > rules.changeThreshold) {
            isAnomaly = true;
            
            // 根据变化幅度确定严重程度
            if (Math.abs(priceChange) > rules.absoluteThreshold) {
                severity = 'critical';
            } else if (Math.abs(priceChangeRate) > rules.changeThreshold * 2) {
                severity = 'warning';
            } else {
                severity = 'info';
            }
        }

        if (!isAnomaly) {
            return null;
        }

        return {
            product_id: product.id,
            detected_at: new Date().toISOString(),
            type: 'price_anomaly',
            severity: severity,
            description: `价格异常变化: ${priceChangeRate > 0 ? '+' : ''}${priceChangeRate.toFixed(1)}% (¥${previousPrice} → ¥${currentPrice})`,
            data: {
                current_price: currentPrice,
                previous_price: previousPrice,
                change: priceChange,
                change_rate: priceChangeRate,
                snapshot_date: latestSnapshot.snapshot_date
            }
        };
    }

    /**
     * 检测数据缺失异常
     */
    detectDataLossAnomaly(product, snapshots) {
        const rules = this.detectionRules.dataLossAnomaly;
        
        if (snapshots.length === 0) {
            return {
                product_id: product.id,
                detected_at: new Date().toISOString(),
                type: 'data_loss_anomaly',
                severity: 'warning',
                description: '商品无快照数据',
                data: {
                    last_update: product.updated_at || product.created_at,
                    days_without_update: null
                }
            };
        }

        // 检查最后更新时间
        const latestSnapshot = snapshots[0];
        const daysSinceUpdate = Math.floor(
            (Date.now() - new Date(latestSnapshot.snapshot_date).getTime()) / (24 * 60 * 60 * 1000)
        );

        if (daysSinceUpdate > rules.maxDaysWithoutUpdate) {
            return {
                product_id: product.id,
                detected_at: new Date().toISOString(),
                type: 'data_loss_anomaly',
                severity: daysSinceUpdate > 7 ? 'warning' : 'info',
                description: `数据更新滞后: ${daysSinceUpdate}天未更新`,
                data: {
                    last_update: latestSnapshot.snapshot_date,
                    days_without_update: daysSinceUpdate
                }
            };
        }

        return null;
    }

    /**
     * 获取商品最近的快照数据
     */
    async getProductRecentSnapshots(productId, days = 7) {
        try {
            // 计算时间范围
            const endDate = new Date();
            const startDate = new Date(endDate.getTime() - (days * 24 * 60 * 60 * 1000));

            return new Promise((resolve, reject) => {
                const transaction = this.dataManager.db.transaction(['snapshots'], 'readonly');
                const store = transaction.objectStore('snapshots');
                const index = store.index('product_id');
                const request = index.openCursor(productId);

                const snapshots = [];

                request.onsuccess = (event) => {
                    const cursor = event.target.result;
                    if (cursor) {
                        const snapshot = cursor.value;
                        const snapshotDate = new Date(snapshot.snapshot_date);
                        
                        // 过滤时间范围内的数据
                        if (snapshotDate >= startDate && snapshotDate <= endDate) {
                            snapshots.push(snapshot);
                        }
                        
                        cursor.continue();
                    } else {
                        console.log(`🔍 找到商品 ${productId} 的快照数据: ${snapshots.length} 条`);
                        if (snapshots.length > 0) {
                            console.log('快照数据:', snapshots.map(s => ({
                                id: s.id,
                                date: s.snapshot_date,
                                sales: s.sales_data,
                                price: s.price_data
                            })));
                        }
                        resolve(snapshots);
                    }
                };

                request.onerror = () => {
                    reject(new Error('获取商品快照数据失败'));
                };
            });

        } catch (error) {
            console.error('获取商品快照数据错误:', error);
            return [];
        }
    }

    /**
     * 从快照中提取销量数值
     */
    extractSalesValue(snapshot) {
        if (!snapshot || !snapshot.sales_data) {
            return null;
        }

        // 尝试多种数据格式
        if (typeof snapshot.sales_data === 'number') {
            return snapshot.sales_data;
        }

        if (snapshot.sales_data.current !== undefined) {
            return snapshot.sales_data.current;
        }

        if (snapshot.sales_data.sales !== undefined) {
            return snapshot.sales_data.sales;
        }

        // 如果是字符串，尝试解析数字
        if (typeof snapshot.sales_data === 'string') {
            const match = snapshot.sales_data.match(/(\d+)/);
            return match ? parseInt(match[1], 10) : null;
        }

        return null;
    }

    /**
     * 从快照中提取价格数值
     */
    extractPriceValue(snapshot) {
        if (!snapshot || !snapshot.price_data) {
            return null;
        }

        // 尝试多种数据格式
        if (typeof snapshot.price_data === 'number') {
            return snapshot.price_data;
        }

        if (snapshot.price_data.current !== undefined) {
            return snapshot.price_data.current;
        }

        if (snapshot.price_data.price !== undefined) {
            return snapshot.price_data.price;
        }

        // 如果是字符串，尝试解析数字
        if (typeof snapshot.price_data === 'string') {
            const match = snapshot.price_data.match(/(\d+(?:\.\d+)?)/);
            return match ? parseFloat(match[1]) : null;
        }

        return null;
    }

    /**
     * 启动定时异常检测
     * @param {number} intervalMinutes 检测间隔（分钟）
     */
    startScheduledDetection(intervalMinutes = 60) {
        if (this.detectionInterval) {
            this.stopScheduledDetection();
        }

        console.log(`⏰ 启动定时异常检测，间隔: ${intervalMinutes}分钟`);
        
        this.detectionInterval = setInterval(async () => {
            try {
                console.log('⏰ 执行定时异常检测...');
                const result = await this.runFullDetection();
                
                if (result.success && result.anomaliesFound > 0) {
                    console.log(`🚨 定时检测发现 ${result.anomaliesFound} 个异常`);
                    
                    // 这里可以添加通知逻辑
                    this.notifyAnomalies(result);
                }
                
            } catch (error) {
                console.error('❌ 定时异常检测失败:', error);
            }
        }, intervalMinutes * 60 * 1000);
    }

    /**
     * 停止定时异常检测
     */
    stopScheduledDetection() {
        if (this.detectionInterval) {
            clearInterval(this.detectionInterval);
            this.detectionInterval = null;
            console.log('⏹️ 定时异常检测已停止');
        }
    }

    /**
     * 异常通知（集成ComponentBridge）
     */
    notifyAnomalies(detectionResult) {
        console.log('📢 异常通知:', {
            总异常数: detectionResult.anomaliesFound,
            严重异常: detectionResult.criticalAnomalies,
            警告异常: detectionResult.warningAnomalies,
            信息异常: detectionResult.infoAnomalies
        });
        
        // 通过ComponentBridge发送异常检测完成通知
        if (typeof window !== 'undefined' && window.getComponentBridge) {
            const bridge = window.getComponentBridge();
            if (bridge) {
                bridge.sendMessage('data-manager', 'ANOMALY_DETECTION_COMPLETED', {
                    ...detectionResult,
                    timestamp: Date.now()
                });
            }
        }
        
        // 如果发现严重异常，发送单独的严重异常通知
        if (detectionResult.criticalAnomalies > 0) {
            if (typeof chrome !== 'undefined' && chrome.notifications) {
                chrome.notifications.create({
                    type: 'basic',
                    iconUrl: 'icons/icon48.png',
                    title: '🚨 发现严重异常',
                    message: `检测到 ${detectionResult.criticalAnomalies} 个严重异常，请及时处理！`
                });
            }
        }
    }
    
    /**
     * 发送单个异常通知
     */
    notifySingleAnomaly(anomaly) {
        console.log(`🚨 发现单个异常: ${anomaly.description}`);
        
        // 通过ComponentBridge发送单个异常通知
        if (typeof window !== 'undefined' && window.getComponentBridge) {
            const bridge = window.getComponentBridge();
            if (bridge) {
                bridge.sendMessage('data-manager', 'ANOMALY_DETECTED', anomaly);
            }
        }
        
        // 严重异常立即发送浏览器通知
        if (anomaly.severity === 'critical' && typeof chrome !== 'undefined' && chrome.notifications) {
            chrome.notifications.create({
                type: 'basic',
                iconUrl: 'icons/icon48.png',
                title: '🚨 严重异常警报',
                message: anomaly.description
            });
        }
    }

    /**
     * 获取异常统计
     */
    async getAnomalyStats(timeRange = 7) {
        try {
            const endDate = new Date();
            const startDate = new Date(endDate.getTime() - (timeRange * 24 * 60 * 60 * 1000));

            const anomalies = await this.dataManager.getAnomalies({
                startDate: startDate.toISOString(),
                endDate: endDate.toISOString()
            });

            const stats = {
                total: anomalies.length,
                critical: anomalies.filter(a => a.severity === 'critical').length,
                warning: anomalies.filter(a => a.severity === 'warning').length,
                info: anomalies.filter(a => a.severity === 'info').length,
                byType: {}
            };

            // 按类型统计
            anomalies.forEach(anomaly => {
                if (!stats.byType[anomaly.type]) {
                    stats.byType[anomaly.type] = 0;
                }
                stats.byType[anomaly.type]++;
            });

            return stats;

        } catch (error) {
            console.error('获取异常统计失败:', error);
            return {
                total: 0,
                critical: 0,
                warning: 0,
                info: 0,
                byType: {}
            };
        }
    }

    /**
     * 更新检测规则
     */
    updateDetectionRules(newRules) {
        this.detectionRules = {
            ...this.detectionRules,
            ...newRules
        };
        console.log('✅ 异常检测规则已更新:', newRules);
        
        // 保存规则到本地存储
        this.saveRulesToStorage();
    }
    
    /**
     * 保存规则到本地存储
     */
    async saveRulesToStorage() {
        try {
            if (typeof chrome !== 'undefined' && chrome.storage) {
                await chrome.storage.local.set({
                    'anomaly_detection_rules': this.detectionRules
                });
                console.log('✅ 异常检测规则已保存到本地存储');
            }
        } catch (error) {
            console.warn('⚠️ 保存异常检测规则失败:', error);
        }
    }
    
    /**
     * 从本地存储加载规则
     */
    async loadRulesFromStorage() {
        try {
            if (typeof chrome !== 'undefined' && chrome.storage) {
                const result = await chrome.storage.local.get('anomaly_detection_rules');
                if (result.anomaly_detection_rules) {
                    this.detectionRules = {
                        ...this.getDefaultDetectionRules(),
                        ...result.anomaly_detection_rules
                    };
                    console.log('✅ 从本地存储加载异常检测规则');
                }
            }
        } catch (error) {
            console.warn('⚠️ 加载异常检测规则失败，使用默认规则:', error);
        }
    }
    
    /**
     * 重置为默认规则
     */
    resetToDefaultRules() {
        this.detectionRules = this.getDefaultDetectionRules();
        this.saveRulesToStorage();
        console.log('✅ 异常检测规则已重置为默认值');
    }

    /**
     * 实时检测单个商品异常 - 供批量监控调用
     * @param {string} productId 商品ID
     * @param {Object} newData 新的商品数据 (可选)
     */
    async checkProductAnomaly(productId, newData = null) {
        try {
            console.log(`🔍 实时检测商品 ${productId} 的异常情况...`);
            
            // 获取商品信息
            const product = await this.dataManager.getProduct(productId);
            if (!product) {
                console.warn(`商品 ${productId} 不存在`);
                return null;
            }
            
            // 获取最近的快照数据
            const snapshots = await this.getProductRecentSnapshots(productId, 2); // 只需要最近2个快照
            
            if (snapshots.length < 2) {
                console.log(`商品 ${productId} 快照数据不足，无法进行异常检测`);
                return null;
            }
            
            // 按时间排序
            snapshots.sort((a, b) => new Date(b.snapshot_date) - new Date(a.snapshot_date));
            
            // 如果提供了新数据，创建临时快照
            let latestSnapshot = snapshots[0];
            if (newData) {
                latestSnapshot = {
                    product_id: productId,
                    snapshot_date: new Date().toISOString(),
                    sales_data: newData.sales || newData.currentSales,
                    price_data: newData.price || newData.currentPrice
                };
            }
            
            const previousSnapshot = snapshots[newData ? 0 : 1];
            
            // 执行各种异常检测
            const anomalies = [];
            
            // 销量异常检测
            if (this.detectionRules.salesSurge.enabled) {
                const salesAnomaly = this.detectSalesAnomaly(product, latestSnapshot, previousSnapshot);
                if (salesAnomaly) {
                    anomalies.push(salesAnomaly);
                    console.log(`🚨 发现销量异常: ${salesAnomaly.description}`);
                }
            }
            
            // 营收异常检测
            if (this.detectionRules.revenueSurge.enabled) {
                const revenueAnomaly = this.detectRevenueSurge(product, latestSnapshot, previousSnapshot);
                if (revenueAnomaly) {
                    anomalies.push(revenueAnomaly);
                    console.log(`🚨 发现营收异常: ${revenueAnomaly.description}`);
                }
            }
            
            // 价格异常检测
            if (this.detectionRules.priceAnomaly.enabled) {
                const priceAnomaly = this.detectPriceAnomaly(product, latestSnapshot, previousSnapshot);
                if (priceAnomaly) {
                    anomalies.push(priceAnomaly);
                    console.log(`🚨 发现价格异常: ${priceAnomaly.description}`);
                }
            }
            
            // 保存检测到的异常
            for (const anomaly of anomalies) {
                await this.dataManager.saveAnomaly(anomaly);
            }
            
            // 返回最严重的异常（如果有的话）
            if (anomalies.length > 0) {
                const severityOrder = { 'critical': 3, 'warning': 2, 'info': 1 };
                anomalies.sort((a, b) => severityOrder[b.severity] - severityOrder[a.severity]);
                return anomalies[0]; // 返回最严重的异常
            }
            
            return null;
            
        } catch (error) {
            console.error(`❌ 实时异常检测失败 (商品 ${productId}):`, error);
            throw error;
        }
    }
    
    /**
     * 获取检测状态
     */
    getDetectionStatus() {
        return {
            isRunning: this.isRunning,
            lastDetectionTime: this.lastDetectionTime,
            scheduledDetectionActive: this.detectionInterval !== null,
            detectionRules: this.detectionRules
        };
    }
}

// 在浏览器环境中暴露
if (typeof window !== 'undefined') {
    window.AnomalyDetector = AnomalyDetector;
}

// 在Node.js环境中导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AnomalyDetector;
}