/**
 * 状态同步管理器
 * 负责管理数据管理器中所有状态的同步更新
 * 
 * @version 2.0
 * @author AI Assistant
 */

class StateSyncManager {
    constructor(dataManager) {
        this.dataManager = dataManager;
        this.eventListeners = new Map();
        this.syncInProgress = false;
        this.pendingSyncs = new Set();
        
        console.log('📡 状态同步管理器已初始化');
    }
    
    /**
     * 注册事件监听器
     */
    on(event, listener) {
        if (!this.eventListeners.has(event)) {
            this.eventListeners.set(event, []);
        }
        this.eventListeners.get(event).push(listener);
    }
    
    /**
     * 移除事件监听器
     */
    off(event, listener) {
        if (this.eventListeners.has(event)) {
            const listeners = this.eventListeners.get(event);
            const index = listeners.indexOf(listener);
            if (index > -1) {
                listeners.splice(index, 1);
            }
        }
    }
    
    /**
     * 触发事件
     */
    emit(event, data) {
        if (this.eventListeners.has(event)) {
            this.eventListeners.get(event).forEach(listener => {
                try {
                    listener(data);
                } catch (error) {
                    console.error(`状态同步事件监听器执行失败 [${event}]:`, error);
                }
            });
        }
    }
    
    /**
     * 统一的分类状态同步
     * @param {string} action - 操作类型: 'create', 'update', 'delete', 'bulk_update'
     * @param {Object} data - 相关数据
     */
    async syncCategoryState(action, data = {}) {
        if (this.syncInProgress) {
            this.pendingSyncs.add({ type: 'category', action, data });
            return;
        }
        
        this.syncInProgress = true;
        
        try {
            console.log(`🔄 开始同步分类状态 [${action}]:`, data);
            
            // 触发同步前事件
            this.emit('category_sync_start', { action, data });
            
            // 执行核心同步逻辑
            await this.performCategorySync(action, data);
            
            // 触发同步完成事件
            this.emit('category_sync_complete', { action, data });
            
            console.log(`✅ 分类状态同步完成 [${action}]`);
            
        } catch (error) {
            console.error(`❌ 分类状态同步失败 [${action}]:`, error);
            this.emit('category_sync_error', { action, data, error });
            throw error;
        } finally {
            this.syncInProgress = false;
            
            // 处理待处理的同步请求
            if (this.pendingSyncs.size > 0) {
                const pending = Array.from(this.pendingSyncs);
                this.pendingSyncs.clear();
                
                // 异步处理待处理的同步
                setTimeout(() => {
                    pending.forEach(sync => {
                        if (sync.type === 'category') {
                            this.syncCategoryState(sync.action, sync.data);
                        } else if (sync.type === 'product') {
                            this.syncProductState(sync.action, sync.data);
                        }
                    });
                }, 100);
            }
        }
    }
    
    /**
     * 执行分类同步的核心逻辑
     */
    async performCategorySync(action, data) {
        // 1. 刷新分类数据缓存
        await this.refreshCategoryCache();
        
        // 2. 更新侧边栏分类树
        await this.updateCategoryTree();
        
        // 3. 更新主内容区分类卡片
        await this.updateCategoryCards();
        
        // 4. 更新统计信息
        await this.updateStatistics();
        
        // 5. 根据不同操作类型执行特定逻辑
        switch (action) {
            case 'create':
                this.handleCategoryCreate(data);
                break;
            case 'update':
                this.handleCategoryUpdate(data);
                break;
            case 'delete':
                this.handleCategoryDelete(data);
                break;
            case 'bulk_update':
                this.handleCategoryBulkUpdate(data);
                break;
        }
    }
    
    /**
     * 统一的商品状态同步
     * @param {string} action - 操作类型: 'create', 'update', 'delete', 'batch_import'
     * @param {Object} data - 相关数据
     */
    async syncProductState(action, data = {}) {
        if (this.syncInProgress) {
            this.pendingSyncs.add({ type: 'product', action, data });
            return;
        }
        
        this.syncInProgress = true;
        
        try {
            console.log(`🔄 开始同步商品状态 [${action}]:`, data);
            
            // 触发同步前事件
            this.emit('product_sync_start', { action, data });
            
            // 执行核心同步逻辑
            await this.performProductSync(action, data);
            
            // 触发同步完成事件
            this.emit('product_sync_complete', { action, data });
            
            console.log(`✅ 商品状态同步完成 [${action}]`);
            
        } catch (error) {
            console.error(`❌ 商品状态同步失败 [${action}]:`, error);
            this.emit('product_sync_error', { action, data, error });
            throw error;
        } finally {
            this.syncInProgress = false;
        }
    }
    
    /**
     * 执行商品同步的核心逻辑
     */
    async performProductSync(action, data) {
        console.log(`🔄 执行商品同步核心逻辑 [${action}]:`, data);
        
        // 1. 刷新受影响分类的商品计数
        if (data.categoryIds) {
            console.log(`📊 刷新受影响的分类数量:`, data.categoryIds);
            for (const categoryId of data.categoryIds) {
                await this.refreshCategoryProductCount(categoryId);
            }
        }
        
        // 2. 延迟更新UI组件，确保数据更新完成
        setTimeout(async () => {
            console.log('🔄 开始更新UI组件...');
            
            // 更新侧边栏分类树（商品数量）
            await this.updateCategoryTree();
            
            // 更新主内容区分类卡片（商品数量）
            await this.updateCategoryCards();
            
            // 更新统计信息
            await this.updateStatistics();
            
            // 如果当前视图显示商品列表，刷新商品列表
            if (this.dataManager.currentView === 'products') {
                await this.refreshProductList();
            }
            
            console.log('✅ UI组件更新完成');
        }, 200); // 延迟200ms确保数据同步完成
        
        // 6. 根据不同操作类型执行特定逻辑
        switch (action) {
            case 'delete':
                this.handleProductDelete(data);
                break;
            case 'batch_import':
                this.handleProductBatchImport(data);
                break;
            case 'monitor_complete':
                this.handleMonitorComplete(data);
                break;
        }
    }
    
    /**
     * 刷新分类数据缓存
     */
    async refreshCategoryCache() {
        if (this.dataManager.categoriesCache) {
            this.dataManager.categoriesCache.clear();
            const categories = await this.dataManager.categoryManager.getAllCategories();
            categories.forEach(category => {
                this.dataManager.categoriesCache.set(category.id, category);
            });
        }
    }
    
    /**
     * 更新侧边栏分类树
     */
    async updateCategoryTree() {
        if (typeof this.dataManager.loadCategoryTree === 'function') {
            await this.dataManager.loadCategoryTree();
        }
    }
    
    /**
     * 更新主内容区分类卡片
     */
    async updateCategoryCards() {
        if (typeof this.dataManager.loadCategoriesData === 'function') {
            await this.dataManager.loadCategoriesData();
        }
    }
    
    /**
     * 更新统计信息
     */
    async updateStatistics() {
        if (typeof this.dataManager.updateStatistics === 'function') {
            await this.dataManager.updateStatistics();
        }
    }
    
    /**
     * 刷新指定分类的商品数量
     */
    async refreshCategoryProductCount(categoryId) {
        try {
            console.log(`🔄 刷新分类 ${categoryId} 的商品数量...`);
            const count = await this.dataManager.localDataManager.getProductCountByCategory(categoryId);
            console.log(`📊 分类 ${categoryId} 当前商品数量: ${count}`);
            
            // 更新缓存中的分类商品数量
            if (this.dataManager.categoriesCache && this.dataManager.categoriesCache.has(categoryId)) {
                const category = this.dataManager.categoriesCache.get(categoryId);
                const oldCount = category.product_count;
                category.product_count = count;
                this.dataManager.categoriesCache.set(categoryId, category);
                console.log(`💾 缓存更新: 分类 ${categoryId} 商品数量 ${oldCount} → ${count}`);
            } else {
                console.warn(`⚠️ 分类 ${categoryId} 不在缓存中，跳过缓存更新`);
            }
            
            // 确保DOM更新在合适的时机执行
            setTimeout(() => {
                this.updateCategoryCountInDOM(categoryId, count);
            }, 100); // 延迟100ms确保DOM已完全渲染
            
        } catch (error) {
            console.error(`❌ 刷新分类商品数量失败 [${categoryId}]:`, error);
        }
    }
    
    /**
     * 更新DOM中的分类商品数量显示
     */
    updateCategoryCountInDOM(categoryId, count) {
        console.log(`🔄 更新分类 ${categoryId} 的商品数量显示: ${count}`);
        
        // 更新侧边栏分类数量
        const sidebarCategory = document.querySelector(`.category-item[data-category-id="${categoryId}"] .category-count`);
        if (sidebarCategory) {
            sidebarCategory.textContent = count;
            console.log(`✅ 侧边栏分类 ${categoryId} 数量已更新: ${count}`);
        } else {
            console.warn(`⚠️ 未找到侧边栏分类 ${categoryId} 的数量元素`);
        }
        
        // 更新主内容区分类卡片数量 - 精确选择商品数量元素
        const categoryCard = document.querySelector(`.category-card[data-category-id="${categoryId}"]`);
        if (categoryCard) {
            // 查找"商品数量"对应的统计值元素
            const statLabels = categoryCard.querySelectorAll('.category-stat-label');
            for (let label of statLabels) {
                if (label.textContent.trim() === '商品数量') {
                    const valueElement = label.nextElementSibling;
                    if (valueElement && valueElement.classList.contains('category-stat-value')) {
                        valueElement.textContent = count;
                        console.log(`✅ 分类卡片 ${categoryId} 商品数量已更新: ${count}`);
                        break;
                    }
                }
            }
        } else {
            console.warn(`⚠️ 未找到分类卡片 ${categoryId}`);
        }
    }
    
    /**
     * 刷新商品列表
     */
    async refreshProductList() {
        if (typeof this.dataManager.loadProductsData === 'function') {
            await this.dataManager.loadProductsData();
        }
    }
    
    /**
     * 处理分类创建
     */
    handleCategoryCreate(data) {
        console.log('📁 处理分类创建:', data);
        this.dataManager.showToast('success', '同步完成', '新分类已添加到侧边栏');
    }
    
    /**
     * 处理分类更新
     */
    handleCategoryUpdate(data) {
        console.log('📝 处理分类更新:', data);
        this.dataManager.showToast('success', '同步完成', '分类信息已更新');
    }
    
    /**
     * 处理分类删除
     */
    handleCategoryDelete(data) {
        console.log('🗑️ 处理分类删除:', data);
        this.dataManager.showToast('success', '同步完成', '分类已从侧边栏移除');
    }
    
    /**
     * 处理批量分类更新
     */
    handleCategoryBulkUpdate(data) {
        console.log('📦 处理批量分类更新:', data);
        this.dataManager.showToast('success', '同步完成', '所有分类状态已更新');
    }
    
    /**
     * 处理批量商品导入
     */
    handleProductBatchImport(data) {
        console.log('📥 处理批量商品导入:', data);
        const message = `导入完成，${data.successCount || 0} 个商品已添加到相应分类`;
        this.dataManager.showToast('success', '导入同步完成', message);
    }
    
    /**
     * 处理商品删除
     */
    handleProductDelete(data) {
        console.log('🗑️ 处理商品删除:', data);
        const message = `商品已删除，分类商品数量已同步更新`;
        this.dataManager.showToast('success', '删除同步完成', message);
    }
    
    /**
     * 处理监控完成
     */
    handleMonitorComplete(data) {
        console.log('🎯 处理监控完成:', data);
        const message = `监控数据已更新，影响 ${data.categoryCount || 0} 个分类`;
        this.dataManager.showToast('success', '监控同步完成', message);
    }
    
    /**
     * 强制全量同步
     * 用于解决状态不一致的问题
     */
    async forceFullSync() {
        console.log('⚡ 执行强制全量同步...');
        
        try {
            // 强制刷新所有状态
            await this.syncCategoryState('bulk_update', { forceRefresh: true });
            
            console.log('✅ 强制全量同步完成');
            
        } catch (error) {
            console.error('❌ 强制全量同步失败:', error);
            throw error;
        }
    }
    
    /**
     * 获取同步状态信息
     */
    getSyncStatus() {
        return {
            syncInProgress: this.syncInProgress,
            pendingSyncs: this.pendingSyncs.size,
            eventListeners: Array.from(this.eventListeners.keys())
        };
    }
}

// 导出到全局作用域
window.StateSyncManager = StateSyncManager;

console.log('📦 StateSyncManager 类已加载');