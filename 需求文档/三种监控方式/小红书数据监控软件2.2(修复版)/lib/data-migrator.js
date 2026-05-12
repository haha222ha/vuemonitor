/**
 * 流量蜂小红书数据监控助手 - 数据迁移工具
 * Data Migration Tool for Xiaohongshu Monitor Extension
 * 
 * 负责将现有Chrome Storage数据迁移到IndexedDB
 * 确保数据完整性和无缝过渡
 */

class DataMigrator {
    constructor(localDataManager) {
        this.dataManager = localDataManager;
        this.migrationStatus = {
            isRunning: false,
            progress: 0,
            totalItems: 0,
            completedItems: 0,
            errors: []
        };
    }

    /**
     * 执行完整数据迁移
     */
    async runMigration() {
        console.log('🔄 开始数据迁移...');
        
        try {
            this.migrationStatus.isRunning = true;
            this.migrationStatus.progress = 0;
            this.migrationStatus.errors = [];

            // 1. 检查现有Chrome Storage数据
            const storageData = await this.readChromeStorage();
            console.log('📊 检测到的数据:', storageData);

            if (!storageData || Object.keys(storageData).length === 0) {
                console.log('ℹ️ 未发现需要迁移的数据');
                return { success: true, message: '无数据需要迁移' };
            }

            // 2. 分析并迁移历史记录
            if (storageData.history && Array.isArray(storageData.history)) {
                await this.migrateHistoryData(storageData.history);
            }

            // 3. 迁移设置数据
            if (storageData.settings) {
                await this.migrateSettings(storageData.settings);
            }

            // 4. 创建备份标记
            await this.createMigrationBackup(storageData);

            console.log('✅ 数据迁移完成');
            this.migrationStatus.isRunning = false;
            this.migrationStatus.progress = 100;

            return {
                success: true,
                message: '数据迁移成功',
                statistics: {
                    totalMigrated: this.migrationStatus.completedItems,
                    errors: this.migrationStatus.errors.length
                }
            };

        } catch (error) {
            console.error('❌ 数据迁移失败:', error);
            this.migrationStatus.isRunning = false;
            
            return {
                success: false,
                message: '数据迁移失败: ' + error.message,
                error: error
            };
        }
    }

    /**
     * 读取Chrome Storage中的现有数据
     */
    async readChromeStorage() {
        return new Promise((resolve) => {
            try {
                // 读取local storage
                chrome.storage.local.get(null, (localData) => {
                    if (chrome.runtime.lastError) {
                        console.warn('读取Local Storage失败:', chrome.runtime.lastError);
                        localData = {};
                    }

                    // 读取sync storage
                    chrome.storage.sync.get(null, (syncData) => {
                        if (chrome.runtime.lastError) {
                            console.warn('读取Sync Storage失败:', chrome.runtime.lastError);
                            syncData = {};
                        }

                        resolve({
                            local: localData || {},
                            sync: syncData || {},
                            // 合并两个存储的历史数据
                            history: localData.history || syncData.history || [],
                            settings: syncData.settings || localData.settings || {}
                        });
                    });
                });
            } catch (error) {
                console.error('Chrome Storage API调用失败:', error);
                resolve({});
            }
        });
    }

    /**
     * 迁移历史记录数据
     */
    async migrateHistoryData(historyArray) {
        console.log(`🔄 开始迁移 ${historyArray.length} 条历史记录...`);
        
        this.migrationStatus.totalItems = historyArray.length;
        let successCount = 0;
        
        for (let i = 0; i < historyArray.length; i++) {
            try {
                const historyItem = historyArray[i];
                const productData = this.transformHistoryItem(historyItem);
                
                if (productData) {
                    // 保存到IndexedDB，默认使用"未分类"分类
                    await this.dataManager.saveProduct(productData, 1);
                    successCount++;
                    this.migrationStatus.completedItems++;
                }

                // 更新进度
                this.migrationStatus.progress = Math.floor((i + 1) / historyArray.length * 80); // 80%用于历史数据迁移
                
                if (i % 10 === 0) {
                    console.log(`迁移进度: ${i + 1}/${historyArray.length} (${successCount} 成功)`);
                }

            } catch (error) {
                console.error(`历史记录 ${i + 1} 迁移失败:`, error);
                this.migrationStatus.errors.push({
                    type: 'history',
                    index: i,
                    item: historyArray[i],
                    error: error.message
                });
            }
        }
        
        console.log(`✅ 历史记录迁移完成: ${successCount}/${historyArray.length} 成功`);
    }

    /**
     * 转换历史记录项目格式
     */
    transformHistoryItem(historyItem) {
        try {
            // 处理不同的历史记录格式
            if (typeof historyItem === 'string') {
                // 如果是字符串，尝试解析JSON
                historyItem = JSON.parse(historyItem);
            }

            // 映射字段名称
            const productData = {
                productId: historyItem.productId || historyItem.商品ID || this.extractProductIdFromUrl(historyItem.url || historyItem.商品链接),
                productName: historyItem.productName || historyItem.商品名称 || '',
                productUrl: historyItem.url || historyItem.商品链接 || '',
                productPrice: historyItem.productPrice || historyItem.商品价格 || 0,
                productSales: historyItem.productSales || historyItem.商品销量 || 0,
                storeSales: historyItem.storeSales || historyItem.店铺销量 || 0,
                storeName: historyItem.storeName || historyItem.店铺名称 || '',
                goodReviews: historyItem.goodReviews || historyItem.好评人数 || '',
                cartCount: historyItem.cartCount || historyItem.加购件数 || '',
                recentSales: historyItem.recentSales || historyItem.近3个月销量 || '',
                storeFollowers: historyItem.storeFollowers || historyItem.店铺粉丝数 || '',
                notes: historyItem.notes || historyItem.备注 || '',
                // 保留原始时间戳
                extractedAt: historyItem.timestamp ? new Date(historyItem.timestamp) : new Date()
            };

            // 验证必要字段
            if (!productData.productId && !productData.productUrl) {
                console.warn('跳过无效记录: 缺少商品ID和URL');
                return null;
            }

            return productData;

        } catch (error) {
            console.error('历史记录格式转换失败:', error, historyItem);
            return null;
        }
    }

    /**
     * 从URL中提取商品ID
     */
    extractProductIdFromUrl(url) {
        if (!url) return null;
        
        try {
            // 小红书商品URL通常包含商品ID
            const match = url.match(/\/item\/([a-zA-Z0-9]+)/);
            return match ? match[1] : null;
        } catch (error) {
            return null;
        }
    }

    /**
     * 迁移设置数据
     */
    async migrateSettings(settings) {
        console.log('🔄 迁移设置数据...');
        
        try {
            // 过滤出需要保留的设置（排除Feishu相关设置）
            const relevantSettings = {};
            
            if (settings.autoExtract !== undefined) {
                relevantSettings.autoExtract = settings.autoExtract;
            }
            
            if (settings.soundNotification !== undefined) {
                relevantSettings.soundNotification = settings.soundNotification;
            }
            
            if (settings.theme !== undefined) {
                relevantSettings.theme = settings.theme;
            }

            // 添加迁移标记
            relevantSettings.migrationCompleted = true;
            relevantSettings.migrationDate = new Date().toISOString();
            relevantSettings.version = '2.0.0';

            // 保存到新的设置存储
            await chrome.storage.sync.set({ settings: relevantSettings });
            console.log('✅ 设置迁移完成');
            
        } catch (error) {
            console.error('❌ 设置迁移失败:', error);
            this.migrationStatus.errors.push({
                type: 'settings',
                error: error.message
            });
        }
    }

    /**
     * 创建迁移备份
     */
    async createMigrationBackup(originalData) {
        try {
            const backupData = {
                backupDate: new Date().toISOString(),
                originalData: originalData,
                migrationVersion: '2.0.0'
            };

            await chrome.storage.local.set({ 
                migrationBackup: backupData 
            });

            console.log('✅ 迁移备份创建完成');
        } catch (error) {
            console.warn('⚠️ 备份创建失败:', error);
        }
    }

    /**
     * 验证迁移完整性
     */
    async validateMigration() {
        console.log('🔍 验证迁移完整性...');
        
        try {
            // 检查IndexedDB中的数据
            const statistics = await this.dataManager.getStatistics();
            const categories = await this.dataManager.getCategories();
            
            console.log('📊 迁移后统计:', {
                totalProducts: statistics.totalProducts,
                totalCategories: statistics.totalCategories,
                defaultCategoryExists: categories.some(c => c.id === 1)
            });

            // 验证核心功能
            const testProduct = {
                productId: 'test_' + Date.now(),
                productName: '测试商品',
                productSales: 100,
                productUrl: 'https://test.com'
            };

            const saved = await this.dataManager.saveProduct(testProduct, 1);
            if (saved && saved.id) {
                console.log('✅ 核心功能验证通过');
                
                // 清理测试数据
                // 这里可以添加删除测试商品的逻辑
                
                return { valid: true, message: '迁移验证成功' };
            } else {
                throw new Error('保存测试失败');
            }

        } catch (error) {
            console.error('❌ 迁移验证失败:', error);
            return { valid: false, message: '迁移验证失败: ' + error.message };
        }
    }

    /**
     * 获取迁移状态
     */
    getMigrationStatus() {
        return { ...this.migrationStatus };
    }

    /**
     * 回滚迁移（紧急情况下使用）
     */
    async rollbackMigration() {
        console.log('🔄 开始回滚迁移...');
        
        try {
            // 读取备份数据
            const backupResult = await new Promise(resolve => {
                chrome.storage.local.get(['migrationBackup'], resolve);
            });

            if (!backupResult.migrationBackup) {
                throw new Error('未找到迁移备份数据');
            }

            const backup = backupResult.migrationBackup;
            
            // 恢复到Chrome Storage
            await chrome.storage.local.set(backup.originalData.local || {});
            await chrome.storage.sync.set(backup.originalData.sync || {});

            console.log('✅ 迁移回滚完成');
            return { success: true, message: '迁移回滚成功' };

        } catch (error) {
            console.error('❌ 迁移回滚失败:', error);
            return { success: false, message: '迁移回滚失败: ' + error.message };
        }
    }

    /**
     * 检查是否需要迁移
     */
    async checkMigrationNeeded() {
        try {
            // 检查是否已经迁移
            const settings = await new Promise(resolve => {
                chrome.storage.sync.get(['settings'], resolve);
            });

            if (settings.settings && settings.settings.migrationCompleted) {
                return { needed: false, reason: '已完成迁移' };
            }

            // 检查是否有历史数据需要迁移
            const storageData = await this.readChromeStorage();
            const hasHistoryData = storageData.history && storageData.history.length > 0;
            
            return {
                needed: hasHistoryData,
                reason: hasHistoryData ? `发现 ${storageData.history.length} 条历史记录需要迁移` : '无数据需要迁移',
                dataCount: hasHistoryData ? storageData.history.length : 0
            };

        } catch (error) {
            console.error('检查迁移需求失败:', error);
            return { needed: false, reason: '检查失败: ' + error.message };
        }
    }
}

// 导出供其他模块使用
window.DataMigrator = DataMigrator;