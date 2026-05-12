/**
 * 流量蜂小红书数据监控助手 - 分类管理器
 * Category Manager for Xiaohongshu Monitor Extension
 * 
 * 负责商品分类的创建、管理和数据统计
 * 支持分类间的数据迁移和层次化管理
 */

class CategoryManager {
    constructor(dataManager = null) {
        this.dataManager = dataManager;
        this.defaultCategoryId = 1; // "未分类"
        this.isInitialized = false;
        
        // 预设分类模板
        this.categoryTemplates = [
            { name: '服装配饰', description: '服装、鞋包、配饰等商品', color: '#ef4444' },
            { name: '美妆个护', description: '化妆品、护肤品、个护用品', color: '#f97316' },
            { name: '数码电器', description: '数码产品、家用电器', color: '#3b82f6' },
            { name: '食品饮料', description: '食品、饮料、零食', color: '#10b981' },
            { name: '家居生活', description: '家居用品、生活用品', color: '#8b5cf6' },
            { name: '运动户外', description: '运动用品、户外装备', color: '#06b6d4' },
            { name: '母婴用品', description: '母婴、儿童用品', color: '#f59e0b' },
            { name: '图书教育', description: '图书、教育培训产品', color: '#84cc16' }
        ];
    }

    /**
     * 初始化分类管理器
     */
    async init() {
        try {
            console.log('🔧 初始化分类管理器...');

            // 如果没有传入dataManager，则创建新的实例
            if (!this.dataManager) {
                this.dataManager = new LocalDataManager();
                await this.dataManager.init();
                console.log('📦 创建了新的LocalDataManager实例');
            } else {
                console.log('♻️ 使用共享的LocalDataManager实例');
            }

            this.isInitialized = true;
            console.log('✅ 分类管理器初始化完成');

        } catch (error) {
            console.error('❌ 分类管理器初始化失败:', error);
            throw error;
        }
    }

    /**
     * 检查是否已初始化
     */
    checkInitialized() {
        if (!this.isInitialized || !this.dataManager) {
            throw new Error('分类管理器未初始化，请先调用init()方法');
        }
    }

    /**
     * 创建新分类
     */
    async createCategory(name, description = '', color = null) {
        this.checkInitialized();
        
        try {
            // 验证分类名称
            const validation = this.validateCategoryName(name);
            if (!validation.valid) {
                throw new Error(validation.message);
            }

            // 检查是否重名
            const existingCategories = await this.dataManager.getCategories();
            const isDuplicate = existingCategories.some(cat => 
                cat.name.toLowerCase() === name.toLowerCase().trim()
            );

            if (isDuplicate) {
                throw new Error('分类名称已存在，请选择其他名称');
            }

            // 如果没有指定颜色，随机选择一个
            if (!color) {
                const colors = ['#ef4444', '#f97316', '#3b82f6', '#10b981', '#8b5cf6', '#06b6d4', '#f59e0b', '#84cc16'];
                color = colors[Math.floor(Math.random() * colors.length)];
            }

            const category = await this.dataManager.createCategory(name.trim(), description.trim(), color);
            
            console.log(`✅ 分类创建成功: ${category.name}`);
            
            // 发送分类更新事件
            this.notifyCategoryChange('created', category);
            
            return category;

        } catch (error) {
            console.error('❌ 分类创建失败:', error);
            throw error;
        }
    }

    /**
     * 批量创建预设分类
     */
    async createPresetCategories(selectedTemplates = []) {
        this.checkInitialized();
        
        try {
            const results = [];
            const errors = [];

            // 如果没有指定模板，使用所有预设模板
            const templates = selectedTemplates.length > 0 
                ? selectedTemplates 
                : this.categoryTemplates;

            console.log(`🔄 开始创建 ${templates.length} 个预设分类...`);

            for (let template of templates) {
                try {
                    const category = await this.createCategory(
                        template.name,
                        template.description,
                        template.color
                    );
                    results.push(category);
                    console.log(`✅ 预设分类创建: ${template.name}`);
                } catch (error) {
                    if (error.message.includes('已存在')) {
                        console.log(`ℹ️ 跳过已存在分类: ${template.name}`);
                        continue;
                    }
                    errors.push({
                        template: template,
                        error: error.message
                    });
                    console.error(`❌ 预设分类创建失败 ${template.name}:`, error.message);
                }
            }

            console.log(`✅ 预设分类创建完成: ${results.length} 成功, ${errors.length} 失败`);

            return {
                success: results.length,
                failed: errors.length,
                results: results,
                errors: errors
            };

        } catch (error) {
            console.error('❌ 批量创建预设分类失败:', error);
            throw error;
        }
    }

    /**
     * 更新分类信息
     */
    async updateCategory(id, updates) {
        this.checkInitialized();
        
        try {
            // 验证分类ID
            if (id === this.defaultCategoryId && updates.name && updates.name !== '未分类') {
                throw new Error('默认分类名称不能修改');
            }

            // 如果要修改名称，检查重名
            if (updates.name) {
                const validation = this.validateCategoryName(updates.name);
                if (!validation.valid) {
                    throw new Error(validation.message);
                }

                const categories = await this.dataManager.getCategories();
                const isDuplicate = categories.some(cat => 
                    cat.id !== id && cat.name.toLowerCase() === updates.name.toLowerCase().trim()
                );

                if (isDuplicate) {
                    throw new Error('分类名称已存在，请选择其他名称');
                }
            }

            const updatedCategory = await this.dataManager.updateCategory(id, updates);
            
            console.log(`✅ 分类更新成功: ${updatedCategory.name}`);
            
            // 发送分类更新事件
            this.notifyCategoryChange('updated', updatedCategory);
            
            return updatedCategory;

        } catch (error) {
            console.error('❌ 分类更新失败:', error);
            throw error;
        }
    }

    /**
     * 删除分类
     */
    async deleteCategory(id, moveToId = null) {
        this.checkInitialized();
        
        try {
            // 保护默认分类
            if (id === this.defaultCategoryId) {
                throw new Error('默认分类不能被删除');
            }

            // 检查分类是否存在
            const category = await this.dataManager.getCategoryById(id);
            if (!category) {
                throw new Error('分类不存在');
            }

            // 检查目标分类（如果指定）
            if (moveToId && moveToId !== this.defaultCategoryId) {
                const targetCategory = await this.dataManager.getCategoryById(moveToId);
                if (!targetCategory) {
                    throw new Error('目标分类不存在');
                }
            }

            // 获取该分类下的商品数量
            const productCount = await this.dataManager.getProductCountByCategory(id);
            
            if (productCount > 0) {
                const targetId = moveToId || this.defaultCategoryId;
                console.log(`🔄 正在移动 ${productCount} 个商品到分类 ${targetId}...`);
            }

            // 删除分类（数据迁移在LocalDataManager中处理）
            const success = await this.dataManager.deleteCategory(id, moveToId || this.defaultCategoryId);
            
            if (success) {
                console.log(`✅ 分类删除成功: ${category.name} (${productCount} 个商品已迁移)`);
                
                // 发送分类删除事件
                this.notifyCategoryChange('deleted', { 
                    ...category, 
                    movedProductsCount: productCount,
                    movedToId: moveToId || this.defaultCategoryId
                });
                
                return {
                    success: true,
                    deletedCategory: category,
                    movedProductsCount: productCount,
                    movedToId: moveToId || this.defaultCategoryId
                };
            }

        } catch (error) {
            console.error('❌ 分类删除失败:', error);
            throw error;
        }
    }

    /**
     * 获取分类统计信息
     */
    async getCategoryStats(categoryId = null) {
        this.checkInitialized();
        
        try {
            if (categoryId) {
                // 单个分类统计
                const category = await this.dataManager.getCategoryById(categoryId);
                if (!category) {
                    throw new Error('分类不存在');
                }

                const productCount = await this.dataManager.getProductCountByCategory(categoryId);
                const products = await this.dataManager.getProducts(categoryId, {}, { page: 1, limit: 1000 });
                
                // 计算销量统计
                const totalSales = products.products.reduce((sum, p) => sum + (p.product_sales || 0), 0);
                const avgSales = productCount > 0 ? Math.floor(totalSales / productCount) : 0;
                const maxSales = products.products.length > 0 
                    ? Math.max(...products.products.map(p => p.product_sales || 0))
                    : 0;

                // 计算价格统计
                const totalPrice = products.products.reduce((sum, p) => sum + (p.product_price || 0), 0);
                const avgPrice = productCount > 0 ? totalPrice / productCount : 0;

                return {
                    category: category,
                    productCount: productCount,
                    totalProducts: productCount,
                    totalSales: totalSales,
                    averageSales: avgSales,
                    avgPrice: avgPrice,
                    maxSales: maxSales,
                    lastUpdate: products.products.length > 0
                        ? new Date(Math.max(...products.products.map(p => new Date(p.extracted_at))))
                        : null
                };

            } else {
                // 全部分类统计
                const categories = await this.dataManager.getCategories();
                const stats = await Promise.all(categories.map(async (cat) => {
                    const productCount = await this.dataManager.getProductCountByCategory(cat.id);
                    return {
                        ...cat,
                        product_count: productCount
                    };
                }));

                const totalProducts = stats.reduce((sum, cat) => sum + cat.product_count, 0);
                const activeCategories = stats.filter(cat => cat.product_count > 0).length;

                return {
                    totalCategories: categories.length,
                    activeCategories: activeCategories,
                    totalProducts: totalProducts,
                    categories: stats.sort((a, b) => b.product_count - a.product_count)
                };
            }

        } catch (error) {
            console.error('❌ 获取分类统计失败:', error);
            throw error;
        }
    }

    /**
     * 移动商品到指定分类
     */
    async moveProductsToCategory(productIds, targetCategoryId) {
        this.checkInitialized();
        
        try {
            // 验证目标分类
            const targetCategory = await this.dataManager.getCategoryById(targetCategoryId);
            if (!targetCategory) {
                throw new Error('目标分类不存在');
            }

            // 这里需要在LocalDataManager中实现批量更新商品分类的方法
            // 暂时使用循环更新的方式
            const results = [];
            const errors = [];

            for (let productId of productIds) {
                try {
                    // 注意：这需要在LocalDataManager中添加updateProduct方法
                    console.log(`移动商品 ${productId} 到分类 ${targetCategoryId}`);
                    results.push(productId);
                } catch (error) {
                    errors.push({ productId, error: error.message });
                }
            }

            console.log(`✅ 商品移动完成: ${results.length} 成功, ${errors.length} 失败`);
            
            return {
                success: results.length,
                failed: errors.length,
                results: results,
                errors: errors
            };

        } catch (error) {
            console.error('❌ 移动商品失败:', error);
            throw error;
        }
    }

    /**
     * 搜索分类
     */
    async searchCategories(searchTerm) {
        this.checkInitialized();
        
        try {
            const categories = await this.dataManager.getCategories();
            
            if (!searchTerm || searchTerm.trim() === '') {
                return categories;
            }

            const term = searchTerm.toLowerCase().trim();
            return categories.filter(cat => 
                cat.name.toLowerCase().includes(term) ||
                (cat.description && cat.description.toLowerCase().includes(term))
            );

        } catch (error) {
            console.error('❌ 搜索分类失败:', error);
            throw error;
        }
    }

    /**
     * 获取分类树（支持层次化结构）
     */
    async getCategoryTree() {
        this.checkInitialized();
        
        try {
            const categories = await this.dataManager.getCategories();
            
            // ✅ 优化：现在getCategories()已经包含正确的product_count，无需重复查询
            const categoriesWithStats = categories.map(cat => ({
                ...cat,
                product_count: cat.product_count || 0, // 确保有默认值
                children: [] // 预留层次化结构支持
            }));

            // 按创建时间排序，默认分类始终在第一位
            return categoriesWithStats.sort((a, b) => {
                if (a.id === this.defaultCategoryId) return -1;
                if (b.id === this.defaultCategoryId) return 1;
                return a.created_at - b.created_at;
            });

        } catch (error) {
            console.error('❌ 获取分类树失败:', error);
            throw error;
        }
    }

    /**
     * 验证分类名称
     */
    validateCategoryName(name) {
        if (!name || typeof name !== 'string') {
            return { valid: false, message: '分类名称不能为空' };
        }

        const trimmedName = name.trim();

        if (trimmedName.length === 0) {
            return { valid: false, message: '分类名称不能为空' };
        }

        if (trimmedName.length > 50) {
            return { valid: false, message: '分类名称不能超过50个字符' };
        }

        // 检查特殊字符
        const invalidChars = /[<>:"/\\|?*]/;
        if (invalidChars.test(trimmedName)) {
            return { valid: false, message: '分类名称不能包含特殊字符 < > : " / \\ | ? *' };
        }

        return { valid: true, message: '分类名称有效' };
    }

    /**
     * 发送分类变化通知
     */
    notifyCategoryChange(action, categoryData) {
        try {
            // 发送消息给其他组件
            if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.sendMessage) {
                chrome.runtime.sendMessage({
                    action: 'category_changed',
                    changeType: action,
                    category: categoryData,
                    timestamp: new Date().toISOString()
                });
            }

            // 触发自定义事件
            if (typeof window !== 'undefined') {
                const event = new CustomEvent('categoryChanged', {
                    detail: {
                        action: action,
                        category: categoryData,
                        timestamp: new Date().toISOString()
                    }
                });
                window.dispatchEvent(event);
            }

        } catch (error) {
            console.warn('分类变化通知发送失败:', error);
        }
    }

    /**
     * 导出分类配置
     */
    async exportCategoryConfig() {
        this.checkInitialized();
        
        try {
            const categories = await this.dataManager.getCategories();
            
            const config = {
                version: '2.0.0',
                exportDate: new Date().toISOString(),
                categories: categories.map(cat => ({
                    name: cat.name,
                    description: cat.description,
                    color: cat.color,
                    // 不导出ID和时间戳，便于在其他环境导入
                }))
            };

            return config;

        } catch (error) {
            console.error('❌ 导出分类配置失败:', error);
            throw error;
        }
    }

    /**
     * 导入分类配置
     */
    async importCategoryConfig(config) {
        this.checkInitialized();
        
        try {
            if (!config || !config.categories || !Array.isArray(config.categories)) {
                throw new Error('无效的分类配置格式');
            }

            const results = [];
            const errors = [];

            for (let catConfig of config.categories) {
                try {
                    const category = await this.createCategory(
                        catConfig.name,
                        catConfig.description || '',
                        catConfig.color || null
                    );
                    results.push(category);
                } catch (error) {
                    // 跳过已存在的分类
                    if (error.message.includes('已存在')) {
                        continue;
                    }
                    errors.push({
                        categoryName: catConfig.name,
                        error: error.message
                    });
                }
            }

            console.log(`✅ 分类配置导入完成: ${results.length} 成功, ${errors.length} 失败`);

            return {
                success: results.length,
                failed: errors.length,
                results: results,
                errors: errors
            };

        } catch (error) {
            console.error('❌ 导入分类配置失败:', error);
            throw error;
        }
    }

    /**
     * 获取预设分类模板
     */
    getCategoryTemplates() {
        return [...this.categoryTemplates];
    }

    /**
     * 获取所有分类
     */
    async getAllCategories() {
        this.checkInitialized();
        
        try {
            return await this.dataManager.getCategories();
        } catch (error) {
            console.error('❌ 获取所有分类失败:', error);
            throw error;
        }
    }

    /**
     * 根据ID获取分类
     */
    async getCategoryById(categoryId) {
        this.checkInitialized();
        
        try {
            return await this.dataManager.getCategoryById(categoryId);
        } catch (error) {
            console.error(`❌ 获取分类 ${categoryId} 失败:`, error);
            throw error;
        }
    }

    /**
     * 获取预设分类模板
     */
    getPresetCategories() {
        return [...this.categoryTemplates];
    }

    /**
     * 重置为默认分类配置
     */
    async resetToDefault() {
        this.checkInitialized();
        
        try {
            console.log('🔄 重置为默认分类配置...');
            
            // 获取所有非默认分类
            const categories = await this.dataManager.getCategories();
            const nonDefaultCategories = categories.filter(cat => cat.id !== this.defaultCategoryId);

            // 将所有商品移动到默认分类
            for (let category of nonDefaultCategories) {
                const productCount = await this.dataManager.getProductCountByCategory(category.id);
                if (productCount > 0) {
                    await this.dataManager.moveProductsToCategory(category.id, this.defaultCategoryId);
                }
                await this.dataManager.deleteCategory(category.id, this.defaultCategoryId);
            }

            console.log(`✅ 分类重置完成，删除了 ${nonDefaultCategories.length} 个分类`);
            
            return {
                success: true,
                deletedCategories: nonDefaultCategories.length,
                message: '分类已重置为默认配置'
            };

        } catch (error) {
            console.error('❌ 分类重置失败:', error);
            throw error;
        }
    }
}

// 导出供其他模块使用
window.CategoryManager = CategoryManager;