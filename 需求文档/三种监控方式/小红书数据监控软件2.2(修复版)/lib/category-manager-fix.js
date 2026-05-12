/**
 * CategoryManager兼容性修复
 * 解决data-manager.js中CategoryManager初始化问题
 */

// 等待CategoryManager类加载完成
function waitForCategoryManager() {
    return new Promise((resolve) => {
        if (typeof window.CategoryManager !== 'undefined') {
            resolve();
            return;
        }
        
        let attempts = 0;
        const maxAttempts = 50;
        const checkInterval = setInterval(() => {
            attempts++;
            if (typeof window.CategoryManager !== 'undefined') {
                clearInterval(checkInterval);
                resolve();
            } else if (attempts >= maxAttempts) {
                clearInterval(checkInterval);
                console.error('❌ CategoryManager加载超时');
                resolve();
            }
        }, 100);
    });
}

// 异步初始化修复
(async () => {
    await waitForCategoryManager();
    
    // 检查是否已经存在CategoryManager类
    if (typeof window.CategoryManager !== 'undefined') {
        console.log('🔧 检测到CategoryManager，进行兼容性修复...');
    
    // 保存原始的CategoryManager
    const OriginalCategoryManager = window.CategoryManager;
    
    // 创建兼容版本
    class CompatibleCategoryManager extends OriginalCategoryManager {
        constructor(localDataManager = null) {
            if (localDataManager) {
                // 如果传入了localDataManager，使用简化版逻辑
                super(localDataManager);
                this.isSimpleMode = true;
                this.localDataManager = localDataManager;
            } else {
                // 否则使用完整版逻辑
                super();
                this.isSimpleMode = false;
            }
        }
        
        async init() {
            if (this.isSimpleMode) {
                // 简化模式：不需要init，直接标记为已初始化
                this.isInitialized = true;
                this.dataManager = this.localDataManager;
                console.log('✅ CategoryManager (简化模式) 初始化完成');
                return;
            } else {
                // 完整模式：执行原来的init逻辑
                return await super.init();
            }
        }
        
        // 确保所有方法都能正常工作
        async getAllCategories() {
            if (this.isSimpleMode) {
                return await this.getCategories();
            } else {
                return await super.getAllCategories ? super.getAllCategories() : await this.getCategories();
            }
        }
        
        async getCategoryStats(categoryId) {
            if (this.isSimpleMode) {
                // 简化的统计逻辑
                try {
                    const category = await this.getCategoryById(categoryId);
                    if (!category) {
                        throw new Error('分类不存在');
                    }

                    const productCount = await this.dataManager.getProductCountByCategory(categoryId);
                    const products = await this.dataManager.getProducts(categoryId, {}, { page: 1, limit: 1000 });
                    
                    // 计算统计信息
                    const totalSales = products.products.reduce((sum, p) => sum + (p.product_sales || 0), 0);
                    const totalPrice = products.products.reduce((sum, p) => sum + (p.product_price || 0), 0);
                    const avgSales = productCount > 0 ? Math.floor(totalSales / productCount) : 0;
                    const avgPrice = productCount > 0 ? totalPrice / productCount : 0;

                    return {
                        category: category,
                        productCount: productCount,
                        totalProducts: productCount,
                        totalSales: totalSales,
                        averageSales: avgSales,
                        avgPrice: avgPrice,
                        maxSales: products.products.length > 0 
                            ? Math.max(...products.products.map(p => p.product_sales || 0))
                            : 0,
                        lastUpdate: products.products.length > 0 
                            ? new Date(Math.max(...products.products.map(p => new Date(p.extracted_at))))
                            : null
                    };
                } catch (error) {
                    console.error('❌ 获取分类统计失败:', error);
                    throw error;
                }
            } else {
                return await super.getCategoryStats(categoryId);
            }
        }
    }
    
    // 替换全局的CategoryManager
    window.CategoryManager = CompatibleCategoryManager;
    
        console.log('✅ CategoryManager兼容性修复完成');
    } else {
        console.log('⚠️ 未找到CategoryManager，跳过兼容性修复');
    }
})();

// 检查AnomalyDetector是否存在，如果不存在则创建一个空的
if (typeof window.AnomalyDetector === 'undefined') {
    class AnomalyDetector {
        constructor(localDataManager) {
            this.localDataManager = localDataManager;
        }
        
        async detectAnomalies() {
            console.log('异常检测功能尚未实现');
            return [];
        }
    }
    
    window.AnomalyDetector = AnomalyDetector;
    console.log('✅ AnomalyDetector占位类已创建');
}