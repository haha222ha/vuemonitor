/**
 * crawl_time 字段恢复脚本
 * 修复 ultrathink 错误删除的爬取时间字段
 */

class CrawlTimeFieldRestorer {
    constructor() {
        this.db = null;
        this.isInitialized = false;
        this.stats = {
            totalRecords: 0,
            restoredRecords: 0,
            errors: [],
            startTime: null,
            endTime: null
        };
    }

    /**
     * 初始化恢复器
     */
    async init() {
        try {
            console.log('🔧 初始化 crawl_time 字段恢复器...');

            if (window.dataManagerApp && window.dataManagerApp.sharedDataService && window.dataManagerApp.sharedDataService.localDataManager) {
                this.localDataManager = window.dataManagerApp.sharedDataService.localDataManager;
                console.log('✅ 使用现有数据管理器');
            } else {
                // 直接连接 IndexedDB
                this.db = await new Promise((resolve, reject) => {
                    const request = indexedDB.open('xiaohongshu_monitor', 2);
                    request.onerror = () => reject(request.error);
                    request.onsuccess = () => resolve(request.result);
                });
                console.log('✅ 直接连接 IndexedDB');
            }

            this.isInitialized = true;
            console.log('✅ crawl_time 字段恢复器初始化完成');

        } catch (error) {
            console.error('❌ 初始化失败:', error);
            throw error;
        }
    }

    /**
     * 执行字段恢复
     */
    async executeRestore() {
        if (!this.isInitialized) {
            await this.init();
        }

        this.stats.startTime = new Date();
        console.log('🚀 开始恢复 crawl_time 字段...');

        try {
            // 1. 分析当前状况
            await this.analyzeCurrentState();

            // 2. 执行字段恢复
            await this.restoreCrawlTimeFields();

            // 3. 验证恢复结果
            await this.validateRestore();

            // 4. 生成报告
            this.generateRestoreReport();

            this.stats.endTime = new Date();
            console.log('🎉 crawl_time 字段恢复完成！');

        } catch (error) {
            console.error('❌ crawl_time 字段恢复失败:', error);
            this.stats.errors.push({
                stage: 'restore',
                error: error.message,
                timestamp: new Date()
            });
            throw error;
        }
    }

    /**
     * 分析当前状况
     */
    async analyzeCurrentState() {
        console.log('🔍 分析当前数据状况...');

        try {
            let products = [];

            if (this.localDataManager) {
                // 使用数据管理器获取数据
                const result = await this.localDataManager.getProducts(null, {}, { page: 1, limit: 10000 });
                products = result.products || [];
            } else {
                // 直接从 IndexedDB 获取数据
                const transaction = this.db.transaction(['products'], 'readonly');
                const store = transaction.objectStore('products');

                products = await new Promise((resolve, reject) => {
                    const request = store.getAll();
                    request.onsuccess = () => resolve(request.result);
                    request.onerror = () => reject(request.error);
                });
            }

            this.stats.totalRecords = products.length;
            console.log(`📊 找到 ${products.length} 条产品记录`);

            // 分析字段状况
            const analysis = this.analyzeFieldState(products);
            console.log('📋 字段状况分析:', analysis);

            return analysis;

        } catch (error) {
            console.error('❌ 数据分析失败:', error);
            throw error;
        }
    }

    /**
     * 分析字段状态
     */
    analyzeFieldState(products) {
        const analysis = {
            hasExtractedAt: 0,
            hasCrawlTime: 0,
            needsRestore: 0,
            hasTimeSeriesData: 0
        };

        for (const product of products) {
            if (product.extracted_at) {
                analysis.hasExtractedAt++;
            }

            if (product.crawl_time) {
                analysis.hasCrawlTime++;
            } else if (product.extracted_at) {
                analysis.needsRestore++;
            }

            // 检查是否有时间序列数据
            const hasTimeSeries = Object.keys(product).some(key =>
                key.startsWith('爬取时间（') && key.endsWith('）')
            );
            if (hasTimeSeries) {
                analysis.hasTimeSeriesData++;
            }
        }

        return analysis;
    }

    /**
     * 恢复 crawl_time 字段
     */
    async restoreCrawlTimeFields() {
        console.log('🔄 开始恢复 crawl_time 字段...');

        try {
            let products = [];

            if (this.localDataManager) {
                // 使用数据管理器获取数据
                const result = await this.localDataManager.getProducts(null, {}, { page: 1, limit: 10000 });
                products = result.products || [];
            } else {
                // 直接从 IndexedDB 获取数据
                const transaction = this.db.transaction(['products'], 'readwrite');
                const store = transaction.objectStore('products');

                products = await new Promise((resolve, reject) => {
                    const request = store.getAll();
                    request.onsuccess = () => resolve(request.result);
                    request.onerror = () => reject(request.error);
                });
            }

            let processedCount = 0;

            for (const product of products) {
                if (!product.crawl_time && product.extracted_at) {
                    // 恢复 crawl_time 字段
                    const updatedProduct = {
                        ...product,
                        crawl_time: product.extracted_at
                    };

                    if (this.localDataManager) {
                        // 使用数据管理器更新
                        await this.localDataManager.updateProduct(updatedProduct);
                    } else {
                        // 直接更新 IndexedDB
                        const transaction = this.db.transaction(['products'], 'readwrite');
                        const store = transaction.objectStore('products');

                        await new Promise((resolve, reject) => {
                            const updateRequest = store.put(updatedProduct);
                            updateRequest.onsuccess = () => resolve();
                            updateRequest.onerror = () => reject(updateRequest.error);
                        });
                    }

                    processedCount++;
                    this.stats.restoredRecords++;

                    if (processedCount % 100 === 0) {
                        console.log(`📈 已恢复 ${processedCount} 条记录...`);
                    }
                }
            }

            console.log(`✅ crawl_time 字段恢复完成，处理了 ${processedCount} 条记录`);

        } catch (error) {
            console.error('❌ crawl_time 字段恢复失败:', error);
            throw error;
        }
    }

    /**
     * 验证恢复结果
     */
    async validateRestore() {
        console.log('🔍 验证恢复结果...');

        try {
            const analysis = await this.analyzeCurrentState();

            console.log('📊 恢复后状况:', analysis);

            const successRate = (analysis.hasCrawlTime / this.stats.totalRecords * 100).toFixed(1);
            console.log(`✅ crawl_time 字段覆盖率: ${successRate}%`);

            return analysis;

        } catch (error) {
            console.error('❌ 恢复验证失败:', error);
            throw error;
        }
    }

    /**
     * 生成恢复报告
     */
    generateRestoreReport() {
        const duration = this.stats.endTime - this.stats.startTime;

        const report = {
            '恢复开始时间': this.stats.startTime?.toLocaleString(),
            '恢复结束时间': this.stats.endTime?.toLocaleString(),
            '总耗时(秒)': Math.round(duration / 1000),
            '总记录数': this.stats.totalRecords,
            '恢复记录数': this.stats.restoredRecords,
            '错误数量': this.stats.errors.length,
            '恢复成功率': `${Math.round((this.stats.restoredRecords / this.stats.totalRecords) * 100)}%`
        };

        console.log('\n📋 crawl_time 字段恢复报告:');
        console.table(report);

        return report;
    }

    /**
     * 获取恢复统计
     */
    getStats() {
        return this.stats;
    }
}

// 快速执行函数
async function restoreCrawlTimeField() {
    console.log('🚀 开始恢复 crawl_time 字段...');

    const restorer = new CrawlTimeFieldRestorer();

    try {
        await restorer.executeRestore();
        console.log('🎉 crawl_time 字段恢复执行成功！');
        return restorer.getStats();

    } catch (error) {
        console.error('❌ crawl_time 字段恢复执行失败:', error);
        throw error;
    }
}

// 暴露给全局使用
if (typeof window !== 'undefined') {
    window.CrawlTimeFieldRestorer = CrawlTimeFieldRestorer;
    window.restoreCrawlTimeField = restoreCrawlTimeField;
}

// Node.js环境支持
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { CrawlTimeFieldRestorer, restoreCrawlTimeField };
}