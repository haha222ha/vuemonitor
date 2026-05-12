/**
 * 小红书数据管理器主脚本 v2.0
 * Data Manager Main Script for Xiaohongshu Monitor Extension
 */

class DataManagerApp {
    constructor() {
        this.localDataManager = null;
        this.categoryManager = null;
        this.dataMigrator = null;
        this.anomalyDetector = null; // 异常检测器
        this.batchDeleteManager = null; // 批量删除管理器
        this.charts = {};
        this.currentView = 'products';
        this.categoriesCache = new Map(); // 分类缓存
        this.filters = {
            category: 'all'
        };
        this.pagination = {
            currentPage: 1,
            pageSize: 20,
            totalItems: 0
        };
        // 🆕 异常监控分页状态
        this.anomalyPagination = {
            currentPage: 1,
            pageSize: 50,  // 每页显示50条
            totalItems: 0,
            totalPages: 0
        };
        this.selectedProducts = new Set();
        this.selectedCategory = null;
        this.latestAnomalyResults = null; // 最新异常检测结果

        // 🆕 分类筛选相关属性
        this.originalAnomalies = []; // 保存完整的原始数据
        this.selectedCategories = []; // 选中的分类（空数组表示全部）

        // 🎯 商品数据缓存（用于保持排序状态）
        this.currentProducts = []; // 当前筛选和排序后的商品列表

        // 🎯 排序状态
        this.sortState = {
            field: null,
            direction: 'desc' // 'asc' | 'desc'
        };

        // ⭐ ultrathink 修复：创建安全的Console机制，解决Console依赖性Bug
        this.initializeSafeConsole();

        // 初始化增强的错误处理和日志系统
        this.initializeEnhancedLogging();

        // ultrathink: 暴露全局实例供侧边栏调用
        window.dataManagerApp = this;
        this.safeLog('🌐 DataManagerApp已暴露到全局window.dataManagerApp');

        this.init();
    }

    /**
     * ⭐ ultrathink 核心修复：初始化安全的Console机制
     * 解决Console依赖性Bug - F12开启/关闭导致的功能异常
     */
    initializeSafeConsole() {
        // 创建安全的console方法，永远不会抛出错误
        this.safeLog = (message, ...args) => {
            try {
                if (typeof console !== 'undefined' && console.log) {
                    console.log(message, ...args);
                }
            } catch (e) {
                // 静默处理console错误，确保业务逻辑不受影响
            }
        };

        this.safeWarn = (message, ...args) => {
            try {
                if (typeof console !== 'undefined' && console.warn) {
                    console.warn(message, ...args);
                } else if (typeof console !== 'undefined' && console.log) {
                    console.log('[WARN]', message, ...args);
                }
            } catch (e) {
                // 静默处理console错误
            }
        };

        this.safeError = (message, ...args) => {
            try {
                if (typeof console !== 'undefined' && console.error) {
                    console.error(message, ...args);
                } else if (typeof console !== 'undefined' && console.log) {
                    console.log('[ERROR]', message, ...args);
                }
            } catch (e) {
                // 静默处理console错误
            }
        };

        // 为了向后兼容，也提供全局的安全console
        if (typeof window !== 'undefined') {
            window.safeConsole = {
                log: this.safeLog,
                warn: this.safeWarn,
                error: this.safeError
            };
        }
    }

    /**
     * 初始化增强的错误处理和日志系统
     */
    initializeEnhancedLogging() {
        // 性能监控对象
        this.performanceMonitor = {
            operations: new Map(),
            startTime: null,
            endTime: null,
            
            startOperation(operationName) {
                this.operations.set(operationName, performance.now());
                console.log(`⏱️ [${operationName}] 开始执行...`);
            },
            
            endOperation(operationName) {
                if (!this.operations.has(operationName)) {
                    console.warn(`⚠️ 操作 ${operationName} 未找到开始时间`);
                    return 0;
                }
                
                const startTime = this.operations.get(operationName);
                const duration = performance.now() - startTime;
                this.operations.delete(operationName);
                
                const emoji = duration < 100 ? '✅' : duration < 1000 ? '⚡' : '🐌';
                console.log(`${emoji} [${operationName}] 执行完成，耗时: ${duration.toFixed(2)}ms`);
                
                return duration;
            }
        };

        // 结构化日志记录器
        this.logger = {
            debug: (category, message, data = null) => {
                if (data) {
                    console.log(`🔍 [DEBUG][${category}] ${message}`, data);
                } else {
                    console.log(`🔍 [DEBUG][${category}] ${message}`);
                }
            },
            
            info: (category, message, data = null) => {
                if (data) {
                    console.log(`ℹ️ [INFO][${category}] ${message}`, data);
                } else {
                    console.log(`ℹ️ [INFO][${category}] ${message}`);
                }
            },
            
            warn: (category, message, data = null) => {
                if (data) {
                    console.warn(`⚠️ [WARN][${category}] ${message}`, data);
                } else {
                    console.warn(`⚠️ [WARN][${category}] ${message}`);
                }
            },
            
            error: (category, message, error = null, context = null) => {
                const errorInfo = {
                    message,
                    error: error ? {
                        name: error.name,
                        message: error.message,
                        stack: error.stack
                    } : null,
                    context,
                    timestamp: new Date().toISOString(),
                    url: window.location.href
                };
                
                console.error(`❌ [ERROR][${category}] ${message}`, errorInfo);
                
                // 显示用户友好的错误信息
                this.showUserFriendlyError(category, message, error);
                
                return errorInfo;
            },
            
            success: (category, message, data = null) => {
                if (data) {
                    console.log(`✅ [SUCCESS][${category}] ${message}`, data);
                } else {
                    console.log(`✅ [SUCCESS][${category}] ${message}`);
                }
            }
        };

        // 全局错误处理
        window.addEventListener('error', (event) => {
            this.logger.error('GLOBAL', '未捕获的错误', event.error, {
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno
            });
        });

        window.addEventListener('unhandledrejection', (event) => {
            this.logger.error('GLOBAL', '未处理的Promise拒绝', event.reason);
        });

        this.logger.info('INIT', '增强的错误处理和日志系统已初始化');
    }

    /**
     * 显示用户友好的错误信息
     */
    showUserFriendlyError(category, message, error) {
        const userFriendlyMessages = {
            'DATA_LOAD': '数据加载失败，请刷新页面重试',
            'NETWORK': '网络连接问题，请检查网络后重试',
            'VALIDATION': '数据验证失败，请检查输入格式',
            'PERMISSION': '权限不足，请联系管理员',
            'STORAGE': '存储空间不足或数据库访问失败',
            'EXPORT': '导出功能暂时不可用，请稍后重试',
            'IMPORT': '导入数据格式有误，请检查文件格式'
        };

        const userMessage = userFriendlyMessages[category] || '系统遇到未知错误，请联系技术支持';
        
        // 只在用户可见的严重错误时显示toast
        if (['DATA_LOAD', 'NETWORK', 'STORAGE', 'EXPORT', 'IMPORT'].includes(category)) {
            this.showToast('error', '操作失败', userMessage);
        }
    }

    async init() {
        this.performanceMonitor.startOperation('INIT_APP');
        this.logger.info('INIT', '数据管理器初始化开始');
        
        try {
            // 显示加载界面
            this.showLoading('正在初始化数据管理器...');
            
            // 初始化数据服务
            await this.initializeServices();
            
            // 初始化UI组件
            this.initializeUI();
            
            // 初始化ComponentBridge通信
            this.initializeComponentBridge();
            
            // 加载初始数据
            await this.loadInitialData();
            
            // 隐藏加载界面
            this.hideLoading();
            
            // 显示成功通知
            this.showToast('success', '数据管理器', '初始化完成');

            // 验证修复是否成功
            await this.validateTimeSeriesFix();

            const duration = this.performanceMonitor.endOperation('INIT_APP');
            this.logger.success('INIT', `数据管理器初始化完成，总耗时: ${duration.toFixed(2)}ms`);
            
        } catch (error) {
            this.performanceMonitor.endOperation('INIT_APP');
            this.logger.error('INIT', '数据管理器初始化失败', error, {
                step: '应用初始化',
                hasLocalDataManager: !!this.localDataManager,
                hasCategoryManager: !!this.categoryManager
            });
            
            this.hideLoading();
            this.showToast('error', '初始化失败', '系统初始化失败，请刷新页面重试');
        }
    }

    async initializeServices() {
        this.performanceMonitor.startOperation('INIT_SERVICES');
        this.logger.info('SERVICES', '正在初始化数据服务');
        
        try {
            // 等待必要的类加载完成
            await this.waitForClasses();
            
            // 使用统一数据服务管理器
            this.sharedDataService = SharedDataService.getInstance();
            await this.sharedDataService.init();
            
            // 从统一服务获取各个管理器实例
            this.localDataManager = this.sharedDataService.getLocalDataManager();
            this.categoryManager = this.sharedDataService.getCategoryManager();
            this.dataMigrator = this.sharedDataService.getDataMigrator();
            this.anomalyDetector = this.sharedDataService.getAnomalyDetector();
            
            // 初始化状态同步管理器
            this.stateSyncManager = new StateSyncManager(this);
            
            // 初始化导出管理器（延迟初始化）
            this.exportManager = null;
            
            this.performanceMonitor.endOperation('INIT_SERVICES');
            this.logger.success('SERVICES', '数据服务初始化完成（使用统一服务）', {
                hasLocalDataManager: !!this.localDataManager,
                hasCategoryManager: !!this.categoryManager,
                hasDataMigrator: !!this.dataMigrator,
                hasAnomalyDetector: !!this.anomalyDetector
            });
            
        } catch (error) {
            this.performanceMonitor.endOperation('INIT_SERVICES');
            this.logger.error('SERVICES', '数据服务初始化失败', error);
            throw error;
        }
    }

    async waitForClasses() {
        console.log('等待必要的类加载...');

        // 关键依赖类 - 必须首先加载
        const coreClasses = ['DateFormatter', 'SimpleGrowthCalculator', 'TimeSeriesDataManager'];

        // 服务管理类
        const serviceClasses = ['SharedDataService', 'ComponentBridge', 'StateSyncManager', 'ExportManager'];

        // 先等待核心依赖类
        console.log('🔄 加载核心依赖类...');
        for (const className of coreClasses) {
            await this.waitForClass(className);
        }
        console.log('✅ 核心依赖类加载完成');

        // 再等待服务管理类
        console.log('🔄 加载服务管理类...');
        for (const className of serviceClasses) {
            await this.waitForClass(className);
        }
        console.log('✅ 服务管理类加载完成');

        console.log('✅ 所有必要的类已加载');
    }
    
    async waitForClass(className) {
        return new Promise((resolve) => {
            if (typeof window[className] !== 'undefined') {
                resolve();
                return;
            }
            
            let attempts = 0;
            const maxAttempts = 100;
            const checkInterval = setInterval(() => {
                attempts++;
                if (typeof window[className] !== 'undefined') {
                    clearInterval(checkInterval);
                    console.log(`✅ ${className} 已加载`);
                    resolve();
                } else if (attempts >= maxAttempts) {
                    clearInterval(checkInterval);
                    console.error(`❌ ${className} 加载超时`);
                    resolve();
                }
            }, 50);
        });
    }

    initializeUI() {
        console.log('正在初始化UI组件...');
        
        // 事件系统完整性检查（已简化）
        
        // 绑定导航事件
        this.bindNavigationEvents();
        
        // 绑定视图切换事件
        this.bindViewEvents();
        
        // 绑定工具栏事件
        this.bindToolbarEvents();
        
        // 绑定快速操作事件
        this.bindQuickActionEvents();
        
        // 绑定表格事件
        this.bindTableEvents();
        
        // 绑定商品页面事件（修复批量删除按钮点击无反应问题）
        this.bindProductPageEvents();
        
        // 绑定分类管理事件
        this.bindCategoryEvents();

        // 🆕 绑定商品筛选事件
        this.bindProductFilterEvents();

        // 绑定筛选事件
        this.bindFilterEvents();
        
        // 绑定导出相关事件
        this.bindExportEvents();
        
        // 绑定事件委托
        this.bindEventDelegation();

        // 初始化悬浮图表功能
        this.initializeHoverChart();

        console.log('✅ UI组件初始化完成');
    }

    bindNavigationEvents() {
        // 刷新数据按钮
        document.getElementById('refreshDataBtn').addEventListener('click', () => {
            this.refreshAllData();
        });
        
        // 最小化按钮
        document.getElementById('minimizeBtn').addEventListener('click', () => {
            window.minimize && window.minimize();
        });
        
        // 关闭按钮
        document.getElementById('closeBtn').addEventListener('click', () => {
            if (confirm('确定要关闭数据管理器吗？')) {
                window.close();
            }
        });
    }

    bindViewEvents() {
        // 视图切换标签
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const view = e.target.closest('.tab-btn').dataset.view;
                this.switchView(view);
            });
        });
    }

    bindToolbarEvents() {
        // 搜索和筛选功能已移除
    }

    bindQuickActionEvents() {
        // 导出所有数据
        const exportAllBtn = document.getElementById('exportAllBtn');
        if (exportAllBtn) {
            exportAllBtn.addEventListener('click', () => {
                this.exportAllData();
            });
        }
        
        // 导出异常商品
        const exportAnomalyDataBtn = document.getElementById('exportAnomalyDataBtn');
        if (exportAnomalyDataBtn) {
            exportAnomalyDataBtn.addEventListener('click', () => {
                this.exportAnomalyResults();
            });
        }
        
        // 备份数据和清理缓存按钮已移除
        
        // 添加分类
        const addCategoryBtn = document.getElementById('addCategoryBtn');
        if (addCategoryBtn) {
            addCategoryBtn.addEventListener('click', () => {
                this.createNewCategory();
            });
        }

        // 异常检测按钮已移除

        // 导出异常检测结果
        const exportAnomalyResultsBtn = document.getElementById('exportAnomalyResultsBtn');
        if (exportAnomalyResultsBtn) {
            exportAnomalyResultsBtn.addEventListener('click', () => {
                this.exportAnomalyResults();
            });
        }
    }

    bindTableEvents() {
        // 全选复选框 - 商品列表
        document.getElementById('selectAll').addEventListener('change', (e) => {
            this.toggleSelectAll(e.target.checked);
        });

        // 全选复选框 - 异常监控
        const selectAllAnomalies = document.getElementById('selectAllAnomalies');
        if (selectAllAnomalies) {
            selectAllAnomalies.addEventListener('change', (e) => {
                this.toggleSelectAllAnomalies(e.target.checked);
            });
        }

        // 表格排序
        document.querySelectorAll('.sortable').forEach(header => {
            header.addEventListener('click', () => {
                this.sortTable(header.dataset.sort);
            });
        });

        // 🆕 分类筛选事件监听
        const categorySelect = document.getElementById('categoryFilterSelect');
        if (categorySelect) {
            categorySelect.addEventListener('change', (e) => {
                this.handleCategoryFilter(e.target.value);
            });
        }

        // 分页控件
        document.getElementById('prevPageBtn').addEventListener('click', () => {
            this.changePage(this.pagination.currentPage - 1);
        });

        document.getElementById('nextPageBtn').addEventListener('click', () => {
            this.changePage(this.pagination.currentPage + 1);
        });
    }

    bindCategoryEvents() {
        // 新建分类按钮
        document.getElementById('newCategoryBtn').addEventListener('click', () => {
            this.createNewCategory();
        });
    }

    /**
     * 🆕 绑定商品筛选事件
     */
    bindProductFilterEvents() {
        const productCategorySelect = document.getElementById('productCategoryFilterSelect');
        if (productCategorySelect) {
            productCategorySelect.addEventListener('change', (e) => {
                this.handleProductCategoryFilter(e.target.value);
            });
            console.log('✅ 商品筛选下拉框事件已绑定');
        } else {
            console.warn('⚠️ 未找到商品筛选下拉框元素');
        }
    }

    bindFilterEvents() {
        // 筛选功能已移除
    }

    bindExportEvents() {
        // 商品管理页面导出按钮
        const exportProductsBtn = document.getElementById('exportProductsBtn');
        if (exportProductsBtn) {
            exportProductsBtn.addEventListener('click', () => {
                this.openExportDialog();
            });
        }
    }

    bindEventDelegation() {
        // 使用事件委托处理动态生成的按钮点击事件
        document.addEventListener('click', (e) => {
            // 商品删除按钮
            if (e.target.matches('[data-action="delete-product"]')) {
                const productId = parseInt(e.target.getAttribute('data-product-id'), 10);
                this.deleteProduct(productId);
            }

            // 异常监控 - 忽略异常按钮
            if (e.target.matches('[data-action="ignore-anomaly"]')) {
                const productId = parseInt(e.target.getAttribute('data-product-id'), 10);
                this.ignoreAnomaly(productId);
            }

            // 异常监控 - 查看详情按钮
            if (e.target.matches('[data-action="view-anomaly"]')) {
                const productId = parseInt(e.target.getAttribute('data-product-id'), 10);
                this.viewAnomalyDetails(productId);
            }

            // 分类菜单按钮
            if (e.target.matches('[data-action="show-category-menu"]')) {
                const categoryId = e.target.getAttribute('data-category-id');
                this.showCategoryMenu(categoryId);
            }
            
            // 分类编辑按钮
            if (e.target.matches('[data-action="edit-category"]')) {
                const categoryId = e.target.getAttribute('data-category-id');
                this.editCategory(categoryId);
            }
            
            // 分类删除按钮
            if (e.target.matches('[data-action="delete-category"]')) {
                const categoryId = e.target.getAttribute('data-category-id');
                this.deleteCategory(categoryId);
            }
            
            // ultrathink: 移除异常详情功能，简化设计

            // ultrathink: 移除标记异常已解决功能，简化设计
        });
    }

    async loadInitialData() {
        console.log('正在加载初始数据...');
        
        try {
            // 加载分类树
            await this.loadCategoryTree();
            
            // 加载默认视图数据
            await this.loadViewData(this.currentView);
            
            console.log('✅ 初始数据加载完成');
            
        } catch (error) {
            console.error('❌ 初始数据加载失败:', error);
            throw error;
        }
    }


    async loadCategoryTree() {
        try {
            // 确保 categoryManager 已初始化
            if (!this.categoryManager) {
                console.error('❌ CategoryManager 未初始化');
                return;
            }

            const categories = await this.categoryManager.getAllCategories();
            
            // 📊 调试信息：分类数据加载
            console.log('🔍 分类数据加载详情:', {
                总分类数: categories.length,
                分类详细信息: categories.map(cat => ({id: cat.id, name: cat.name})),
                分类ID类型: categories.map(cat => typeof cat.id)
            });
            
            // 更新分类缓存 - 确保ID类型一致
            this.categoriesCache.clear();
            categories.forEach(category => {
                // 确保category.id是数字类型
                const categoryId = typeof category.id === 'string' ? parseInt(category.id) : category.id;
                this.categoriesCache.set(categoryId, {
                    ...category,
                    id: categoryId  // 统一为数字类型
                });
            });
            
            console.log('✅ 分类缓存已更新，缓存大小:', this.categoriesCache.size);
            console.log('✅ 缓存中的分类ID:', Array.from(this.categoriesCache.keys()));
            
            const categoryTree = document.getElementById('categoryTree');
            
            categoryTree.innerHTML = categories.map(category => `
                <div class="category-item" data-category-id="${category.id}">
                    <div class="category-name">
                        <span class="category-icon">${category.icon || '📁'}</span>
                        <span>${category.name}</span>
                    </div>
                    <div class="category-count">${category.product_count || 0}</div>
                </div>
            `).join('');
            
            // 绑定分类点击事件
            categoryTree.querySelectorAll('.category-item').forEach(item => {
                item.addEventListener('click', () => {
                    this.selectCategory(parseInt(item.dataset.categoryId));
                });
            });
            
        } catch (error) {
            console.error('❌ 加载分类树失败:', error);
            console.error(error);
        }
    }

    /**
     * 强制刷新分类缓存
     */
    async forceRefreshCategoryCache() {
        try {
            console.log('🔄 强制刷新分类缓存...');
            await this.loadCategoryTree();
            console.log('✅ 分类缓存强制刷新完成');
        } catch (error) {
            console.error('❌ 强制刷新分类缓存失败:', error);
        }
    }

    /**
     * 数据一致性检查
     */
    async validateDataConsistency(products) {
        console.log('🔍 开始数据一致性检查...');
        
        const validationResults = {
            totalProducts: products.length,
            validProducts: 0,
            invalidProducts: 0,
            missingNames: 0,
            invalidCategories: 0,
            fieldStats: {
                hasProductName: 0,
                hasProductUrl: 0,
                hasCategoryId: 0,
                hasProductPrice: 0,
                hasProductSales: 0
            },
            issues: []
        };

        products.forEach((product, index) => {
            let isValid = true;
            const issues = [];

            // 检查必要字段
            if (!this.getProductName(product) || this.getProductName(product) === '商品名称缺失') {
                validationResults.missingNames++;
                issues.push('缺少商品名称');
                isValid = false;
            }

            // 检查分类ID是否有效
            const categoryId = product.category_id;
            if (!categoryId || (!this.categoriesCache.has(categoryId))) {
                validationResults.invalidCategories++;
                issues.push(`无效分类ID: ${categoryId}`);
                isValid = false;
            }

            // 统计字段存在情况
            if (product.product_name) validationResults.fieldStats.hasProductName++;
            if (product.product_url) validationResults.fieldStats.hasProductUrl++;
            if (product.category_id) validationResults.fieldStats.hasCategoryId++;
            if (product.product_price !== undefined) validationResults.fieldStats.hasProductPrice++;
            if (product.product_sales !== undefined) validationResults.fieldStats.hasProductSales++;

            if (isValid) {
                validationResults.validProducts++;
            } else {
                validationResults.invalidProducts++;
                validationResults.issues.push({
                    productIndex: index,
                    productId: product.id || product.product_id,
                    issues: issues
                });
            }
        });

        console.log('📊 数据一致性检查结果:', validationResults);

        // 如果有严重问题，输出详细信息
        if (validationResults.invalidProducts > 0) {
            console.warn('⚠️ 发现数据不一致问题:');
            validationResults.issues.slice(0, 5).forEach(issue => {
                console.warn(`  商品 ${issue.productIndex + 1} (ID: ${issue.productId}): ${issue.issues.join(', ')}`);
            });
        }

        return validationResults;
    }

    async switchView(view) {
        if (this.currentView === view) return;
        
        console.log(`切换到视图: ${view}`);
        
        // 更新标签状态
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === view);
        });
        
        // 更新面板显示
        document.querySelectorAll('.view-panel').forEach(panel => {
            panel.classList.toggle('active', panel.id === `${view}View`);
        });
        
        this.currentView = view;
        
        // 加载视图数据
        await this.loadViewData(view);
    }

    async loadViewData(view) {
        this.showLoading(`正在加载${this.getViewName(view)}数据...`);

        try {
            switch (view) {
                case 'products':
                    // 🆕 每次进入商品视图都刷新分类筛选选项
                    await this.loadProductCategoryFilterOptions();
                    await this.loadProductsData();
                    break;
                case 'categories':
                    await this.loadCategoriesData();
                    break;
                case 'anomalies':
                    await this.loadAnomaliesData();
                    break;
            }
        } catch (error) {
            console.error(`加载${view}视图数据失败:`, error);
            this.showToast('error', '加载失败', `无法加载${this.getViewName(view)}数据`);
        } finally {
            this.hideLoading();
        }
    }



    async loadProductsData() {
        this.performanceMonitor.startOperation('LOAD_PRODUCTS');
        
        try {
            this.logger.info('PRODUCTS', '开始加载商品数据', {
                currentFilters: this.filters,
                cacheSize: this.categoriesCache.size
            });
            
            // 确保分类缓存是最新的
            if (!this.categoriesCache || this.categoriesCache.size === 0) {
                this.logger.warn('PRODUCTS', '分类缓存为空，重新加载');
                await this.forceRefreshCategoryCache();
            }
            
            // 获取产品数据
            let products = await this.getFilteredProducts();

            this.logger.debug('PRODUCTS', '获取到的商品数据', {
                totalProducts: products.length,
                currentPage: this.pagination.currentPage,
                pageSize: this.pagination.pageSize
            });

            // 🎯 如果有排序状态，应用排序
            if (this.sortState.field) {
                await this.applySortToProducts(products);
                products = this.currentProducts; // 使用排序后的数据
            } else {
                // 🎯 保存数据到缓存
                this.currentProducts = products;
            }

            // 更新表格
            this.updateProductsTable(products);

            // 更新分页
            this.updatePagination(products.length);
            
            // 更新计数
            document.getElementById('productCount').textContent = products.length;
            
            // 绑定商品页面的动态事件
            this.bindProductPageEvents();

            // ultrathink: 更新商品管理页面的统计卡片
            await this.updateProductsStatsCards(products);

            // ultrathink: 更新侧边栏统计数据，确保异常商品数量正确显示
            await this.updateStatistics();

            this.performanceMonitor.endOperation('LOAD_PRODUCTS');
            this.logger.success('PRODUCTS', `商品数据加载完成，共${products.length}个商品`);
            
        } catch (error) {
            this.performanceMonitor.endOperation('LOAD_PRODUCTS');
            this.logger.error('DATA_LOAD', '加载商品数据失败', error, {
                filters: this.filters,
                cacheSize: this.categoriesCache.size,
                hasLocalDataManager: !!this.localDataManager
            });
        }
    }

    /**
     * 更新商品管理页面的统计卡片 - ultrathink
     */
    async updateProductsStatsCards(products) {
        try {
            console.log('📊 更新商品管理页面统计卡片...');

            // 1. 商品总数
            const totalProducts = products.length;
            document.getElementById('productsTotalProducts').textContent = totalProducts.toLocaleString();

            // 2. 计算平均价格
            let totalPrice = 0;
            let validPriceCount = 0;
            products.forEach(product => {
                const price = product.product_price || product.price || 0;
                if (price > 0) {
                    totalPrice += parseFloat(price);
                    validPriceCount++;
                }
            });
            const avgPrice = validPriceCount > 0 ? totalPrice / validPriceCount : 0;
            document.getElementById('productsAvgPrice').textContent = `¥${avgPrice.toFixed(2)}`;

            // 3. 计算总销量
            let totalSales = 0;
            products.forEach(product => {
                const sales = product.product_sales || product.sales || 0;
                totalSales += parseInt(sales) || 0;
            });
            document.getElementById('productsTotalSales').textContent = totalSales.toLocaleString();

            // 4. 获取异常商品数量
            let anomaliesCount = 0;
            products.forEach(product => {
                if (product.is_anomaly) {
                    anomaliesCount++;
                }
            });
            document.getElementById('productsAnomalies').textContent = anomaliesCount.toLocaleString();

            // 5. 更新趋势指示器（简化版，可以后续扩展）
            this.updateProductsTrendIndicators(products);

            console.log('✅ 商品管理页面统计卡片更新完成:', {
                totalProducts,
                avgPrice: avgPrice.toFixed(2),
                totalSales,
                anomaliesCount
            });

        } catch (error) {
            console.error('❌ 更新商品统计卡片失败:', error);
        }
    }

    /**
     * 更新商品页面的趋势指示器 - ultrathink
     */
    updateProductsTrendIndicators(products) {
        try {
            // 简化版趋势计算（基于24小时增长数据）
            let weeklyNewProducts = 0;
            let totalGrowthSales = 0;
            let totalGrowthRevenue = 0;

            const oneWeekAgo = new Date();
            oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);

            products.forEach(product => {
                // 统计本周新增商品
                if (product.created_at) {
                    const createdDate = new Date(product.created_at);
                    if (createdDate >= oneWeekAgo) {
                        weeklyNewProducts++;
                    }
                }

                // 统计24小时增长数据
                const growthSales = product['新增销量'] || 0;
                const growthRevenue = product['新增销售额'] || 0;
                totalGrowthSales += growthSales;
                totalGrowthRevenue += growthRevenue;
            });

            // 更新商品总览趋势
            const productsTrendElement = document.querySelector('#productsTotalProducts').closest('.card-content').querySelector('.trend-indicator');
            if (productsTrendElement) {
                productsTrendElement.textContent = `↗ +${weeklyNewProducts}`;
                productsTrendElement.className = `trend-indicator ${weeklyNewProducts > 0 ? 'positive' : 'neutral'}`;
            }

            // 更新总销量趋势
            const salesTotalTrendElement = document.querySelector('#productsTotalSales').closest('.card-content').querySelector('.trend-indicator');
            if (salesTotalTrendElement) {
                const salesTrendPercent = totalGrowthSales > 0 ? '+' + (totalGrowthSales * 0.1).toFixed(1) : '0';
                salesTotalTrendElement.textContent = totalGrowthSales > 0 ? `↗ ${salesTrendPercent}%` : `→ 0%`;
                salesTotalTrendElement.className = `trend-indicator ${totalGrowthSales > 0 ? 'positive' : 'neutral'}`;
            }

            console.log('📈 趋势指示器更新完成:', {
                weeklyNewProducts,
                totalGrowthSales,
                totalGrowthRevenue
            });

        } catch (error) {
            console.error('❌ 更新趋势指示器失败:', error);
        }
    }

    /**
     * 绑定商品页面相关的动态事件
     */
    bindProductPageEvents() {
        console.log('🔄 绑定商品页面事件...');
        
        // 批量删除按钮
        const batchDeleteBtn = document.getElementById('batchDeleteBtn');
        if (batchDeleteBtn) {
            // 检查是否已绑定事件，避免重复绑定
            if (!batchDeleteBtn.dataset.eventsBound) {
                batchDeleteBtn.addEventListener('click', () => {
                    this.safeLog('🗑️ 批量删除按钮被点击');
                    this.showBatchDeleteDialog();
                });
                batchDeleteBtn.dataset.eventsBound = 'true';
                this.safeLog('✅ 批量删除按钮事件绑定成功');
            }
        } else {
            this.safeWarn('⚠️ 批量删除按钮不存在，跳过事件绑定');
        }
        
        // 导出商品按钮
        const exportProductsBtn = document.getElementById('exportProductsBtn');
        if (exportProductsBtn) {
            // 检查是否已绑定事件，避免重复绑定
            if (!exportProductsBtn.dataset.eventsBound) {
                exportProductsBtn.addEventListener('click', () => {
                    this.safeLog('📤 导出商品按钮被点击');
                    this.openExportDialog();
                });
                exportProductsBtn.dataset.eventsBound = 'true';
                this.safeLog('✅ 导出商品按钮事件绑定成功');
            }
        } else {
            this.safeWarn('⚠️ 导出商品按钮不存在，跳过事件绑定');
        }

        // ==================== 分类编辑功能事件绑定 ====================

        // 绑定分类点击事件
        document.querySelectorAll('.product-category').forEach(categorySpan => {
            categorySpan.addEventListener('click', (e) => {
                e.stopPropagation(); // 防止事件冒泡
                const productId = parseInt(e.target.dataset.productId);
                const categoryId = parseInt(e.target.dataset.categoryId);

                if (!productId || !categoryId) {
                    console.error('缺少必要的商品ID或分类ID');
                    return;
                }

                this.showCategoryFloatSelector(e, productId, categoryId);
            });
        });

        // 初始化点击外部关闭处理器
        if (!this.outsideClickHandler) {
            this.outsideClickHandler = (e) => {
                const floatSelector = document.getElementById('categoryFloatSelector');
                if (!floatSelector) return;

                const isClickInside = floatSelector.contains(e.target);
                const isClickOnCategory = e.target.classList.contains('product-category');

                if (!isClickInside && !isClickOnCategory) {
                    this.hideCategoryFloatSelector();
                }
            };
        }

        this.safeLog('✅ 商品页面动态事件绑定完成（包含分类编辑功能）');
    }

    async getFilteredProducts() {
        this.performanceMonitor.startOperation('FILTER_PRODUCTS');
        
        try {
            let products = await this.localDataManager.getAllProducts();
            
            // 📊 调试信息：显示原始产品数据结构
            if (products.length > 0) {
                this.logger.debug('PRODUCTS', '获取原始产品数据', {
                    总数: products.length,
                    第一个产品: products[0],
                    字段列表: Object.keys(products[0]),
                    数据样本: {
                        product_name: products[0].product_name,
                        category_id: products[0].category_id,
                        product_price: products[0].product_price,
                        product_sales: products[0].product_sales
                    }
                });
            }
        
        // 应用搜索筛选 - 修复字段名
        if (this.filters.search) {
            const search = this.filters.search.toLowerCase();
            products = products.filter(product => 
                (product.product_name && product.product_name.toLowerCase().includes(search)) ||
                (product.product_url && product.product_url.toLowerCase().includes(search))
            );
        }
        
        // 应用分类筛选 - 修复字段名
        if (this.filters.category !== 'all') {
            products = products.filter(product => 
                product.category_id == this.filters.category
            );
        }
        
        // 价格和销量筛选功能已移除
        
            const filteredCount = products.length;
            this.performanceMonitor.endOperation('FILTER_PRODUCTS');
            this.logger.debug('PRODUCTS', '产品筛选完成', {
                筛选后数量: filteredCount,
                应用的筛选器: {
                    分类: this.filters.category
                }
            });
            
            return products;
            
        } catch (error) {
            this.performanceMonitor.endOperation('FILTER_PRODUCTS');
            this.logger.error('PRODUCTS', '产品筛选失败', error);
            throw error;
        }
    }

    updateProductsTable(products) {
        const tbody = document.getElementById('productsTableBody');
        const startIndex = (this.pagination.currentPage - 1) * this.pagination.pageSize;
        const endIndex = startIndex + this.pagination.pageSize;
        const pageProducts = products.slice(startIndex, endIndex);
        
        // 📊 调试信息：检查商品数据结构
        if (pageProducts.length > 0) {
            this.logger.debug('PRODUCTS', '页面商品数据检查', {
                页面商品数量: pageProducts.length,
                分页信息: {
                    当前页: this.pagination.currentPage,
                    页面大小: this.pagination.pageSize,
                    起始索引: startIndex,
                    结束索引: endIndex
                },
                第一个商品: pageProducts[0],
                字段验证: {
                    product_name: pageProducts[0].product_name,
                    productName: pageProducts[0].productName,
                    title: pageProducts[0].title,
                    category_id: pageProducts[0].category_id,
                    所有字段: Object.keys(pageProducts[0])
                }
            });
        }
        
        if (pageProducts.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="11" class="text-center">
                        <div class="empty-state">
                            <div class="empty-icon">📦</div>
                            <div class="empty-text">没有找到商品数据</div>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = pageProducts.map(product => {
            const categoryName = this.getCategoryName(product.category_id);
            const storeFollowers = product.additional_data?.store_followers !== undefined ? product.additional_data.store_followers : 0;
            const recentSales = product.additional_data?.recent_sales !== undefined ? product.additional_data.recent_sales : 0;

            // 🆕 计算粉销比
            const storeSales = this.getStoreSales(product);
            const productSales = this.getProductSales(product);
            const storeFanSalesRatio = this.calculateFanSalesRatio(storeSales, storeFollowers);
            const productFanSalesRatio = this.calculateFanSalesRatio(productSales, storeFollowers);

            return `
                <tr class="product-row" data-product-id="${product.id}">
                    <td class="checkbox-col">
                        <input type="checkbox" class="product-checkbox" value="${product.id}">
                    </td>
                    <td>
                        <div class="product-title" title="${this.getProductName(product)}">
                            ${product.product_url || product.productUrl ?
                                `<a href="${product.product_url || product.productUrl}" target="_blank" class="product-link" rel="noopener noreferrer">
                                    ${this.getProductName(product)}
                                </a>` :
                                this.getProductName(product)
                            }
                        </div>
                    </td>
                    <td>
                        <span class="product-category"
                              data-product-id="${product.id}"
                              data-category-id="${product.category_id}"
                              title="点击修改分类">
                            ${categoryName}
                        </span>
                    </td>
                    <td>
                        <span class="product-price">¥${this.getProductPrice(product).toFixed(2)}</span>
                    </td>
                    <td>
                        <span class="product-sales">${productSales.toLocaleString()}</span>
                    </td>
                    <td>
                        <span class="store-followers">${storeFollowers.toLocaleString()}</span>
                    </td>
                    <td>
                        <span class="store-sales">${storeSales.toLocaleString()}</span>
                    </td>
                    <td>
                        <span class="store-name" title="${this.getStoreName(product)}">${this.getStoreName(product)}</span>
                    </td>
                    <td>
                        <span class="recent-sales">${(recentSales || 0).toLocaleString()}</span>
                    </td>
                    <td>
                        <span class="fan-sales-ratio ${this.getFanSalesRatioClass(storeFanSalesRatio)}"
                              title="店铺销量 ${storeSales} ÷ 粉丝数 ${storeFollowers}">
                            ${storeFanSalesRatio.toFixed(1)}
                        </span>
                    </td>
                    <td>
                        <span class="fan-sales-ratio ${this.getFanSalesRatioClass(productFanSalesRatio)}"
                              title="商品销量 ${productSales} ÷ 粉丝数 ${storeFollowers}">
                            ${productFanSalesRatio.toFixed(1)}
                        </span>
                    </td>
                    <td>
                        <span class="extracted-time">${this.formatDate(product.extracted_at)}</span>
                    </td>
                    <td>
                        <div class="product-actions">
                            <button class="action-icon delete-btn" title="删除" data-action="delete-product" data-product-id="${product.id}">
                                🗑️
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
        
        // 绑定复选框事件
        tbody.querySelectorAll('.product-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const productId = parseInt(e.target.value);
                if (e.target.checked) {
                    this.selectedProducts.add(productId);
                } else {
                    this.selectedProducts.delete(productId);
                }
                this.updateSelectAllState();
            });
        });
    }

    async loadCategoriesData() {
        try {
            const categories = await this.categoryManager.getAllCategories();
            await this.updateCategoryCards(categories);
        } catch (error) {
            console.error('加载分类数据失败:', error);
        }
    }

    async updateCategoryCards(categories) {
        const categoryCards = document.getElementById('categoryCards');
        
        if (categories.length === 0) {
            categoryCards.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📁</div>
                    <div class="empty-text">暂无分类数据</div>
                </div>
            `;
            return;
        }
        
        const cardsHtml = await Promise.all(categories.map(async category => {
            const stats = await this.categoryManager.getCategoryStats(category.id);
            
            return `
                <div class="category-card" data-category-id="${category.id}">
                    <div class="category-card-header">
                        <div class="category-card-title">${category.name}</div>
                        <button class="category-card-menu" data-action="show-category-menu" data-category-id="${category.id}">
                            ⋯
                        </button>
                    </div>
                    <div class="category-card-stats">
                        <div class="category-stat">
                            <span class="category-stat-label">商品数量</span>
                            <span class="category-stat-value">${stats.totalProducts}</span>
                        </div>
                        <div class="category-stat">
                            <span class="category-stat-label">平均价格</span>
                            <span class="category-stat-value">¥${stats.avgPrice?.toFixed(2) || '0.00'}</span>
                        </div>
                        <div class="category-stat">
                            <span class="category-stat-label">总销量</span>
                            <span class="category-stat-value">${stats.totalSales?.toLocaleString() || '0'}</span>
                        </div>
                    </div>
                </div>
            `;
        }));
        
        categoryCards.innerHTML = cardsHtml.join('');
        
        // 绑定分类卡片点击事件
        categoryCards.querySelectorAll('.category-card').forEach(card => {
            card.addEventListener('click', () => {
                const categoryId = parseInt(card.dataset.categoryId);
                this.selectCategoryCard(categoryId);
            });
        });
    }

    // 工具方法
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    getViewName(view) {
        const names = {
            products: '商品管理',
            categories: '分类管理',
            anomalies: '异常监控'
        };
        return names[view] || view;
    }

    getCategoryName(categoryId) {
        // 统一ID类型为数字
        const numericCategoryId = typeof categoryId === 'string' ? parseInt(categoryId) : categoryId;
        
        // 📊 调试信息：分类名称获取过程
        console.log('🔍 获取分类名称:', {
            原始categoryId: categoryId,
            数字categoryId: numericCategoryId,
            缓存存在: !!this.categoriesCache,
            缓存大小: this.categoriesCache?.size || 0,
            缓存中有此ID: this.categoriesCache?.has(numericCategoryId) || false,
            所有分类ID: this.categoriesCache ? Array.from(this.categoriesCache.keys()) : []
        });
        
        // 尝试从缓存的分类数据中获取名称
        if (this.categoriesCache && this.categoriesCache.has(numericCategoryId)) {
            const categoryName = this.categoriesCache.get(numericCategoryId).name;
            console.log(`✅ 找到分类${numericCategoryId}: ${categoryName}`);
            return categoryName;
        }
        
        // 如果缓存不存在，返回默认值
        const defaultName = numericCategoryId === 1 ? '未分类' : `分类${numericCategoryId}`;
        console.log(`⚠️ 未找到分类${numericCategoryId}，使用默认名称: ${defaultName}`);
        return defaultName;
    }

    /**
     * 智能获取商品名称 - 支持多种字段格式
     */
    getProductName(product) {
        // 尝试多种可能的字段名
        const possibleFields = [
            'product_name',    // 数据库标准格式
            'productName',     // Excel解析格式
            '商品名称',         // 中文字段名
            '产品名称',         // 备选中文字段名
            'title',           // 通用标题字段
            'name'             // 通用名称字段
        ];
        
        for (let field of possibleFields) {
            if (product[field] && product[field].trim() !== '') {
                return product[field].trim();
            }
        }
        
        // 如果都没有，尝试从ID生成名称
        if (product.product_id) {
            return `商品_${product.product_id}`;
        }
        
        if (product.id) {
            return `商品_${product.id}`;
        }
        
        // 最后的备用方案
        return '商品名称缺失';
    }

    /**
     * 智能获取商品价格 - 支持多种字段格式
     */
    getProductPrice(product) {
        const priceFields = [
            'product_price',
            'productPrice', 
            '商品价格',
            '产品价格',
            'price'
        ];
        
        for (let field of priceFields) {
            if (product[field] !== undefined && product[field] !== null && !isNaN(parseFloat(product[field]))) {
                return parseFloat(product[field]);
            }
        }
        
        return 0;
    }

    /**
     * 智能获取商品销量 - 支持多种字段格式
     */
    getProductSales(product) {
        const salesFields = [
            'product_sales',
            'productSales',
            '商品销量', 
            '产品销量',
            'sales'
        ];
        
        for (let field of salesFields) {
            if (product[field] !== undefined && product[field] !== null && !isNaN(parseInt(product[field]))) {
                return parseInt(product[field]);
            }
        }
        
        return 0;
    }

    /**
     * 智能获取店铺销量 - 支持多种字段格式
     */
    getStoreSales(product) {
        const storeSalesFields = [
            'store_sales',
            'storeSales',
            '店铺销量',
            '店铺总销量'
        ];
        
        for (let field of storeSalesFields) {
            if (product[field] !== undefined && product[field] !== null && !isNaN(parseInt(product[field]))) {
                return parseInt(product[field]);
            }
        }
        
        return 0;
    }

    /**
     * 智能获取店铺名称 - 支持多种字段格式
     */
    getStoreName(product) {
        const storeNameFields = [
            'store_name',
            'storeName',
            '店铺名称',
            '店铺',
            'store'
        ];

        for (let field of storeNameFields) {
            if (product[field] && product[field].trim() !== '') {
                return product[field].trim();
            }
        }

        return '';
    }

    /**
     * 计算粉销比（Fan-Sales Ratio）
     * @param {number} sales - 销量
     * @param {number} followers - 粉丝数
     * @returns {number} 粉销比，保留1位小数
     */
    calculateFanSalesRatio(sales, followers) {
        // 边界处理：销量或粉丝数为0、缺失、无效时返回0
        if (!sales || sales === 0 || !followers || followers === 0) {
            return 0;
        }

        // 计算比值
        const ratio = sales / followers;

        // 处理 Infinity 和 NaN 情况
        if (!isFinite(ratio) || isNaN(ratio)) {
            return 0;
        }

        return parseFloat(ratio.toFixed(1)); // 保留1位小数
    }

    /**
     * 获取粉销比的CSS类名（用于分级着色）
     * @param {number} ratio - 粉销比值
     * @returns {string} CSS类名
     */
    getFanSalesRatioClass(ratio) {
        if (ratio === 0) {
            return 'ratio-zero';
        } else if (ratio >= 5.0) {
            return 'ratio-high';    // 高转化：≥5.0
        } else if (ratio >= 2.0) {
            return 'ratio-medium';  // 中等：2.0-4.9
        } else {
            return 'ratio-low';     // 低转化：<2.0
        }
    }

    getProductStatus(product) {
        // 简单的状态判断逻辑 - 使用正确的字段名
        const sales = this.getProductSales(product);
        if (!sales || sales === 0) {
            return { class: 'error', text: '无销量' };
        } else if (sales < 100) {
            return { class: 'warning', text: '销量低' };
        } else {
            return { class: 'normal', text: '正常' };
        }
    }

    getTimeAgo(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diffMs = now - time;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        
        if (diffMins < 1) return '刚刚';
        if (diffMins < 60) return `${diffMins}分钟前`;
        if (diffHours < 24) return `${diffHours}小时前`;
        return `${diffDays}天前`;
    }

    getChangeType(activity) {
        // 优先使用新增销量数据
        if (activity.newSales !== undefined) {
            if (activity.newSales > 0) return 'positive';
            if (activity.newSales < 0) return 'negative';
            return 'neutral';
        }

        // 后备：使用销量变化数据
        const change = (activity.currentSales || 0) - (activity.previousSales || 0);
        if (change > 0) return 'positive';
        if (change < 0) return 'negative';
        return 'neutral';
    }

    getChangeIcon(type) {
        const icons = {
            positive: '📈',
            negative: '📉',
            neutral: '➖'
        };
        return icons[type] || '📊';
    }

    formatDate(timestamp) {
        if (!timestamp) return '-';
        return new Date(timestamp).toLocaleString('zh-CN');
    }

    /**
     * 格式化为图表日期格式 (9月X日)
     */
    formatChartDate(timestamp) {
        if (!timestamp) return '-';
        const date = new Date(timestamp);
        const month = date.getMonth() + 1;
        const day = date.getDate();
        return `${month}月${day}日`;
    }

    showLoading(text = '正在加载...') {
        const overlay = document.getElementById('loadingOverlay');
        const loadingText = document.querySelector('.loading-text');
        if (loadingText) {
            loadingText.textContent = text;
        }
        overlay.classList.add('active');
    }

    hideLoading() {
        document.getElementById('loadingOverlay').classList.remove('active');
    }

    showToast(type, title, message) {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icon = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        }[type] || 'ℹ️';
        
        toast.innerHTML = `
            <div class="toast-icon">${icon}</div>
            <div class="toast-content">
                <div class="toast-title">${title}</div>
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close">×</button>
        `;
        
        container.appendChild(toast);
        
        // 绑定关闭事件
        toast.querySelector('.toast-close').addEventListener('click', () => {
            toast.remove();
        });
        
        // 自动消失
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 5000);
    }

    // 刷新所有数据 - 使用状态同步管理器
    async refreshAllData() {
        this.showToast('info', '刷新数据', '正在刷新所有数据...');

        try {
            // 使用状态同步管理器进行强制全量同步
            await this.stateSyncManager.forceFullSync();

            // ultrathink: 强制同步后，更新统计数据和当前视图
            await this.updateStatistics();
            await this.loadViewData(this.currentView);

            this.showToast('success', '刷新完成', '数据已更新');
        } catch (error) {
            console.error('❌ 强制刷新失败:', error);
            // 备用方案：使用原来的加载方法
            await this.loadInitialData();
            this.showToast('success', '刷新完成', '数据已更新（备用方案）');
        }
    }


    async exportAllData() {
        // 快速导出 - 使用之前保存的配置
        try {
            this.showLoading('正在执行快速导出...');
            
            if (!this.exportManager) {
                this.exportManager = new ExportManager(this.localDataManager, this.categoryManager);
            }
            
            const result = await this.exportManager.quickExport();
            
            this.hideLoading();
            this.showToast('success', '导出成功', 
                `文件：${result.filename}，共 ${result.recordCount} 条记录`);
            
        } catch (error) {
            this.hideLoading();
            console.error('❌ 快速导出失败:', error);
            this.showToast('error', '导出失败', error.message);
        }
    }

    openImportDialog() {
        this.showToast('info', '导入数据', '导入功能开发中...');
    }

    // 备份数据和清理缓存方法已移除

    openCategoryDialog(categoryId = null) {
        this.showToast('info', '分类管理', '分类编辑功能开发中...');
    }

    collectFilters() {
        // 筛选功能已移除
    }

    applyFilters() {
        if (this.currentView === 'products') {
            // 🎯 重置页码为第1页
            this.pagination.currentPage = 1;
            this.loadProductsData();
        }
    }

    resetFilters() {
        this.filters = {
            category: 'all'
        };

        this.applyFilters();
    }

    toggleSelectAll(checked) {
        document.querySelectorAll('.product-checkbox').forEach(checkbox => {
            checkbox.checked = checked;
            const productId = parseInt(checkbox.value);
            if (checked) {
                this.selectedProducts.add(productId);
            } else {
                this.selectedProducts.delete(productId);
            }
        });
    }

    toggleSelectAllAnomalies(checked) {
        document.querySelectorAll('.product-checkbox').forEach(checkbox => {
            // 只选择异常监控表格中的复选框
            if (checkbox.closest('#anomaliesTable')) {
                checkbox.checked = checked;
                const productId = parseInt(checkbox.value);
                if (checked) {
                    this.selectedProducts.add(productId);
                } else {
                    this.selectedProducts.delete(productId);
                }
            }
        });
    }

    /**
     * 表格排序功能
     */
    async sortTable(field) {
        console.log(`🔄 排序字段: ${field}`);

        // 切换排序方向
        if (this.sortState.field === field) {
            // 同一字段：切换方向
            this.sortState.direction = this.sortState.direction === 'desc' ? 'asc' : 'desc';
        } else {
            // 新字段：默认降序
            this.sortState.field = field;
            this.sortState.direction = 'desc';
        }

        // 🆕 根据当前视图选择不同的排序逻辑
        if (this.currentView === 'products') {
            // 商品管理视图排序
            await this.sortProductsTable(field);
        } else if (this.currentView === 'anomalies') {
            // 异常监控视图排序
            this.sortAnomaliesTable(field);
        }

        // 更新排序图标
        this.updateSortUI();
        console.log(`✅ 排序完成: ${field} ${this.sortState.direction}`);
    }

    /**
     * 🎯 应用排序到商品列表（通用排序方法）
     */
    applySortToProducts(products) {
        if (!products || products.length === 0) {
            console.warn('⚠️ 没有商品数据可排序');
            return;
        }

        const field = this.sortState.field;
        if (!field) {
            console.warn('⚠️ 没有排序字段');
            return;
        }

        console.log(`🔢 应用排序: ${field} ${this.sortState.direction}`);

        // 排序逻辑
        products.sort((a, b) => {
                let valueA, valueB;

                // 🆕 处理粉销比字段
                if (field === 'store_fan_sales_ratio') {
                    const followersA = a.additional_data?.store_followers || 0;
                    const followersB = b.additional_data?.store_followers || 0;
                    valueA = this.calculateFanSalesRatio(this.getStoreSales(a), followersA);
                    valueB = this.calculateFanSalesRatio(this.getStoreSales(b), followersB);
                } else if (field === 'product_fan_sales_ratio') {
                    const followersA = a.additional_data?.store_followers || 0;
                    const followersB = b.additional_data?.store_followers || 0;
                    valueA = this.calculateFanSalesRatio(this.getProductSales(a), followersA);
                    valueB = this.calculateFanSalesRatio(this.getProductSales(b), followersB);
                } else if (field === 'title') {
                    valueA = this.getProductName(a);
                    valueB = this.getProductName(b);
                    // 字符串比较
                    return this.sortState.direction === 'desc' ?
                        valueB.localeCompare(valueA) :
                        valueA.localeCompare(valueB);
                } else if (field === 'price') {
                    valueA = this.getProductPrice(a);
                    valueB = this.getProductPrice(b);
                } else if (field === 'sales') {
                    valueA = this.getProductSales(a);
                    valueB = this.getProductSales(b);
                } else if (field === 'store_sales') {
                    valueA = this.getStoreSales(a);
                    valueB = this.getStoreSales(b);
                } else if (field === 'store_followers') {
                    valueA = a.additional_data?.store_followers || 0;
                    valueB = b.additional_data?.store_followers || 0;
                } else if (field === 'recent_sales') {
                    valueA = a.additional_data?.recent_sales || 0;
                    valueB = b.additional_data?.recent_sales || 0;
                } else if (field === 'extracted_at') {
                    valueA = new Date(a.extracted_at || 0).getTime();
                    valueB = new Date(b.extracted_at || 0).getTime();
                } else {
                    valueA = Number(a[field]) || 0;
                    valueB = Number(b[field]) || 0;
                }

                // 🎯 关键：缺失数据(0)排在最后
                if (valueA === 0 && valueB !== 0) {
                    return 1;  // A排后面
                }
                if (valueA !== 0 && valueB === 0) {
                    return -1; // B排后面
                }

                // 都为0或都不为0，按正常排序
                return this.sortState.direction === 'desc' ?
                    valueB - valueA : // 降序：大到小
                    valueA - valueB;  // 升序：小到大
            });

        // 🎯 保存排序后的数据到缓存
        this.currentProducts = products;

        console.log(`✅ 排序完成，已缓存 ${products.length} 个商品`);
    }

    /**
     * 🆕 商品列表排序逻辑
     */
    async sortProductsTable(field) {
        try {
            // 获取当前筛选后的商品数据
            let products = await this.getFilteredProducts();

            if (!products || products.length === 0) {
                console.warn('⚠️ 没有商品数据可排序');
                return;
            }

            console.log(`🔢 商品排序前(前3个):`, products.slice(0, 3).map(p => ({
                name: this.getProductName(p),
                [field]: field
            })));

            // 🎯 应用排序
            this.applySortToProducts(products);

            // 重新渲染商品表格
            this.updateProductsTable(this.currentProducts);
            this.updatePagination(this.currentProducts.length);

        } catch (error) {
            console.error('❌ 商品排序失败:', error);
        }
    }

    /**
     * 异常监控排序逻辑（保持原有实现）
     */
    sortAnomaliesTable(field) {
        // 🎯 调试：检查数据状态
        console.log('🔍 currentAnomalies状态:', {
            exists: !!this.currentAnomalies,
            length: this.currentAnomalies?.length,
            firstItem: this.currentAnomalies?.[0],
            fieldValue: this.currentAnomalies?.[0]?.[field]
        });

        // 排序数据
        if (this.currentAnomalies && this.currentAnomalies.length > 0) {
            console.log(`🔢 排序前数据(前3个):`, this.currentAnomalies.slice(0, 3).map(item => ({
                productName: item.productName,
                [field]: item[field]
            })));

            this.currentAnomalies.sort((a, b) => {
                // 🎯 修复：支持多种字段名格式
                let valueA, valueB;

                if (field === 'sales_24h') {
                    valueA = Number(a.sales_24h || a.sales24h) || 0;
                    valueB = Number(b.sales_24h || b.sales24h) || 0;
                } else if (field === 'revenue_24h') {
                    valueA = Number(a.revenue_24h || a.revenue24h) || 0;
                    valueB = Number(b.revenue_24h || b.revenue24h) || 0;
                } else {
                    valueA = Number(a[field]) || 0;
                    valueB = Number(b[field]) || 0;
                }

                console.log(`🔢 比较: ${valueA} vs ${valueB} (字段: ${field})`);

                return this.sortState.direction === 'desc' ?
                    valueB - valueA : // 降序：大到小
                    valueA - valueB;  // 升序：小到大
            });

            console.log(`🔢 排序后数据(前3个):`, this.currentAnomalies.slice(0, 3).map(item => ({
                productName: item.productName,
                [field]: item[field]
            })));

            // 重新渲染表格
            this.renderSimpleAnomalyList(this.currentAnomalies);
        } else {
            console.warn('⚠️ 没有数据可排序');
        }
    }

    /**
     * 更新排序UI图标
     */
    updateSortUI() {
        // 清除所有排序样式
        document.querySelectorAll('.sortable').forEach(header => {
            header.classList.remove('sort-asc', 'sort-desc');
        });

        // 设置当前排序样式
        if (this.sortState.field) {
            const currentHeader = document.querySelector(`[data-sort="${this.sortState.field}"]`);
            if (currentHeader) {
                currentHeader.classList.add(`sort-${this.sortState.direction}`);
            }
        }
    }

    updateSelectAllState() {
        const checkboxes = document.querySelectorAll('.product-checkbox');
        const selectAllCheckbox = document.getElementById('selectAll');
        
        if (checkboxes.length === 0) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
            return;
        }
        
        const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
        
        if (checkedCount === 0) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        } else if (checkedCount === checkboxes.length) {
            selectAllCheckbox.checked = true;
            selectAllCheckbox.indeterminate = false;
        } else {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = true;
        }
    }

    updatePagination(totalItems) {
        this.pagination.totalItems = totalItems;
        const totalPages = Math.ceil(totalItems / this.pagination.pageSize);
        
        // 更新分页信息
        const startIndex = (this.pagination.currentPage - 1) * this.pagination.pageSize + 1;
        const endIndex = Math.min(this.pagination.currentPage * this.pagination.pageSize, totalItems);
        
        document.getElementById('pageStart').textContent = totalItems > 0 ? startIndex : 0;
        document.getElementById('pageEnd').textContent = endIndex;
        document.getElementById('totalCount').textContent = totalItems;
        
        // 更新按钮状态
        document.getElementById('prevPageBtn').disabled = this.pagination.currentPage <= 1;
        document.getElementById('nextPageBtn').disabled = this.pagination.currentPage >= totalPages;
        
        // 更新页码按钮
        this.updatePageNumbers(totalPages);
    }

    updatePageNumbers(totalPages) {
        const container = document.getElementById('pageNumbers');
        container.innerHTML = '';
        
        const currentPage = this.pagination.currentPage;
        let startPage = Math.max(1, currentPage - 2);
        let endPage = Math.min(totalPages, currentPage + 2);
        
        // 确保显示5个页码（如果可能的话）
        if (endPage - startPage < 4) {
            if (startPage === 1) {
                endPage = Math.min(totalPages, startPage + 4);
            } else if (endPage === totalPages) {
                startPage = Math.max(1, endPage - 4);
            }
        }
        
        for (let i = startPage; i <= endPage; i++) {
            const pageBtn = document.createElement('button');
            pageBtn.className = `page-number ${i === currentPage ? 'active' : ''}`;
            pageBtn.textContent = i;
            pageBtn.addEventListener('click', () => this.changePage(i));
            container.appendChild(pageBtn);
        }
    }

    changePage(page) {
        const totalPages = Math.ceil(this.pagination.totalItems / this.pagination.pageSize);
        if (page < 1 || page > totalPages) return;

        this.pagination.currentPage = page;
        if (this.currentView === 'products') {
            // 🎯 使用缓存的商品数据，避免重新加载导致排序丢失
            if (this.currentProducts && this.currentProducts.length > 0) {
                this.updateProductsTable(this.currentProducts);
                // 🎯 更新分页UI，确保页码按钮状态正确
                this.updatePagination(this.currentProducts.length);
            } else {
                // 如果缓存为空，重新加载数据
                this.loadProductsData();
            }
        }
    }

    selectCategory(categoryId) {
        console.log('🌲 分类树选择分类:', categoryId);

        // 🆕 使用统一的同步方法（双向同步）
        this.syncCategorySelection(categoryId, 'tree');

        // 原有逻辑已集成到 syncCategorySelection() 中
        // - 更新分类树高亮
        // - 同步下拉框选中状态
        // - 更新筛选条件
        // - 重新加载商品数据
    }

    selectCategoryCard(categoryId) {
        // 更新分类卡片选中状态
        document.querySelectorAll('.category-card').forEach(card => {
            card.classList.toggle('active', parseInt(card.dataset.categoryId) === categoryId);
        });
        
        this.selectedCategory = categoryId;
        // 加载分类详情到右侧面板
        this.loadCategoryDetail(categoryId);
    }

    async loadCategoryDetail(categoryId) {
        const panel = document.getElementById('categoryDetailPanel');
        
        try {
            const category = await this.categoryManager.getCategoryById(categoryId);
            const stats = await this.categoryManager.getCategoryStats(categoryId);
            
            panel.innerHTML = `
                <div class="detail-header">
                    <h3>${category.name}</h3>
                    <div class="detail-actions">
                        <button class="btn-secondary btn-small" data-action="edit-category" data-category-id="${categoryId}">
                            编辑
                        </button>
                        <button class="btn-secondary btn-small" data-action="delete-category" data-category-id="${categoryId}">
                            删除
                        </button>
                    </div>
                </div>
                <div class="detail-content">
                    <div class="detail-section">
                        <h4>基本信息</h4>
                        <div class="detail-item">
                            <span class="detail-label">描述:</span>
                            <span class="detail-value">${category.description || '无描述'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">创建时间:</span>
                            <span class="detail-value">${this.formatDate(category.createTime)}</span>
                        </div>
                    </div>
                    <div class="detail-section">
                        <h4>统计信息</h4>
                        <div class="detail-item">
                            <span class="detail-label">商品数量:</span>
                            <span class="detail-value">${stats.totalProducts}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">平均价格:</span>
                            <span class="detail-value">¥${stats.avgPrice?.toFixed(2) || '0.00'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">总销量:</span>
                            <span class="detail-value">${stats.totalSales?.toLocaleString() || '0'}</span>
                        </div>
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('加载分类详情失败:', error);
            panel.innerHTML = `
                <div class="error-state">
                    <div class="error-icon">❌</div>
                    <div class="error-text">加载分类详情失败</div>
                </div>
            `;
        }
    }

    // 商品操作方法（占位）

    async deleteProduct(productId) {
        if (confirm('确定要删除这个商品吗？')) {
            try {
                console.log(`🗑️ 开始删除商品: ${productId}`);
                
                // 在删除前获取商品信息，用于状态同步
                const productResult = await this.localDataManager.getProduct(productId);
                if (!productResult.success || !productResult.product) {
                    throw new Error('商品不存在');
                }
                
                const product = productResult.product;
                const categoryId = product.category_id;
                console.log(`📊 将删除分类 ${categoryId} 中的商品: ${product.product_name || productId}`);
                
                // 删除商品
                await this.localDataManager.deleteProduct(productId);
                console.log(`✅ 商品 ${productId} 已从数据库删除`);

                // ✅ 立即从异常监控列表中移除该商品（ultrathink 优化）
                if (this.latestAnomalyResults && this.latestAnomalyResults.anomalies) {
                    const beforeCount = this.latestAnomalyResults.anomalies.length;
                    this.latestAnomalyResults.anomalies = this.latestAnomalyResults.anomalies.filter(
                        anomaly => (anomaly.productId || anomaly.product_id) != productId
                    );
                    const afterCount = this.latestAnomalyResults.anomalies.length;
                    this.latestAnomalyResults.anomaliesFound = afterCount;

                    console.log(`📊 异常列表更新: ${beforeCount} → ${afterCount} 项`);

                    // 立即重新渲染异常列表
                    this.renderSimpleAnomalyList(this.latestAnomalyResults.anomalies);
                }

                this.showToast('success', '删除成功', '商品已从数据库删除，页面即将刷新...');

                // 使用状态同步管理器进行统一状态更新
                console.log(`🔄 开始状态同步，影响的分类: [${categoryId}]`);
                await this.stateSyncManager.syncProductState('delete', {
                    productId: parseInt(productId),
                    categoryIds: [categoryId], // 影响的分类ID列表
                    operation: 'delete',
                    productName: product.product_name || `商品_${productId}`
                });

                console.log(`✅ 商品删除流程完成: ${productId}`);

                // ⭐ ultrathink 核心优化：删除后自动刷新页面，确保所有统计数据更新
                setTimeout(() => {
                    console.log(`🔄 页面自动刷新，确保数据完全同步...`);
                    window.location.reload();
                }, 1000); // 1秒延迟，让用户看到成功提示
                
            } catch (error) {
                console.error(`❌ 删除商品失败 [${productId}]:`, error);
                this.showToast('error', '删除失败', error.message);
            }
        }
    }

    // 分类操作方法
    async editCategory(categoryId) {
        try {
            const category = await this.categoryManager.getCategoryById(parseInt(categoryId));
            if (!category) {
                this.showToast('error', '编辑失败', '分类不存在');
                return;
            }
            
            // 创建编辑对话框
            this.showCategoryEditDialog(category);
            
        } catch (error) {
            console.error('❌ 获取分类信息失败:', error);
            this.showToast('error', '编辑失败', error.message);
        }
    }

    async deleteCategory(categoryId) {
        if (confirm('确定要删除这个分类吗？分类下的商品将移至"未分类"。')) {
            try {
                await this.categoryManager.deleteCategory(parseInt(categoryId));
                this.showToast('success', '删除成功', '分类已删除');

                // 使用状态同步管理器进行统一状态更新
                await this.stateSyncManager.syncCategoryState('delete', {
                    categoryId: parseInt(categoryId),
                    operation: 'delete'
                });

                // 🔔 发送跨页面消息通知侧边栏更新分类列表
                if (this.componentBridge) {
                    this.componentBridge.broadcast('CATEGORIES_UPDATED', {
                        action: 'delete',
                        categoryId: parseInt(categoryId),
                        timestamp: Date.now()
                    });
                    console.log('📡 已发送分类删除通知到侧边栏');
                }
            } catch (error) {
                this.showToast('error', '删除失败', error.message);
            }
        }
    }

    showCategoryMenu(categoryId) {
        // 检查是否为默认分类（不能删除）
        const isDefault = parseInt(categoryId) === 1;

        const menuHtml = `
            <div class="category-menu-overlay" data-category-id="${categoryId}">
                <div class="category-menu">
                    <div class="category-menu-header">
                        <span>分类操作</span>
                        <button class="category-menu-close">&times;</button>
                    </div>
                    <div class="category-menu-body">
                        <button class="category-menu-item" data-action="edit-category" data-category-id="${categoryId}">
                            <span class="menu-icon">✏️</span>
                            <span>编辑分类</span>
                        </button>
                        ${!isDefault ? `
                        <button class="category-menu-item delete-item" data-action="delete-category" data-category-id="${categoryId}">
                            <span class="menu-icon">🗑️</span>
                            <span>删除分类</span>
                        </button>
                        ` : `
                        <button class="category-menu-item disabled" disabled>
                            <span class="menu-icon">🔒</span>
                            <span>默认分类不可删除</span>
                        </button>
                        `}
                    </div>
                </div>
            </div>
        `;

        // 移除已存在的菜单
        const existingMenu = document.querySelector('.category-menu-overlay');
        if (existingMenu) {
            existingMenu.remove();
        }

        // 添加新菜单到页面
        document.body.insertAdjacentHTML('beforeend', menuHtml);

        // 绑定关闭事件
        const overlay = document.querySelector('.category-menu-overlay');
        const closeBtn = overlay.querySelector('.category-menu-close');

        const closeMenu = () => {
            overlay.remove();
        };

        // 点击遮罩关闭
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                closeMenu();
            }
        });

        // 点击关闭按钮
        closeBtn.addEventListener('click', closeMenu);

        // ESC键关闭
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                closeMenu();
                document.removeEventListener('keydown', handleEscape);
            }
        };
        document.addEventListener('keydown', handleEscape);

        console.log(`📋 显示分类 ${categoryId} 的操作菜单`);
    }

    // 显示分类编辑对话框
    showCategoryEditDialog(category = null) {
        const isEdit = category !== null;
        const title = isEdit ? '编辑分类' : '新建分类';
        
        const dialogHtml = `
            <div class="modal-header">
                <h3 class="modal-title">${title}</h3>
                <button class="modal-close" id="modalCloseBtn">&times;</button>
            </div>
            <div class="modal-body">
                <form id="categoryForm" class="category-form">
                    <div class="form-group">
                        <label for="categoryName">分类名称 <span class="required">*</span></label>
                        <input type="text" id="categoryName" class="form-input" 
                               value="${category?.name || ''}" 
                               placeholder="请输入分类名称" 
                               maxlength="50" required>
                        <div class="form-help">最多50个字符</div>
                    </div>
                    
                    <div class="form-group">
                        <label for="categoryDescription">分类描述</label>
                        <textarea id="categoryDescription" class="form-textarea" 
                                  placeholder="请输入分类描述（可选）" 
                                  maxlength="200">${category?.description || ''}</textarea>
                        <div class="form-help">最多200个字符</div>
                    </div>
                    
                    <div class="form-group">
                        <label for="categoryColor">分类颜色</label>
                        <div class="color-picker">
                            <input type="color" id="categoryColor" class="color-input" 
                                   value="${category?.color || '#6366f1'}">
                            <div class="color-presets">
                                <button type="button" class="color-preset" data-color="#ef4444" style="background: #ef4444"></button>
                                <button type="button" class="color-preset" data-color="#f97316" style="background: #f97316"></button>
                                <button type="button" class="color-preset" data-color="#3b82f6" style="background: #3b82f6"></button>
                                <button type="button" class="color-preset" data-color="#10b981" style="background: #10b981"></button>
                                <button type="button" class="color-preset" data-color="#8b5cf6" style="background: #8b5cf6"></button>
                                <button type="button" class="color-preset" data-color="#06b6d4" style="background: #06b6d4"></button>
                                <button type="button" class="color-preset" data-color="#f59e0b" style="background: #f59e0b"></button>
                                <button type="button" class="color-preset" data-color="#84cc16" style="background: #84cc16"></button>
                            </div>
                        </div>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" id="modalCancelBtn">取消</button>
                <button type="button" class="btn btn-primary" id="modalSaveBtn" data-category-id="${category?.id || 'null'}">
                    ${isEdit ? '保存' : '创建'}
                </button>
            </div>
        `;
        
        this.showModal(dialogHtml);
        
        // 绑定颜色预设点击事件
        document.querySelectorAll('.color-preset').forEach(preset => {
            preset.addEventListener('click', (e) => {
                const color = e.target.dataset.color;
                document.getElementById('categoryColor').value = color;
            });
        });
        
        // 聚焦到名称输入框
        setTimeout(() => {
            document.getElementById('categoryName')?.focus();
        }, 100);
    }

    // 保存分类表单
    async saveCategoryForm(categoryId) {
        try {
            const nameInput = document.getElementById('categoryName');
            const descInput = document.getElementById('categoryDescription');
            const colorInput = document.getElementById('categoryColor');
            
            const name = nameInput.value.trim();
            const description = descInput.value.trim();
            const color = colorInput.value;
            
            // 验证输入
            if (!name) {
                this.showToast('warning', '验证失败', '分类名称不能为空');
                nameInput.focus();
                return;
            }
            
            if (name.length > 50) {
                this.showToast('warning', '验证失败', '分类名称不能超过50个字符');
                nameInput.focus();
                return;
            }
            
            this.showLoading('正在保存分类...');
            
            let result;
            if (categoryId && !isNaN(categoryId)) {
                // 编辑现有分类
                result = await this.categoryManager.updateCategory(parseInt(categoryId), {
                    name: name,
                    description: description,
                    color: color
                });
                this.showToast('success', '保存成功', `分类"${name}"已更新`);
            } else {
                // 创建新分类
                result = await this.categoryManager.createCategory(name, description, color);
                this.showToast('success', '创建成功', `分类"${name}"已创建`);
            }
            
            // 关闭对话框并刷新数据
            this.closeModal();
            
            // 使用状态同步管理器进行统一状态更新
            const syncAction = categoryId && !isNaN(categoryId) ? 'update' : 'create';
            await this.stateSyncManager.syncCategoryState(syncAction, {
                categoryId: result.id || result,
                categoryName: name,
                operation: syncAction
            });

            // 🔔 发送跨页面消息通知侧边栏更新分类列表
            if (this.componentBridge) {
                this.componentBridge.broadcast('CATEGORIES_UPDATED', {
                    action: syncAction,
                    categoryId: result.id || result,
                    categoryName: name,
                    timestamp: Date.now()
                });
                console.log(`📡 已发送分类${syncAction === 'create' ? '创建' : '更新'}通知到侧边栏`);
            }

            console.log('✅ 分类保存成功:', result);
            
        } catch (error) {
            console.error('❌ 保存分类失败:', error);
            this.showToast('error', '保存失败', error.message);
        } finally {
            this.hideLoading();
        }
    }

    // 新建分类入口
    async createNewCategory() {
        this.showCategoryEditDialog();
    }

    /**
     * 更新统计信息 - 统一数据源和计算方法
     */
    async updateStatistics() {
        try {
            // 获取真实的数据库统计，确保一致性
            const totalProductsFromDB = await this.localDataManager.getTotalProductCount();
            const categories = await this.categoryManager.getAllCategories();
            const totalTimeSeriesFields = await this.localDataManager.getTotalSnapshotCount();
            // ultrathink: 使用简化的is_anomaly标记而不是旧的anomalies表
            const anomalyProducts = await this.localDataManager.getAnomalyProducts();
            console.log('📊 [updateStatistics] 异常商品数量:', anomalyProducts.length);

            // 统计有数据的分类数量
            const categoriesWithData = categories.filter(cat => 
                (cat.product_count && cat.product_count > 0) || 
                this.localDataManager.getProductCountByCategory(cat.id) > 0
            ).length;
            
            // 更新侧边栏统计信息（使用直接数据库查询结果）
            const totalProductsElement = document.getElementById('totalProducts');
            const totalCategoriesElement = document.getElementById('totalCategories');
            const anomalyProductsElement = document.getElementById('anomalyProducts');
            const totalSnapshotsElement = document.getElementById('totalSnapshots');

            if (totalProductsElement) {
                totalProductsElement.textContent = totalProductsFromDB;
            }
            
            if (totalCategoriesElement) {
                totalCategoriesElement.textContent = categories.length;
            }
            
            if (anomalyProductsElement) {
                anomalyProductsElement.textContent = anomalyProducts.length;
                console.log('📊 [updateStatistics] 已更新侧边栏异常商品数量 (anomalyProducts):', anomalyProducts.length);
            }

            // ultrathink: 同时更新异常监控页面的计数元素
            const anomalyCountElement = document.getElementById('anomalyCount');
            if (anomalyCountElement) {
                anomalyCountElement.textContent = anomalyProducts.length;
                console.log('📊 [updateStatistics] 已更新异常监控页面计数 (anomalyCount):', anomalyProducts.length);
            } else {
                console.log('⚠️ [updateStatistics] 未找到 anomalyCount 元素');
            }

            if (totalSnapshotsElement) {
                totalSnapshotsElement.textContent = totalTimeSeriesFields;
                // 更新快照相关的标签文本
                const snapshotLabel = document.querySelector('label[for="totalSnapshots"]');
                if (snapshotLabel) {
                    snapshotLabel.textContent = '时间序列数据点';
                }
            }
            
            
            // 构建统一的统计对象
            const statistics = {
                totalProducts: totalProductsFromDB,
                totalCategories: categories.length,
                categoriesWithData: categoriesWithData,
                anomalyProducts: anomalyProducts.length,
                totalSnapshots: totalTimeSeriesFields,
            };
            
            console.log('✅ 统计信息更新完成:', statistics);
            
        } catch (error) {
            console.warn('⚠️ 统计信息更新失败:', error);
            // 不抛出错误，避免影响主流程
        }
    }

    // 模态对话框控制
    showModal(content) {
        const overlay = document.getElementById('modalOverlay');
        const modalContent = document.getElementById('modalContent');
        
        if (overlay && modalContent) {
            modalContent.innerHTML = content;
            overlay.classList.add('active');
            
            // 绑定模态框内的事件
            this.bindModalEvents();
            
            // ESC键关闭
            this.modalKeyHandler = (e) => {
                if (e.key === 'Escape') {
                    this.closeModal();
                }
            };
            document.addEventListener('keydown', this.modalKeyHandler);
        }
    }

    bindModalEvents() {
        // 绑定关闭按钮
        const closeBtn = document.getElementById('modalCloseBtn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeModal());
        }
        
        // 绑定取消按钮
        const cancelBtn = document.getElementById('modalCancelBtn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.closeModal());
        }
        
        // 绑定保存按钮
        const saveBtn = document.getElementById('modalSaveBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', (e) => {
                const categoryId = e.target.getAttribute('data-category-id');
                const parsedCategoryId = categoryId === 'null' ? null : parseInt(categoryId);
                this.saveCategoryForm(parsedCategoryId);
            });
        }
        
        // 绑定颜色预设按钮
        const colorPresets = document.querySelectorAll('.color-preset');
        colorPresets.forEach(preset => {
            preset.addEventListener('click', (e) => {
                e.preventDefault();
                const color = e.target.getAttribute('data-color');
                const colorInput = document.getElementById('categoryColor');
                if (colorInput && color) {
                    colorInput.value = color;
                }
            });
        });
    }

    closeModal() {
        const overlay = document.getElementById('modalOverlay');
        if (overlay) {
            overlay.classList.remove('active');
            
            // 移除ESC键监听
            if (this.modalKeyHandler) {
                document.removeEventListener('keydown', this.modalKeyHandler);
                this.modalKeyHandler = null;
            }
        }
    }

    // 异常监控数据加载和管理 - 使用简化异常检测
    async loadAnomaliesData() {
        console.log('🔍 加载简化异常监控数据...');

        try {
            // 检查是否有最新的检测结果
            if (this.latestAnomalyResults && this.latestAnomalyResults.anomalies.length > 0) {
                console.log('🎯 显示最新的异常检测结果，跳过数据库加载');
                this.displayAnomalyDetectionResults(this.latestAnomalyResults);
                return;
            }

            // 如果没有最新结果，从数据库加载已标记为异常的商品
            console.log('📊 没有最新检测结果，从数据库加载已标记为异常的商品...');
            const anomalyProducts = await this.sharedDataService.localDataManager.getAnomalyProducts();

            if (anomalyProducts && anomalyProducts.length > 0) {
                console.log(`🎯 从数据库加载到 ${anomalyProducts.length} 个异常商品`);

                // 转换数据库中的异常商品为渲染格式 - 使用正确的数据库字段映射 (ultrathink)
                const anomaliesForRender = await Promise.all(
                    anomalyProducts.map(async (product) => {
                        // 直接从商品数据解析字段名称，避免环境依赖 (ultrathink修复)
                        let fieldNames;

                        // 检查是否存在时间序列字段
                        const allKeys = Object.keys(product);
                        const timeSeriesFields = allKeys.filter(key =>
                            key.includes('商品销量（') || key.includes('店铺销量（') || key.includes('爬取时间（')
                        );

                        if (timeSeriesFields.length > 0) {
                            // 获取最新日期的时间序列字段（按日期排序取最新）
                            const latestSalesField = timeSeriesFields.filter(f => f.includes('商品销量')).sort().pop();
                            const latestStoreSalesField = timeSeriesFields.filter(f => f.includes('店铺销量')).sort().pop();
                            const latestCrawlTimeField = timeSeriesFields.filter(f => f.includes('爬取时间')).sort().pop();

                            // 提取最新日期
                            const latestDate = latestSalesField ? latestSalesField.match(/（(.+?)）/)?.[1] : null;

                            fieldNames = {
                                salesField: latestSalesField || '商品销量',
                                storeSalesField: latestStoreSalesField || '店铺销量',
                                crawlTimeField: latestCrawlTimeField || '更新时间',
                                isTimeSeries: true,
                                latestDate: latestDate,
                                salesValue: product[latestSalesField] || 0,
                                storeSalesValue: product[latestStoreSalesField] || 0,
                                crawlTimeValue: product[latestCrawlTimeField] || null
                            };
                            console.log(`✅ 商品 ${product.id} 使用时间序列字段:`, latestDate);
                        } else {
                            // 使用友好的基础字段名
                            fieldNames = {
                                salesField: '商品销量',
                                storeSalesField: '店铺销量',
                                crawlTimeField: '更新时间',
                                isTimeSeries: false,
                                salesValue: product.product_sales || 0,
                                storeSalesValue: product.store_sales || 0,
                                crawlTimeValue: product.extracted_at || null
                            };
                            console.log(`📊 商品 ${product.id} 使用基础字段`);
                        }

                        // 使用统一的字段获取方法，与商品列表保持一致 (ultrathink)
                        const productName = this.getProductName(product);
                        const productPrice = this.getProductPrice(product);
                        const productSales = this.getProductSales(product);
                        const storeSales = this.getStoreSales(product);
                        const categoryName = this.getCategoryName(product.category_id);

                        // 调试信息：检查数据字段和时间序列字段名 (ultrathink)
                        console.log(`🔍 异常商品 ${product.id} 数据解析:`, {
                            原始数据: product,
                            解析结果: {
                                productName,
                                productPrice,
                                productSales,
                                storeSales,
                                categoryName
                            },
                            字段名映射: fieldNames
                        });

                        // 特别检查时间序列字段名
                        if (fieldNames.isTimeSeries) {
                            console.log(`✅ 时间序列字段检测成功:`, {
                                销量字段: fieldNames.salesField,
                                店铺销量字段: fieldNames.storeSalesField,
                                爬取时间字段: fieldNames.crawlTimeField,
                                最新日期: fieldNames.latestDate
                            });
                        } else {
                            console.log(`📊 使用基础字段:`, {
                                销量字段: fieldNames.salesField,
                                店铺销量字段: fieldNames.storeSalesField,
                                爬取时间字段: fieldNames.crawlTimeField
                            });
                        }

                        return {
                            id: product.id,
                            productId: product.id,
                            productName: productName,
                            productPrice: productPrice,
                            categoryName: categoryName,
                            sales: productSales,
                            storeSales: storeSales,
                            crawlTime: product.extracted_at || product.updateTime,
                            sales24h: product['新增销量'] || product.sales_24h || product.product_sales_24h || 0,
                            revenue24h: product['新增销售额'] || product.revenue_24h || product.product_revenue_24h || 0,
                            isSalesAnomaly: product.is_sales_anomaly !== undefined ? product.is_sales_anomaly : true,
                            isRevenueAnomaly: product.is_revenue_anomaly !== undefined ? product.is_revenue_anomaly : true,
                            salesThreshold: product.sales_threshold || 50,
                            revenueThreshold: product.revenue_threshold || 500,
                            detectionTime: product.anomaly_updated_at || product.updated_at || new Date().toISOString(),
                            severity: 'warning',
                            type: 'persistent_anomaly',
                            description: '数据库中已标记的异常商品',
                            fieldNames: fieldNames
                        };
                    })
                );

                // 渲染异常列表
                this.renderSimpleAnomalyList(anomaliesForRender);
                console.log('✅ 成功显示数据库中的异常商品');

                // ultrathink: 显示导出按钮（数据库数据源）
                const exportBtn = document.getElementById('exportAnomalyResultsBtn');
                if (exportBtn) {
                    exportBtn.style.display = anomaliesForRender.length > 0 ? 'inline-block' : 'none';
                    console.log('🎯 导出按钮已显示，数据库异常商品数量:', anomaliesForRender.length);
                }
            } else {
                // 没有任何异常数据，显示空状态
                console.log('📊 数据库中也没有异常商品，显示空状态');
                this.renderSimpleAnomalyList([]);

                // ultrathink: 隐藏导出按钮（无数据状态）
                const exportBtn = document.getElementById('exportAnomalyResultsBtn');
                if (exportBtn) {
                    exportBtn.style.display = 'none';
                    console.log('🎯 导出按钮已隐藏，无异常数据');
                }
            }

            console.log('✅ 异常监控数据加载完成');

            // 更新侧边栏统计数据，确保异常商品数量显示正确
            await this.updateStatistics();

        } catch (error) {
            console.error('❌ 加载异常监控数据失败:', error);
            this.showToast('error', '加载失败', '无法加载异常监控数据: ' + error.message);
            // 发生错误时显示空状态
            this.renderSimpleAnomalyList([]);
        }
    }

    // 兼容性别名：确保旧的方法名也能正常工作
    async loadAnomalyMonitoringData() {
        console.log('🔄 调用兼容性别名，重定向到 loadAnomaliesData');
        return await this.loadAnomaliesData();
    }

    // 异常统计更新方法已移除
    
    // 渲染异常记录列表
    renderAnomalyList(anomalies) {
        // 重定向到简化异常列表渲染，确保统一显示格式
        console.log('🔄 重定向到简化异常列表渲染');
        this.renderSimpleAnomalyList(anomalies);
    }
    
    // 创建异常记录项
    createAnomalyItem(anomaly) {
        const severityClass = {
            'critical': 'critical',
            'warning': 'warning', 
            'info': 'info'
        }[anomaly.severity] || 'info';
        
        const severityIcon = {
            'critical': '🚨',
            'warning': '⚠️',
            'info': 'ℹ️'
        }[anomaly.severity] || 'ℹ️';
        
        const typeLabel = {
            'sales_spike': '销量激增',
            'revenue_spike': '销售额激增',
            'combined_spike': '销量/销售额双重激增'
        }[anomaly.type] || '未知异常';
        
        const detectedTime = new Date(anomaly.detected_at).toLocaleString('zh-CN');
        
        // 显示24小时增长数据
        const growthDataHtml = anomaly.sales_24h !== undefined || anomaly.revenue_24h !== undefined ? `
            <div class="anomaly-growth-data">
                <div class="growth-metrics">
                    ${anomaly.sales_24h !== undefined ? `
                        <div class="metric-item">
                            <span class="metric-label">24h新增销量:</span>
                            <span class="metric-value ${anomaly.sales_24h > 50 ? 'anomaly-value' : ''}">${anomaly.sales_24h}件</span>
                        </div>
                    ` : ''}
                    ${anomaly.revenue_24h !== undefined ? `
                        <div class="metric-item">
                            <span class="metric-label">24h新增销售额:</span>
                            <span class="metric-value ${anomaly.revenue_24h > 500 ? 'anomaly-value' : ''}">${anomaly.revenue_24h}元</span>
                        </div>
                    ` : ''}
                </div>
            </div>
        ` : '';

        return `
            <div class="anomaly-item ${severityClass}" data-id="${anomaly.id}">
                <div class="anomaly-header">
                    <div class="anomaly-severity">
                        <span class="severity-icon">${severityIcon}</span>
                        <span class="severity-text">${typeLabel}</span>
                    </div>
                    <div class="anomaly-time">${detectedTime}</div>
                </div>
                <div class="anomaly-product">
                    <strong>商品:</strong> ${anomaly.product_name || '未知商品'}
                </div>
                <div class="anomaly-description">${anomaly.description}</div>
                ${growthDataHtml}
                <!-- ultrathink: 移除旧的操作按钮，简化设计 -->
            </div>
        `;
    }

    // ultrathink: 删除旧的异常详情功能，使用简化设计
    // ultrathink: 删除旧的标记异常已解决功能，使用简化设计
    
    // ultrathink: 删除重复的异常检测方法，使用侧边栏触发的简化方案


    // ==================== 批量监控UI功能（数据展示） ====================

    /**
     * 打开批量监控对话框 - 只处理UI展示，实际监控由sidepanel执行
     */
    async openBatchMonitorDialog() {
        try {
            console.log('🔍 打开批量监控配置对话框...');
            
            // 通过ComponentBridge请求sidepanel打开批量监控
            if (this.componentBridge) {
                this.componentBridge.sendMessage('sidepanel', 'OPEN_BATCH_MONITOR_DIALOG', {
                    requestSource: 'data-manager'
                });
            } else {
                this.showToast('warning', '功能提示', '批量监控功能已迁移到侧边栏，请在侧边栏中操作');
            }
            
        } catch (error) {
            console.error('❌ 打开批量监控对话框失败:', error);
            this.showToast('error', '打开失败', '无法打开批量监控对话框');
        }
    }

    /**
     * 显示批量删除对话框
     */
    async showBatchDeleteDialog() {
        try {
            this.safeLog('🗑️ 显示批量删除对话框...');
            
            // 检查数据管理器是否已初始化
            if (!this.localDataManager) {
                this.safeError('❌ LocalDataManager 未初始化');
                this.showToast('error', '系统错误', '数据管理器未初始化，请刷新页面重试');
                return;
            }
            
            this.safeLog('📊 正在获取商品总数...');
            // 获取商品总数和分类信息
            const totalCount = await this.localDataManager.getTotalProductCount();
            this.safeLog(`📊 商品总数: ${totalCount}`);
            
            this.safeLog('📁 正在获取分类信息...');
            const categories = await this.categoryManager.getAllCategories();
            this.safeLog(`📁 分类总数: ${categories ? categories.length : 0}`);
            
            if (totalCount === 0) {
                this.safeLog('ℹ️ 没有商品数据可删除');
                this.showToast('info', '提示', '当前没有商品数据可删除');
                return;
            }
            
            this.safeLog('🔄 准备显示批量删除选择对话框...');
            // 显示分类选择对话框
            const deleteOptions = await this.showBatchDeleteSelectionDialog(totalCount, categories);
            
            if (deleteOptions) {
                this.safeLog('✅ 用户确认删除操作:', deleteOptions);
                await this.performBatchDelete(deleteOptions);
            } else {
                this.safeLog('❌ 用户取消删除操作');
            }
            
        } catch (error) {
            this.safeError('❌ 显示批量删除对话框失败:', error);
            this.showToast('error', '操作失败', '无法显示批量删除对话框: ' + error.message);
        }
    }

    /**
     * 显示批量删除选择对话框
     */
    async showBatchDeleteSelectionDialog(totalCount, categories) {
        return new Promise((resolve) => {
            this.safeLog('🔍 查找模态框元素...');
            const modal = document.getElementById('modalOverlay');
            const modalContent = document.getElementById('modalContent');
            
            this.safeLog('📋 模态框元素检查:');
            this.safeLog('  - modal存在:', !!modal);
            this.safeLog('  - modalContent存在:', !!modalContent);
            this.safeLog('  - modal当前display:', modal ? modal.style.display : 'modal不存在');
            
            if (!modal) {
                this.safeError('❌ 致命错误：找不到 #modalOverlay 元素');
                resolve(null);
                return;
            }
            
            if (!modalContent) {
                this.safeError('❌ 致命错误：找不到 #modalContent 元素');
                resolve(null);
                return;
            }
            
            // 构建分类选项HTML
            let categoryOptions = '';
            if (categories && categories.length > 0) {
                categoryOptions = categories.map(category => {
                    return `
                        <label class="category-option">
                            <input type="radio" name="deleteCategory" value="${category.id}" />
                            <span class="category-name">${category.name}</span>
                            <span class="category-count">(${category.product_count || 0} 件商品)</span>
                        </label>
                    `;
                }).join('');
            }
            
            modalContent.innerHTML = `
                <div class="modal-header">
                    <h3 class="modal-title">🗑️ 批量删除设置</h3>
                </div>
                <div class="modal-body">
                    <div class="delete-options">
                        <h4 class="option-title">请选择删除范围：</h4>
                        
                        <div class="delete-option-group">
                            <label class="delete-option">
                                <input type="radio" name="deleteType" value="all" checked />
                                <div class="option-content">
                                    <span class="option-name">🔥 删除全部商品</span>
                                    <span class="option-desc">删除所有 ${totalCount} 件商品数据</span>
                                </div>
                            </label>

                            ${categories && categories.length > 0 ? `
                            <label class="delete-option">
                                <input type="radio" name="deleteType" value="category" />
                                <div class="option-content">
                                    <span class="option-name">📁 按分类删除</span>
                                    <span class="option-desc">只删除指定分类下的商品</span>
                                </div>
                            </label>
                            ` : ''}

                            <label class="delete-option">
                                <input type="radio" name="deleteType" value="threshold" />
                                <div class="option-content">
                                    <span class="option-name">📉 24小时增长阈值删除</span>
                                    <span class="option-desc">删除新增销量和销售额都低于阈值的商品</span>
                                </div>
                            </label>
                        </div>
                        
                        ${categoryOptions ? `
                        <div class="category-selection" id="categorySelection" style="display: none;">
                            <h4 class="option-title">选择要删除的分类：</h4>
                            <div class="category-options">
                                ${categoryOptions}
                            </div>
                        </div>
                        ` : ''}

                        <div class="threshold-settings" id="thresholdSettings" style="display: none;">
                            <h4 class="option-title">设置删除阈值：</h4>
                            <div class="threshold-inputs">
                                <div class="input-row">
                                    <label>新增销量阈值：</label>
                                    <input type="number" id="salesThreshold" value="0" min="-100" step="1" />
                                    <span class="unit">件</span>
                                </div>
                                <div class="input-row">
                                    <label>新增销售额阈值：</label>
                                    <input type="number" id="revenueThreshold" value="0" min="-1000" step="1" />
                                    <span class="unit">元</span>
                                </div>
                                <div class="help-text">
                                    ⚠️ 将删除"新增销量 ≤ 阈值 且 新增销售额 ≤ 阈值"的商品
                                </div>
                            </div>
                        </div>

                        <div class="warning-message">
                            ⚠️ <strong>重要提示：</strong>删除操作不可撤销，建议先备份数据！
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" id="deleteCancel">取消</button>
                    <button type="button" class="btn btn-danger" id="deleteConfirm">确认删除</button>
                </div>
            `;
            
            // 绑定删除类型切换事件
            const deleteTypeRadios = modalContent.querySelectorAll('input[name="deleteType"]');
            const categorySelection = document.getElementById('categorySelection');
            const thresholdSettings = document.getElementById('thresholdSettings');

            deleteTypeRadios.forEach(radio => {
                radio.addEventListener('change', (e) => {
                    const value = e.target.value;

                    // 显示/隐藏分类选择
                    if (categorySelection) {
                        categorySelection.style.display = value === 'category' ? 'block' : 'none';
                    }

                    // 显示/隐藏阈值设置
                    if (thresholdSettings) {
                        thresholdSettings.style.display = value === 'threshold' ? 'block' : 'none';
                    }
                });
            });
            
            const handleConfirm = () => {
                const deleteType = modalContent.querySelector('input[name="deleteType"]:checked')?.value;
                let selectedCategoryId = null;
                let selectedCategoryName = '';
                let salesThreshold = 0;
                let revenueThreshold = 0;

                if (deleteType === 'category') {
                    const selectedCategory = modalContent.querySelector('input[name="deleteCategory"]:checked');
                    if (!selectedCategory) {
                        alert('请选择要删除的分类');
                        return;
                    }
                    selectedCategoryId = parseInt(selectedCategory.value);
                    selectedCategoryName = selectedCategory.parentNode.querySelector('.category-name').textContent;

                } else if (deleteType === 'threshold') {
                    // 获取阈值参数
                    salesThreshold = parseInt(document.getElementById('salesThreshold').value) || 0;
                    revenueThreshold = parseInt(document.getElementById('revenueThreshold').value) || 0;

                    // 简单验证
                    if (salesThreshold < -1000 || revenueThreshold < -10000) {
                        alert('阈值设置过低，请重新设置');
                        return;
                    }
                }

                modal.classList.remove('active');
                resolve({
                    type: deleteType,
                    categoryId: selectedCategoryId,
                    categoryName: selectedCategoryName,
                    salesThreshold: salesThreshold,
                    revenueThreshold: revenueThreshold
                });
                cleanup();
            };
            
            const handleCancel = () => {
                modal.classList.remove('active');
                resolve(null);
                cleanup();
            };
            
            const cleanup = () => {
                document.getElementById('deleteConfirm')?.removeEventListener('click', handleConfirm);
                document.getElementById('deleteCancel')?.removeEventListener('click', handleCancel);
                modal.removeEventListener('click', handleOutsideClick);
            };

            const handleOutsideClick = (e) => {
                if (e.target === modal) {
                    handleCancel();
                }
            };

            // ✅ 立即绑定事件 - 在HTML生成后马上绑定
            const bindDeleteEvents = () => {
                const deleteConfirmBtn = document.getElementById('deleteConfirm');
                const deleteCancelBtn = document.getElementById('deleteCancel');

                if (deleteConfirmBtn && deleteCancelBtn) {
                    // 移除可能存在的旧事件监听器
                    deleteConfirmBtn.replaceWith(deleteConfirmBtn.cloneNode(true));
                    deleteCancelBtn.replaceWith(deleteCancelBtn.cloneNode(true));

                    // 重新获取元素并绑定新事件
                    const newDeleteConfirmBtn = document.getElementById('deleteConfirm');
                    const newDeleteCancelBtn = document.getElementById('deleteCancel');

                    newDeleteConfirmBtn.addEventListener('click', handleConfirm);
                    newDeleteCancelBtn.addEventListener('click', handleCancel);
                    modal.addEventListener('click', handleOutsideClick);

                    // ⭐ ultrathink 修复：使用安全的console调用
                    this.safeLog('✅ 删除按钮事件重新绑定成功');
                    return true;
                } else {
                    // ⭐ ultrathink 修复：使用安全的console调用
                    this.safeWarn('⚠️ 删除按钮元素未找到，稍后重试...');
                    return false;
                }
            };

            // 立即尝试绑定，如果失败则重试
            if (!bindDeleteEvents()) {
                setTimeout(() => {
                    bindDeleteEvents();
                }, 100);
            }

            // 显示模态框
            if (modal) {
                modal.classList.add('active');
                this.safeLog('✅ 模态框已激活显示');
            } else {
                this.safeError('❌ 无法找到模态框元素 #modalOverlay');
                resolve(null);
                return;
            }
        });
    }

    /**
     * 执行批量删除操作
     */
    async performBatchDelete(deleteOptions) {
        try {
            this.safeLog('🗑️ 开始执行批量删除...', deleteOptions);
            
            let loadingText = '';
            let successMessage = '';
            
            if (deleteOptions.type === 'all') {
                loadingText = '正在删除所有商品数据，请稍候...';
                successMessage = '已成功删除所有商品数据';
                
                // 显示加载状态
                this.showLoading(loadingText);
                
                // 删除所有数据
                await this.localDataManager.clearAllData();
                
            } else if (deleteOptions.type === 'category') {
                loadingText = `正在删除分类"${deleteOptions.categoryName}"的商品数据...`;
                successMessage = `已成功删除分类"${deleteOptions.categoryName}"的商品数据`;

                // 显示加载状态
                this.showLoading(loadingText);

                // 获取该分类下的所有商品并删除
                const result = await this.localDataManager.getProducts(
                    deleteOptions.categoryId,
                    {},
                    { page: 1, limit: 10000 }
                );

                for (const product of result.products) {
                    await this.localDataManager.deleteProduct(product.id);
                }

            } else if (deleteOptions.type === 'threshold') {
                loadingText = `正在删除低增长商品（销量≤${deleteOptions.salesThreshold}，销售额≤${deleteOptions.revenueThreshold}）...`;

                // 显示加载状态
                this.showLoading(loadingText);

                // 执行阈值删除
                const deleteCount = await this.performThresholdDeletion(
                    deleteOptions.salesThreshold,
                    deleteOptions.revenueThreshold
                );

                successMessage = `已成功删除 ${deleteCount} 个低增长商品`;
            }
            
            // 刷新界面数据
            await this.loadInitialData();
            
            // 隐藏加载状态
            this.hideLoading();
            
            this.safeLog('✅ 批量删除完成');
            this.showToast('success', '删除成功', successMessage);
            
        } catch (error) {
            this.hideLoading();
            this.safeError('❌ 批量删除失败:', error);
            this.showToast('error', '删除失败', error.message || '批量删除操作失败');
        }
    }

    /**
     * 执行24小时增长阈值删除
     * @param {number} salesThreshold - 销量阈值
     * @param {number} revenueThreshold - 销售额阈值
     * @returns {number} 删除的商品数量
     */
    async performThresholdDeletion(salesThreshold, revenueThreshold) {
        this.safeLog(`🎯 开始执行阈值删除: 销量≤${salesThreshold}, 销售额≤${revenueThreshold}`);

        // 获取所有商品
        const allProducts = await this.localDataManager.getAllProducts();
        this.safeLog(`📦 获取到 ${allProducts.length} 个商品，开始筛选...`);

        // 筛选符合删除条件的商品
        const productsToDelete = [];
        let skippedProducts = 0; // 跳过的商品数量（没有增长数据）

        allProducts.forEach(product => {
            // 检查是否存在24小时增长数据字段
            const hasNewSalesField = product.hasOwnProperty("新增销量");
            const hasNewRevenueField = product.hasOwnProperty("新增销售额");

            // 如果没有增长数据字段，跳过该商品（不删除）
            if (!hasNewSalesField || !hasNewRevenueField) {
                skippedProducts++;
                return; // 跳过没有增长数据的商品
            }

            // 获取真实的增长数据值
            const newSales = product["新增销量"];
            const newRevenue = product["新增销售额"];

            // 同时满足两个条件才删除（AND逻辑）
            if (newSales <= salesThreshold && newRevenue <= revenueThreshold) {
                productsToDelete.push({
                    id: product.id,
                    product_id: product.product_id,
                    product_name: product.product_name,
                    newSales: newSales,
                    newRevenue: newRevenue
                });
            }
        });

        if (skippedProducts > 0) {
            this.safeLog(`⏭️ 跳过 ${skippedProducts} 个商品（没有24小时增长数据）`);
        }

        this.safeLog(`🎯 找到 ${productsToDelete.length} 个符合删除条件的商品:`);
        productsToDelete.forEach((product, index) => {
            this.safeLog(`  ${index + 1}. ${product.product_name || product.product_id} (销量:${product.newSales}, 销售额:${product.newRevenue})`);
        });

        // 批量删除
        let deleteCount = 0;
        for (const product of productsToDelete) {
            try {
                await this.localDataManager.deleteProduct(product.id);
                deleteCount++;
                this.safeLog(`✅ 已删除: ${product.product_name || product.product_id}`);
            } catch (error) {
                this.safeError(`❌ 删除失败: ${product.product_id}`, error);
            }
        }

        this.safeLog(`✅ 阈值删除完成: 成功删除 ${deleteCount}/${productsToDelete.length} 个商品`);
        return deleteCount;
    }

    /**
     * 显示确认对话框
     */
    async showConfirmDialog(title, message, options = {}) {
        return new Promise((resolve) => {
            const {
                confirmText = '确认',
                cancelText = '取消',
                confirmClass = 'btn-primary'
            } = options;
            
            const modal = document.getElementById('modalOverlay');
            const modalContent = document.getElementById('modalContent');
            
            modalContent.innerHTML = `
                <div class="modal-header">
                    <h3 class="modal-title">${title}</h3>
                </div>
                <div class="modal-body">
                    <div class="confirm-message">${message.replace(/\n/g, '<br>')}</div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" id="confirmCancel">${cancelText}</button>
                    <button type="button" class="btn ${confirmClass}" id="confirmOk">${confirmText}</button>
                </div>
            `;
            
            const handleConfirm = () => {
                modal.classList.remove('active');
                resolve(true);
                cleanup();
            };
            
            const handleCancel = () => {
                modal.classList.remove('active');
                resolve(false);
                cleanup();
            };
            
            const cleanup = () => {
                document.getElementById('confirmOk')?.removeEventListener('click', handleConfirm);
                document.getElementById('confirmCancel')?.removeEventListener('click', handleCancel);
                modal.removeEventListener('click', handleOutsideClick);
            };
            
            const handleOutsideClick = (e) => {
                if (e.target === modal) {
                    handleCancel();
                }
            };
            
            // 绑定事件
            document.getElementById('confirmOk').addEventListener('click', handleConfirm);
            document.getElementById('confirmCancel').addEventListener('click', handleCancel);
            modal.addEventListener('click', handleOutsideClick);
            
            // 显示模态框
            modal.style.display = 'flex';
        });
    }

    // 异常检测运行方法已移除
    
    /**
     * 初始化ComponentBridge通信
     */
    initializeComponentBridge() {
        if (window.getComponentBridge) {
            this.componentBridge = window.getComponentBridge();

            // 注册监控进度消息监听器
            this.componentBridge.onMessage('MONITORING_PROGRESS', (data) => {
                this.handleMonitoringProgress(data);
            });

            // 注册监控状态消息监听器
            this.componentBridge.onMessage('MONITORING_STARTED', (data) => {
                this.handleMonitoringStarted(data);
            });

            this.componentBridge.onMessage('MONITORING_COMPLETED', (data) => {
                this.handleMonitoringCompleted(data);
            });

            this.componentBridge.onMessage('MONITORING_STOPPED', (data) => {
                this.handleMonitoringStopped(data);
            });

            this.componentBridge.onMessage('ANOMALY_DETECTED', (data) => {
                this.handleAnomalyDetected(data);
            });

            this.componentBridge.onMessage('ANOMALY_DETECTION_FAILED', (data) => {
                this.handleAnomalyDetectionFailed(data);
            });

            this.componentBridge.onMessage('ANOMALY_DETECTION_COMPLETED', (data) => {
                console.log('📨 数据管理器收到异常检测完成消息:', data);
                this.handleAnomalyDetectionCompleted(data);
            });

            // 🆕 新增：注册状态同步消息监听器
            this.componentBridge.onMessage('STATE_SYNC_REQUEST', (data) => {
                this.safeLog('📥 收到状态同步请求:', data);
                this.handleStateSyncRequest(data);
            });

            console.log('✅ ComponentBridge 通信已建立');
            console.log('🔗 异常检测完成消息监听器已注册');
            console.log('🔗 状态同步消息监听器已注册');
        } else {
            console.warn('⚠️ ComponentBridge不可用，使用全局方法监听');

            // 全局方法监听备用方案
            window.receiveAnomalyDetectionResults = (data) => {
                console.log('📨 通过全局方法收到异常检测结果:', data);
                this.handleAnomalyDetectionCompleted(data);
            };
        }
    }
    
    /**
     * 处理监控进度更新 - 纯UI展示
     */
    handleMonitoringProgress(data) {
        console.log('📊 收到监控进度更新:', data);
        this.showToast('info', '监控进度', 
            `进度: ${data.processedProducts}/${data.totalProducts} (${data.percentage}%)`);
    }
    
    /**
     * 处理监控开始 - 纯UI展示
     */
    handleMonitoringStarted(data) {
        console.log('🚀 收到监控开始通知:', data);
        this.showToast('info', '批量监控', `批量监控已开始，共 ${data.totalProducts} 件商品`);
    }
    
    /**
     * 处理监控完成 - 纯UI展示
     */
    async handleMonitoringCompleted(data) {
        console.log('✅ 收到监控完成通知:', data);
        this.showToast('success', '监控完成', 
            `监控完成！成功: ${data.successCount}, 失败: ${data.errorCount}`);
        
        // 使用状态同步管理器进行统一状态更新
        try {
            await this.stateSyncManager.syncProductState('monitor_complete', {
                successCount: data.successCount,
                errorCount: data.errorCount,
                categoryCount: data.categoryCount || 0,
                operation: 'monitor_complete'
            });
        } catch (error) {
            console.error('❌ 监控完成状态同步失败:', error);
            // 备用方案：使用原来的刷新方法
            this.loadInitialData();
        }
    }
    
    /**
     * 处理监控停止 - 纯UI展示
     */
    handleMonitoringStopped(data) {
        console.log('⏹️ 收到监控停止通知:', data);
        this.showToast('warning', '监控停止', '批量监控已停止');
    }
    
    /**
     * 处理异常检测结果 - 纯UI展示
     */
    handleAnomalyDetected(anomaly) {
        console.log('⚠️ 收到异常检测通知:', anomaly);
        
        // 根据异常严重程度显示不同的提示
        const toastType = {
            'critical': 'error',
            'warning': 'warning', 
            'info': 'info'
        }[anomaly.severity] || 'warning';
        
        this.showToast(toastType, '异常检测', `检测到${anomaly.severity}异常: ${anomaly.description}`);
        
        // 刷新异常数据显示
        this.loadAnomaliesData();
    }
    
    /**
     * 处理异常检测失败 - 纯UI展示
     */
    handleAnomalyDetectionFailed(data) {
        console.log('❌ 收到异常检测失败通知:', data);
        this.showToast('error', '异常检测失败', `异常检测过程中发生错误: ${data.error}`);
    }

    /**
     * 处理异常检测完成 - 展示结果
     */
    async handleAnomalyDetectionCompleted(data) {
        console.log('✅ 收到异常检测完成通知:', data);

        try {
            const result = data.result;

            // 显示成功提示
            this.showToast('success', '异常检测完成',
                `检测完成：检查了 ${result.checkedCount} 个商品，发现 ${result.anomaliesFound} 个异常`);

            // 切换到异常监控标签页
            this.switchView('anomalies');

            // 展示检测结果
            this.displayAnomalyDetectionResults(result);

        } catch (error) {
            console.error('❌ 处理异常检测结果失败:', error);
            this.showToast('error', '处理失败', '无法显示异常检测结果');
        }
    }

    /**
     * 🆕 新增：处理状态同步请求
     */
    async handleStateSyncRequest(data) {
        try {
            this.safeLog('📥 处理状态同步请求:', data);

            const { operation, data: syncData } = data;

            // 根据操作类型执行相应的状态同步
            switch (operation) {
                case 'excel_upload_completed':
                    await this.handleExcelUploadSync(syncData);
                    break;

                case 'category_created':
                    await this.handleCategoryCreatedSync(syncData);
                    break;

                case 'product_data_updated':
                    await this.handleProductDataUpdatedSync(syncData);
                    break;

                case 'anomaly_detection_updated':
                    await this.handleAnomalyDetectionUpdatedSync(syncData);
                    break;

                case 'batch_monitoring_completed':
                    await this.handleBatchMonitoringCompletedSync(syncData);
                    break;

                default:
                    this.safeLog('⚠️ 未知的状态同步操作类型:', operation);
            }

            this.safeLog('✅ 状态同步处理完成');

        } catch (error) {
            this.safeError('❌ 状态同步处理失败:', error);
        }
    }

    /**
     * 🆕 处理Excel上传完成同步
     */
    async handleExcelUploadSync(data) {
        this.safeLog('📊 处理Excel上传状态同步:', data);

        if (this.stateSyncManager && data.categoryId) {
            await this.stateSyncManager.syncProductState('batch_import', {
                categoryIds: [data.categoryId],
                successCount: data.successCount || 0,
                operation: 'excel_upload'
            });
        }

        this.showToast('success', '数据同步',
            `Excel导入数据已同步：${data.successCount || 0} 条记录`);
    }

    /**
     * 🆕 处理分类创建同步
     */
    async handleCategoryCreatedSync(data) {
        this.safeLog('📁 处理分类创建状态同步:', data);

        if (this.stateSyncManager) {
            await this.stateSyncManager.syncCategoryState('create', {
                categoryId: data.categoryId,
                categoryName: data.categoryName,
                operation: 'create'
            });
        }

        this.showToast('success', '数据同步',
            `分类"${data.categoryName}"已同步到数据管理器`);
    }

    /**
     * 🆕 处理商品数据更新同步
     */
    async handleProductDataUpdatedSync(data) {
        this.safeLog('📦 处理商品数据更新状态同步:', data);

        if (this.stateSyncManager && data.categoryIds) {
            await this.stateSyncManager.syncProductState('update', {
                categoryIds: data.categoryIds,
                operation: data.operation || 'update',
                affectedCategories: data.affectedCategories || data.categoryIds.length
            });
        }

        this.showToast('info', '数据同步',
            `商品数据已同步，影响 ${data.affectedCategories || 0} 个分类`);
    }

    /**
     * 🆕 处理异常检测更新同步
     */
    async handleAnomalyDetectionUpdatedSync(data) {
        this.safeLog('⚠️ 处理异常检测更新状态同步:', data);

        // 刷新异常数据显示
        await this.loadAnomaliesData();

        this.showToast('info', '数据同步',
            `异常检测数据已同步：${data.anomaliesCount || 0} 个异常`);
    }

    /**
     * 🆕 处理批量监控完成同步
     */
    async handleBatchMonitoringCompletedSync(data) {
        this.safeLog('🎯 处理批量监控完成状态同步:', data);

        if (this.stateSyncManager) {
            await this.stateSyncManager.syncProductState('monitor_complete', {
                successCount: data.successCount || 0,
                errorCount: data.errorCount || 0,
                categoryCount: data.affectedCategories || 0,
                operation: 'batch_monitoring'
            });
        }

        this.showToast('success', '数据同步',
            `批量监控数据已同步：成功 ${data.successCount || 0}，失败 ${data.errorCount || 0}`);
    }

    /**
     * 展示异常检测结果
     */
    async displayAnomalyDetectionResults(result) {
        // 异常统计更新已移除

        // 转换检测结果为渲染格式，并预先获取字段名称
        const anomaliesForRender = await Promise.all(
            result.anomalies.map(async (anomaly) => {
                // 获取具体的数据库字段名称
                const fieldNames = await this.getProductFieldNames(anomaly);

                return {
                    id: anomaly.product_id,
                    productId: anomaly.product_id,
                    productName: anomaly.product_name,
                    productPrice: anomaly.product_price,
                    categoryName: anomaly.category_name,
                    sales: anomaly.current_sales,
                    storeSales: anomaly.store_sales,
                    crawlTime: anomaly.crawl_time || anomaly.extracted_at,
                    sales24h: anomaly['新增销量'] || anomaly.sales_24h || 0,
                    revenue24h: anomaly['新增销售额'] || anomaly.revenue_24h || 0,
                    isSalesAnomaly: anomaly.is_sales_anomaly,
                    isRevenueAnomaly: anomaly.is_revenue_anomaly,
                    salesThreshold: anomaly.sales_threshold,
                    revenueThreshold: anomaly.revenue_threshold,
                    detectionTime: result.detectionTime,
                    severity: 'warning', // 简化版统一使用warning级别
                    type: [
                        anomaly.is_sales_anomaly ? 'sales_spike' : '',
                        anomaly.is_revenue_anomaly ? 'revenue_spike' : ''
                    ].filter(Boolean).join(','),
                    description: [
                        anomaly.is_sales_anomaly ? `销量异常(${anomaly.sales_24h}>${anomaly.sales_threshold})` : '',
                        anomaly.is_revenue_anomaly ? `销售额异常(${anomaly.revenue_24h}>${anomaly.revenue_threshold})` : ''
                    ].filter(Boolean).join(', '),
                    // 预先获取的字段名称
                    fieldNames: fieldNames
                };
            })
        );

        // 渲染异常列表
        this.renderSimpleAnomalyList(anomaliesForRender);

        // 保存最新的检测结果供导出使用
        this.latestAnomalyResults = result;

        console.log('✅ 异常检测结果已展示');

        // 显示导出按钮
        const exportBtn = document.getElementById('exportAnomalyResultsBtn');
        if (exportBtn) {
            exportBtn.style.display = result.anomaliesFound > 0 ? 'inline-block' : 'none';
        }

        // ultrathink: 更新统计数据，确保仪表板显示最新的异常数量
        await this.updateStatistics();
    }

    /**
     * 导出异常检测结果 - ultrathink: 使用ExportManager完整功能
     */
    async exportAnomalyResults() {
        try {
            console.log('📊 开始导出异常商品数据...');

            // 1. 获取异常商品数据
            let anomalyProducts = [];

            // 优先使用最新检测结果，否则从数据库获取
            if (this.latestAnomalyResults && this.latestAnomalyResults.anomalies.length > 0) {
                anomalyProducts = this.latestAnomalyResults.anomalies;
                console.log('📊 使用最新检测结果:', anomalyProducts.length, '个异常商品');
            } else {
                console.log('📊 从数据库获取异常商品...');
                anomalyProducts = await this.sharedDataService.localDataManager.getAnomalyProducts();
                console.log('📊 从数据库获取到', anomalyProducts.length, '个异常商品');
            }

            if (!anomalyProducts || anomalyProducts.length === 0) {
                this.showToast('warning', '无数据', '没有异常数据可导出');
                return;
            }

            // 2. 初始化ExportManager
            if (!this.exportManager) {
                this.exportManager = new ExportManager(this.localDataManager, this.categoryManager);
            }

            // 3. 配置导出参数 - 包含所有字段和时间序列数据
            const exportConfig = {
                exportType: 'custom',
                selectedFields: [
                    // 基础字段
                    'id', 'product_id', 'product_name', 'product_url', 'product_price',
                    'product_sales', 'store_sales', 'store_name', 'category_name',

                    // 时间字段
                    'extracted_at',

                    // 额外数据字段
                    'good_reviews', 'cart_count', 'recent_sales', 'store_followers', 'notes',

                    // 增长数据字段
                    '新增销量', '新增销售额', '增长置信度', '增长计算时间', '增长计算间隔'
                ],
                selectedCategories: [],
                includeTimeSeriesData: true, // 关键：启用时间序列数据
                filename: `异常商品完整数据含时间序列_${new Date().toISOString().slice(0, 16).replace(/[:.]/g, '')}.xlsx`,
                dateFormat: 'YYYY-MM-DD',
                includeHeaders: true
            };

            // 4. 临时修改ExportManager的getExportData方法以返回异常商品
            const originalGetExportData = this.exportManager.getExportData.bind(this.exportManager);
            this.exportManager.getExportData = async () => {
                // 获取分类信息用于关联
                const categories = await this.categoryManager.getAllCategories();
                const categoryMap = new Map(categories.map(cat => [cat.id, cat.name]));

                return {
                    products: anomalyProducts,
                    categoryMap: categoryMap,
                    totalCount: anomalyProducts.length
                };
            };

            // 5. 执行导出
            console.log('📤 使用ExportManager导出异常商品数据...');
            const result = await this.exportManager.exportToExcel(exportConfig);

            // 6. 恢复原始方法
            this.exportManager.getExportData = originalGetExportData;

            // 7. 显示成功消息
            this.showToast('success', '导出成功',
                `异常商品完整数据已导出：${anomalyProducts.length} 个异常商品，包含完整时间序列数据`);

            console.log('✅ 异常商品导出成功:', result);

        } catch (error) {
            console.error('❌ 导出异常商品失败:', error);
            this.showToast('error', '导出失败', `导出失败: ${error.message}`);
        }
    }

    /**
     * 格式化时间显示
     */
    formatTime(timeString) {
        try {
            const date = new Date(timeString);
            return date.toLocaleString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } catch (error) {
            return timeString || '未知时间';
        }
    }

    /**
     * 渲染简化异常检测结果列表 - 表格形式
     */
    renderSimpleAnomalyList(anomalies) {
        // 🆕 保存完整原始数据（如果还未保存）
        if (this.originalAnomalies.length === 0 && anomalies.length > 0) {
            this.originalAnomalies = [...anomalies];
            console.log('💾 保存原始异常数据:', this.originalAnomalies.length);

            // 初始化分类选项
            this.loadCategoryFilterOptions();
        }

        // 🎯 修复：保存数据到实例变量，供排序使用
        this.currentAnomalies = anomalies;
        console.log('💾 保存数据到 currentAnomalies:', anomalies.length, '个异常商品');

        const tableBody = document.getElementById('anomaliesTableBody');
        const emptyState = document.getElementById('anomalyEmptyState');
        const tableWrapper = document.querySelector('.data-table-wrapper');
        const countElement = document.getElementById('anomalyCount');

        if (!tableBody) return;

        // 更新数量
        if (countElement) {
            countElement.textContent = anomalies.length;
        }

        // 🆕 控制筛选区域显示/隐藏
        const filterBar = document.querySelector('.anomaly-filter-bar');

        if (anomalies.length === 0) {
            // 隐藏表格和筛选区域，显示空状态
            if (tableWrapper) tableWrapper.style.display = 'none';
            if (emptyState) emptyState.style.display = 'block';
            if (filterBar) filterBar.style.display = 'none';
            // 隐藏分页控件
            this.renderAnomalyPagination(0, 0);
            return;
        }

        // 显示表格和筛选区域，隐藏空状态
        if (tableWrapper) tableWrapper.style.display = 'block';
        if (emptyState) emptyState.style.display = 'none';
        if (filterBar) filterBar.style.display = 'flex';

        // ultrathink: 更新表头显示实际字段名称
        this.updateAnomalyTableHeaders(anomalies);

        // 🆕 分页逻辑
        const totalItems = anomalies.length;
        const pageSize = this.anomalyPagination.pageSize;
        const totalPages = Math.ceil(totalItems / pageSize);

        // 确保当前页在有效范围内
        if (this.anomalyPagination.currentPage > totalPages && totalPages > 0) {
            this.anomalyPagination.currentPage = totalPages;
        }
        if (this.anomalyPagination.currentPage < 1) {
            this.anomalyPagination.currentPage = 1;
        }

        // 更新分页状态
        this.anomalyPagination.totalItems = totalItems;
        this.anomalyPagination.totalPages = totalPages;

        // 计算当前页的数据范围
        const startIndex = (this.anomalyPagination.currentPage - 1) * pageSize;
        const endIndex = Math.min(startIndex + pageSize, totalItems);
        const currentPageData = anomalies.slice(startIndex, endIndex);

        console.log(`📄 分页信息: 第${this.anomalyPagination.currentPage}/${totalPages}页, 显示${startIndex + 1}-${endIndex}/${totalItems}条`);

        // 渲染当前页的异常检测结果表格行
        const anomaliesHtml = currentPageData.map(anomaly => this.createAnomalyTableRow(anomaly)).join('');
        tableBody.innerHTML = anomaliesHtml;

        // 渲染分页控件
        this.renderAnomalyPagination(this.anomalyPagination.currentPage, totalPages);
    }

    /**
     * 🆕 渲染异常监控分页控件
     */
    renderAnomalyPagination(currentPage, totalPages) {
        const paginationContainer = document.getElementById('anomalyPaginationContainer');
        const paginationInfo = document.getElementById('anomalyPaginationInfo');
        const paginationPages = document.getElementById('anomalyPaginationPages');

        if (!paginationContainer) return;

        // 如果没有数据，隐藏分页控件
        if (totalPages === 0) {
            paginationContainer.style.display = 'none';
            return;
        }

        // 显示分页控件
        paginationContainer.style.display = 'flex';

        // 更新分页信息
        const startIndex = (currentPage - 1) * this.anomalyPagination.pageSize + 1;
        const endIndex = Math.min(currentPage * this.anomalyPagination.pageSize, this.anomalyPagination.totalItems);
        if (paginationInfo) {
            paginationInfo.textContent = `显示 ${startIndex}-${endIndex} / 共 ${this.anomalyPagination.totalItems} 条`;
        }

        // 渲染页码按钮
        if (paginationPages) {
            const pageButtons = this.generatePageButtons(currentPage, totalPages);
            paginationPages.innerHTML = pageButtons;
        }

        // 更新跳转输入框的最大值
        const pageJumpInput = document.getElementById('anomalyPageJump');
        if (pageJumpInput) {
            pageJumpInput.max = totalPages;
            pageJumpInput.value = '';
            pageJumpInput.placeholder = `1-${totalPages}`;
        }

        // 更新按钮状态
        this.updatePaginationButtonStates(currentPage, totalPages);

        // 绑定事件（只绑定一次）
        if (!this.anomalyPaginationEventsbound) {
            this.bindAnomalyPaginationEvents();
            this.anomalyPaginationEventsbound = true;
        }
    }

    /**
     * 🆕 生成页码按钮HTML
     */
    generatePageButtons(currentPage, totalPages) {
        const buttons = [];
        const maxVisiblePages = 5; // 最多显示5个页码按钮

        let startPage, endPage;

        if (totalPages <= maxVisiblePages) {
            // 如果总页数小于等于最大可见页数，显示所有页码
            startPage = 1;
            endPage = totalPages;
        } else {
            // 否则，计算可见页码范围
            const halfVisible = Math.floor(maxVisiblePages / 2);
            startPage = Math.max(1, currentPage - halfVisible);
            endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

            // 调整startPage，确保显示maxVisiblePages个页码
            if (endPage - startPage + 1 < maxVisiblePages) {
                startPage = Math.max(1, endPage - maxVisiblePages + 1);
            }
        }

        // 生成页码按钮
        for (let i = startPage; i <= endPage; i++) {
            const activeClass = i === currentPage ? 'active' : '';
            buttons.push(`
                <button class="page-number-btn ${activeClass}" data-page="${i}">
                    ${i}
                </button>
            `);
        }

        return buttons.join('');
    }

    /**
     * 🆕 更新分页按钮状态
     */
    updatePaginationButtonStates(currentPage, totalPages) {
        const firstPageBtn = document.getElementById('anomalyFirstPage');
        const prevPageBtn = document.getElementById('anomalyPrevPage');
        const nextPageBtn = document.getElementById('anomalyNextPage');
        const lastPageBtn = document.getElementById('anomalyLastPage');

        // 更新首页和上一页按钮
        if (firstPageBtn) {
            firstPageBtn.disabled = currentPage === 1;
        }
        if (prevPageBtn) {
            prevPageBtn.disabled = currentPage === 1;
        }

        // 更新下一页和末页按钮
        if (nextPageBtn) {
            nextPageBtn.disabled = currentPage === totalPages;
        }
        if (lastPageBtn) {
            lastPageBtn.disabled = currentPage === totalPages;
        }
    }

    /**
     * 🆕 绑定异常监控分页事件
     */
    bindAnomalyPaginationEvents() {
        // 首页按钮
        const firstPageBtn = document.getElementById('anomalyFirstPage');
        if (firstPageBtn) {
            firstPageBtn.addEventListener('click', () => this.goToAnomalyPage(1));
        }

        // 上一页按钮
        const prevPageBtn = document.getElementById('anomalyPrevPage');
        if (prevPageBtn) {
            prevPageBtn.addEventListener('click', () => {
                this.goToAnomalyPage(this.anomalyPagination.currentPage - 1);
            });
        }

        // 下一页按钮
        const nextPageBtn = document.getElementById('anomalyNextPage');
        if (nextPageBtn) {
            nextPageBtn.addEventListener('click', () => {
                this.goToAnomalyPage(this.anomalyPagination.currentPage + 1);
            });
        }

        // 末页按钮
        const lastPageBtn = document.getElementById('anomalyLastPage');
        if (lastPageBtn) {
            lastPageBtn.addEventListener('click', () => {
                this.goToAnomalyPage(this.anomalyPagination.totalPages);
            });
        }

        // 页码按钮（使用事件委托）
        const paginationPages = document.getElementById('anomalyPaginationPages');
        if (paginationPages) {
            paginationPages.addEventListener('click', (e) => {
                const pageBtn = e.target.closest('.page-number-btn');
                if (pageBtn) {
                    const page = parseInt(pageBtn.dataset.page);
                    this.goToAnomalyPage(page);
                }
            });
        }

        // 页面跳转
        const pageJumpBtn = document.getElementById('anomalyPageJumpBtn');
        const pageJumpInput = document.getElementById('anomalyPageJump');
        if (pageJumpBtn && pageJumpInput) {
            pageJumpBtn.addEventListener('click', () => {
                const page = parseInt(pageJumpInput.value);
                if (page && page >= 1 && page <= this.anomalyPagination.totalPages) {
                    this.goToAnomalyPage(page);
                    pageJumpInput.value = '';
                }
            });

            // 支持回车键跳转
            pageJumpInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    pageJumpBtn.click();
                }
            });
        }
    }

    /**
     * 🆕 跳转到指定页码
     */
    goToAnomalyPage(page) {
        const totalPages = this.anomalyPagination.totalPages;

        // 确保页码在有效范围内
        if (page < 1 || page > totalPages) {
            return;
        }

        // 更新当前页
        this.anomalyPagination.currentPage = page;

        // 重新渲染列表
        this.renderSimpleAnomalyList(this.currentAnomalies);

        // 滚动到表格顶部
        const anomaliesTable = document.getElementById('anomaliesTable');
        if (anomaliesTable) {
            anomaliesTable.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    /**
     * 更新异常监控表头显示实际字段名称 - ultrathink
     */
    updateAnomalyTableHeaders(anomalies) {
        try {
            // 如果没有异常数据，使用默认表头
            if (!anomalies || anomalies.length === 0) {
                this.resetAnomalyTableHeaders();
                return;
            }

            // 从第一个异常数据获取字段名信息
            const firstAnomaly = anomalies[0];
            const fieldNames = firstAnomaly.fieldNames;

            if (!fieldNames) {
                console.log('⚠️ 第一个异常商品没有字段名信息，使用默认表头');
                this.resetAnomalyTableHeaders();
                return;
            }

            // 查找表头元素
            const salesFieldHeader = document.querySelector('th[data-sort="sales_field"]');
            const storeSalesFieldHeader = document.querySelector('th[data-sort="store_sales_field"]');
            const crawlTimeFieldHeader = document.querySelector('th[data-sort="crawl_time_field"]');

            // 更新表头文本
            if (salesFieldHeader && fieldNames.salesField) {
                const displayName = fieldNames.salesField && fieldNames.salesField !== 'product_sales' ? fieldNames.salesField : '商品销量';
                salesFieldHeader.textContent = displayName;
                console.log(`✅ 销量字段表头更新为: ${displayName}`);
            }

            if (storeSalesFieldHeader && fieldNames.storeSalesField) {
                const displayName = fieldNames.storeSalesField && fieldNames.storeSalesField !== 'store_sales' ? fieldNames.storeSalesField : '店铺销量';
                storeSalesFieldHeader.textContent = displayName;
                console.log(`✅ 店铺销量字段表头更新为: ${displayName}`);
            }

            if (crawlTimeFieldHeader && fieldNames.crawlTimeField) {
                const displayName = fieldNames.crawlTimeField && fieldNames.crawlTimeField !== 'extracted_at' ? fieldNames.crawlTimeField : '更新时间';
                crawlTimeFieldHeader.textContent = displayName;
                console.log(`✅ 时间字段表头更新为: ${displayName}`);
            }

        } catch (error) {
            console.error('❌ 更新表头失败:', error);
            this.resetAnomalyTableHeaders();
        }
    }

    /**
     * 重置异常监控表头为默认文本 - ultrathink
     */
    resetAnomalyTableHeaders() {
        try {
            const salesFieldHeader = document.querySelector('th[data-sort="sales_field"]');
            const storeSalesFieldHeader = document.querySelector('th[data-sort="store_sales_field"]');
            const crawlTimeFieldHeader = document.querySelector('th[data-sort="crawl_time_field"]');

            if (salesFieldHeader) salesFieldHeader.textContent = '商品销量';
            if (storeSalesFieldHeader) storeSalesFieldHeader.textContent = '店铺销量';
            if (crawlTimeFieldHeader) crawlTimeFieldHeader.textContent = '更新时间';

            console.log('🔄 表头已重置为默认文本');
        } catch (error) {
            console.error('❌ 重置表头失败:', error);
        }
    }

    /**
     * 创建异常商品表格行 - 异常监控专用字段展示
     */
    createAnomalyTableRow(anomaly) {
        // 格式化时间显示
        const formatTime = (timeValue) => {
            if (!timeValue) return '-';
            try {
                const date = new Date(timeValue);
                return date.toLocaleString('zh-CN');
            } catch {
                return String(timeValue);
            }
        };

        // 格式化字段显示（只显示值，表头已有字段名）
        const formatFieldDisplay = (fieldName, value, unit = '') => {
            return `<span class="field-value">${value || '-'}${unit}</span>`;
        };

        // 获取字段信息
        const fieldNames = anomaly.fieldNames || {};
        const productName = anomaly.productName || anomaly.product_name || '未知商品';
        const categoryName = anomaly.categoryName || anomaly.category_name || '未分类';
        const productPrice = anomaly.productPrice || anomaly.product_price || 0;
        const detectionTime = anomaly.detectionTime ? formatTime(anomaly.detectionTime) : formatTime(new Date());

        console.log('🔍 [DEBUG] 渲染异常商品行:', {
            productId: anomaly.productId,
            fieldNames: fieldNames,
            sales_24h: anomaly.sales_24h,
            sales24h: anomaly.sales24h,
            revenue_24h: anomaly.revenue_24h,
            revenue24h: anomaly.revenue24h
        });

        return `
            <tr class="anomaly-row" data-anomaly-id="${anomaly.productId || anomaly.product_id}">
                <td class="checkbox-col">
                    <input type="checkbox" class="anomaly-checkbox" value="${anomaly.productId || anomaly.product_id}">
                </td>
                <td class="product-name-col">
                    <div class="product-name">${productName}</div>
                    <div class="product-id">ID: ${anomaly.productId || anomaly.product_id}</div>
                </td>
                <td class="category-col">
                    <span class="product-category">${categoryName}</span>
                </td>
                <td class="price-col">
                    <span class="product-price">¥${Number(productPrice).toFixed(2)}</span>
                </td>
                <td class="field-col">
                    ${formatFieldDisplay(
                        fieldNames.salesField && fieldNames.salesField !== 'product_sales' ? fieldNames.salesField : '商品销量',
                        fieldNames.salesValue || anomaly.sales || 0
                    )}
                </td>
                <td class="field-col">
                    ${formatFieldDisplay(
                        fieldNames.storeSalesField && fieldNames.storeSalesField !== 'store_sales' ? fieldNames.storeSalesField : '店铺销量',
                        fieldNames.storeSalesValue || anomaly.storeSales || 0
                    )}
                </td>
                <td class="field-col">
                    ${formatFieldDisplay(
                        fieldNames.crawlTimeField && fieldNames.crawlTimeField !== 'extracted_at' ? fieldNames.crawlTimeField : '更新时间',
                        fieldNames.crawlTimeValue ? formatTime(fieldNames.crawlTimeValue) : (anomaly.crawlTime ? formatTime(anomaly.crawlTime) : '-')
                    )}
                </td>
                <td class="sales-col">
                    <span class="sales-value ${anomaly.isSalesAnomaly ? 'anomaly-highlight' : ''}">${(anomaly.sales_24h || anomaly.sales24h || 0).toLocaleString()}</span>
                </td>
                <td class="revenue-col">
                    <span class="revenue-value ${anomaly.isRevenueAnomaly ? 'anomaly-highlight' : ''}">¥${(anomaly.revenue_24h || anomaly.revenue24h || 0).toLocaleString()}</span>
                </td>
                <td class="time-col">
                    <span class="detection-time">${detectionTime}</span>
                </td>
                <td class="actions-col">
                    <div class="action-buttons">
                        <button class="action-icon view-details-btn" data-product-id="${anomaly.productId || anomaly.product_id}" title="查看详情" style="color: #3b82f6;">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                                <circle cx="12" cy="12" r="3"></circle>
                            </svg>
                        </button>
                        <button class="action-icon delete-btn ignore-anomaly-btn" data-product-id="${anomaly.productId || anomaly.product_id}" title="删除商品" style="color: #dc2626;">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <polyline points="3,6 5,6 21,6"></polyline>
                                <path d="m19,6v14a2,2 0 0,1 -2,2H7a2,2 0 0,1 -2,-2V6m3,0V4a2,2 0 0,1 2,-2h4a2,2 0 0,1 2,2v2"></path>
                                <line x1="10" y1="11" x2="10" y2="17"></line>
                                <line x1="14" y1="11" x2="14" y2="17"></line>
                            </svg>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }

    // ==================== 🆕 分类筛选功能方法 ====================

    /**
     * 处理分类筛选
     */
    handleCategoryFilter(selectedCategory) {
        console.log('🏷️ 分类筛选:', selectedCategory);

        // 更新筛选条件
        if (selectedCategory === '') {
            this.selectedCategories = []; // 空数组表示显示所有分类
        } else {
            this.selectedCategories = [selectedCategory];
        }

        // 应用筛选并重新渲染
        this.applyFiltersAndRender();
    }

    /**
     * 应用筛选逻辑
     */
    applyFiltersAndRender() {
        let filteredData = this.originalAnomalies;

        // 应用分类筛选
        if (this.selectedCategories.length > 0) {
            filteredData = this.originalAnomalies.filter(anomaly =>
                this.selectedCategories.includes(anomaly.categoryName)
            );
        }

        // 更新统计显示
        this.updateFilterStats(filteredData.length, this.originalAnomalies.length);

        // 🆕 如果筛选结果为空，确保正确显示空状态
        if (filteredData.length === 0) {
            const tableWrapper = document.querySelector('.data-table-wrapper');
            const emptyState = document.getElementById('anomalyEmptyState');
            const countElement = document.getElementById('anomalyCount');

            // 更新计数
            if (countElement) {
                countElement.textContent = '0';
            }

            // 隐藏表格，显示空状态
            if (tableWrapper) tableWrapper.style.display = 'none';
            if (emptyState) emptyState.style.display = 'block';

            // 清空表格内容
            const tableBody = document.getElementById('anomaliesTableBody');
            if (tableBody) {
                tableBody.innerHTML = '';
            }
        } else {
            // 有数据时正常渲染
            this.currentAnomalies = filteredData;
            this.renderSimpleAnomalyList(filteredData);
        }

        console.log(`📊 筛选结果: ${filteredData.length}/${this.originalAnomalies.length} 项`);
    }

    /**
     * 更新筛选统计
     */
    updateFilterStats(filtered, total) {
        const statsElement = document.getElementById('filterResultStats');
        if (statsElement) {
            statsElement.textContent = `显示 ${filtered}/${total} 项`;
        }
    }

    /**
     * 加载分类筛选选项 - 只显示有异常记录的分类
     */
    async loadCategoryFilterOptions() {
        try {
            if (!this.categoryManager) {
                console.warn('⚠️ CategoryManager 未初始化');
                return;
            }

            const select = document.getElementById('categoryFilterSelect');
            if (!select) return;

            // 清空现有选项，保留"全部分类"选项
            select.innerHTML = '<option value="">全部分类</option>';

            // 🆕 基于当前异常数据生成分类选项，而不是从categoryManager获取所有分类
            if (this.originalAnomalies.length === 0) {
                console.log('📝 无异常记录，分类筛选选项为空');
                return;
            }

            // 统计每个分类的异常商品数量
            const categoryStats = {};
            this.originalAnomalies.forEach(anomaly => {
                const categoryName = anomaly.categoryName || '未分类';
                if (!categoryStats[categoryName]) {
                    categoryStats[categoryName] = 0;
                }
                categoryStats[categoryName]++;
            });

            // 添加有异常记录的分类选项
            Object.entries(categoryStats)
                .sort(([a], [b]) => a.localeCompare(b)) // 按分类名排序
                .forEach(([categoryName, count]) => {
                    const option = document.createElement('option');
                    option.value = categoryName;
                    option.textContent = `${categoryName} (${count}个异常)`;
                    select.appendChild(option);
                });

            console.log('✅ 分类筛选选项加载完成:', Object.keys(categoryStats).length, '个有异常的分类');
        } catch (error) {
            console.error('❌ 加载分类筛选选项失败:', error);
        }
    }

    // ==================== 🆕 商品管理分类筛选功能方法 ====================

    /**
     * 加载商品筛选分类选项 - 显示所有分类（包括空分类）
     */
    async loadProductCategoryFilterOptions() {
        try {
            if (!this.categoryManager) {
                console.warn('⚠️ CategoryManager 未初始化');
                return;
            }

            const select = document.getElementById('productCategoryFilterSelect');
            if (!select) {
                console.warn('⚠️ 商品筛选下拉框未找到');
                return;
            }

            console.log('🔄 开始加载商品筛选分类选项...');

            // 清空并保留"全部分类"
            select.innerHTML = '<option value="">全部分类</option>';

            // 获取所有分类
            const categories = await this.categoryManager.getAllCategories();
            console.log(`📁 获取到 ${categories.length} 个分类`);

            if (categories.length === 0) {
                console.log('📝 无分类数据，仅显示"全部分类"');
                return;
            }

            // 🆕 按爬取时间降序排序（最新的在前）
            categories.sort((a, b) => {
                // 优先使用 created_at，其次 updated_at，最后使用 id
                const timeA = new Date(a.created_at || a.updated_at || 0).getTime();
                const timeB = new Date(b.created_at || b.updated_at || 0).getTime();

                // 如果时间相同，使用ID降序
                if (timeA === timeB) {
                    return (b.id || 0) - (a.id || 0);
                }

                return timeB - timeA; // 降序：越晚越前
            });

            // 统计每个分类的商品数量
            const categoryCounts = {};
            const allProducts = await this.localDataManager.getAllProducts();
            console.log(`📦 获取到 ${allProducts.length} 个商品`);

            allProducts.forEach(product => {
                const categoryId = product.category_id;
                if (categoryId) {
                    categoryCounts[categoryId] = (categoryCounts[categoryId] || 0) + 1;
                }
            });

            // 🆕 生成所有分类选项，包括空分类
            categories.forEach(category => {
                const count = categoryCounts[category.id] || 0; // 默认0
                const option = document.createElement('option');
                option.value = category.id;
                option.textContent = `${category.name} (${count}个商品)`;

                // 可选：为空分类添加特殊样式
                if (count === 0) {
                    option.classList.add('empty-category');
                }

                select.appendChild(option);
            });

            console.log('✅ 商品筛选分类选项加载完成:', categories.length, '个分类（包括空分类）');

        } catch (error) {
            console.error('❌ 加载商品筛选分类选项失败:', error);
        }
    }

    /**
     * 同步分类选择状态（双向同步：分类树 ↔ 顶部下拉框）
     * @param {string|number} categoryId - 分类ID，'' 或 'all' 表示全部分类
     * @param {string} source - 触发源：'tree' 表示来自分类树，'dropdown' 表示来自下拉框
     */
    syncCategorySelection(categoryId, source) {
        console.log(`🔄 同步分类选择: ID=${categoryId}, 来源=${source}`);

        // 统一处理分类ID格式
        const normalizedCategoryId = (categoryId === '' || categoryId === 'all') ? 'all' : categoryId;

        // 更新筛选条件
        this.filters.category = normalizedCategoryId;

        // 🆕 无论来源如何，都更新分类树高亮状态
        const categoryItems = document.querySelectorAll('.category-item');
        if (normalizedCategoryId === 'all') {
            // 选择"全部分类"时，清除所有分类树高亮
            categoryItems.forEach(item => {
                item.classList.remove('active');
            });
            console.log('  ✓ 已清除分类树高亮');
        } else {
            // 选择特定分类时，高亮对应分类
            categoryItems.forEach(item => {
                const itemCategoryId = parseInt(item.dataset.categoryId);
                const isMatch = itemCategoryId === parseInt(normalizedCategoryId);
                item.classList.toggle('active', isMatch);

                if (isMatch) {
                    console.log(`  ✓ 已高亮分类树节点: ID=${itemCategoryId}`);
                }
            });
        }

        // 🆕 无论来源如何，都同步更新下拉框
        const dropdown = document.getElementById('productCategoryFilterSelect');
        if (dropdown) {
            dropdown.value = normalizedCategoryId === 'all' ? '' : normalizedCategoryId;
            console.log(`  ✓ 已同步下拉框: value="${dropdown.value}"`);
        }

        // 重置到第一页并重新加载商品数据
        this.pagination.currentPage = 1;
        console.log('  ✓ 重置分页到第1页');

        // 重新加载商品数据
        this.loadProductsData();
        console.log('  ✓ 触发商品数据重新加载');
    }

    /**
     * 处理商品分类筛选（下拉框change事件）
     * @param {string} selectedCategory - 选中的分类ID
     */
    handleProductCategoryFilter(selectedCategory) {
        console.log('🏷️ 商品分类筛选触发:', selectedCategory);

        // 使用统一的同步方法
        this.syncCategorySelection(selectedCategory, 'dropdown');
    }

    /**
     * 获取商品的具体数据库字段名称 - 优化版本，集成TimeSeriesDataManager (ultrathink)
     */
    async getProductFieldNames(anomaly) {
        // ultrathink: 统一产品ID参数处理
        const productId = anomaly.productId || anomaly.product_id || anomaly.id;
        console.log(`🔍 开始获取商品 ${productId} 的字段名称...`);

        try {
            // 从数据库获取完整的商品数据，包含时间序列字段
            const result = await this.sharedDataService.localDataManager.getProduct(productId);

            if (result.success && result.product) {
                const product = result.product; // 提取实际的商品对象
                console.log(`📦 成功获取商品数据，商品字段数: ${Object.keys(product).length}`);

                // 使用TimeSeriesDataManager获取最新的时间序列数据
                const timeSeriesManager = this.sharedDataService.localDataManager.timeSeriesManager;

                if (timeSeriesManager) {
                    console.log(`⏰ TimeSeriesDataManager 可用，查找时间序列数据...`);

                    // ultrathink: 调试时间序列字段识别
                    const allFields = Object.keys(product);
                    const timeSeriesFields = allFields.filter(field =>
                        field.includes('商品销量') || field.includes('店铺销量') || field.includes('爬取时间')
                    );
                    console.log(`🔍 商品 ${productId} 所有字段 (${allFields.length}个):`, allFields.slice(0, 20), allFields.length > 20 ? '...' : '');
                    console.log(`🕒 时间序列相关字段 (${timeSeriesFields.length}个):`, timeSeriesFields);

                    // 检查是否有正确格式的时间序列字段
                    const properTimeSeriesFields = allFields.filter(field => {
                        const isTimeSeries = field.match(/^(商品销量|店铺销量|爬取时间)（.+）$/);
                        if (isTimeSeries) {
                            console.log(`✅ 找到正确格式的时间序列字段: ${field}`);
                        }
                        return isTimeSeries;
                    });
                    console.log(`📅 正确格式的时间序列字段 (${properTimeSeriesFields.length}个):`, properTimeSeriesFields);

                    // 如果没有时间序列字段，列出一些示例字段来帮助诊断
                    if (properTimeSeriesFields.length === 0) {
                        console.log(`🔍 诊断信息 - 字段示例:`, allFields.slice(0, 10));
                    }

                    const latestData = timeSeriesManager.getLatestSalesData(product);
                    console.log(`🎯 getLatestSalesData返回结果:`, latestData);

                    if (latestData && latestData.date) {
                        // 有时间序列数据，使用时间序列字段名
                        console.log(`✅ 找到时间序列数据，最新日期: ${latestData.date}`);
                        const timeSeriesFields = {
                            salesField: `商品销量（${latestData.date}）`,
                            storeSalesField: `店铺销量（${latestData.date}）`,
                            crawlTimeField: `爬取时间（${latestData.date}）`,
                            isTimeSeries: true,
                            latestDate: latestData.date,
                            salesValue: latestData.productSales,
                            storeSalesValue: latestData.storeSales,
                            crawlTimeValue: latestData.crawlTime
                        };
                        console.log(`🎯 返回时间序列字段名:`, timeSeriesFields);
                        return timeSeriesFields;
                    } else {
                        console.log(`📊 未找到时间序列数据，检查是否有实际的时间序列字段...`);

                        // ultrathink: 直接检查产品中是否有时间序列格式的字段
                        if (properTimeSeriesFields.length > 0) {
                            console.log(`✅ 发现实际时间序列字段，使用现有字段名`);
                            // 从实际字段中提取最新日期
                            const latestField = this.getLatestField(properTimeSeriesFields);
                            const dateMatch = latestField.match(/（(.+?)）/);
                            const actualDate = dateMatch ? dateMatch[1] : '未知日期';

                            return {
                                salesField: properTimeSeriesFields.find(f => f.includes('商品销量')) || '商品销量',
                                storeSalesField: properTimeSeriesFields.find(f => f.includes('店铺销量')) || '店铺销量',
                                crawlTimeField: properTimeSeriesFields.find(f => f.includes('爬取时间')) || '爬取时间',
                                isTimeSeries: true,
                                latestDate: actualDate,
                                salesValue: product[properTimeSeriesFields.find(f => f.includes('商品销量'))] || 0,
                                storeSalesValue: product[properTimeSeriesFields.find(f => f.includes('店铺销量'))] || 0,
                                crawlTimeValue: product[properTimeSeriesFields.find(f => f.includes('爬取时间'))] || null
                            };
                        } else {
                            console.log(`📊 没有时间序列字段，使用基础字段名`);
                            // 没有时间序列字段，返回基础字段名而不是假的时间序列格式
                        }
                    }
                } else {
                    console.log(`⚠️ TimeSeriesDataManager 不可用，使用基础字段`);
                }

                // 如果没有时间序列数据，查找基础字段 (ultrathink)
                const allFields = Object.keys(product);
                console.log(`🔍 商品 ${productId} 所有字段:`, allFields);

                // 查找基础销量字段 - 扩展字段列表以包含数据库实际字段
                const salesFields = allFields.filter(field =>
                    ['sales', 'current_sales', 'productSales', 'product_sales', 'sales_volume'].includes(field)
                );

                // 查找基础店铺销量字段 - 扩展字段列表
                const storeSalesFields = allFields.filter(field =>
                    ['storeSales', 'store_sales', 'shop_sales', 'store_volume', 'shop_volume'].includes(field)
                );

                // 查找基础爬取时间字段 - 扩展字段列表
                const crawlTimeFields = allFields.filter(field =>
                    ['extracted_at', 'updated_at', 'created_at', 'timestamp'].includes(field)
                );

                console.log(`📊 基础字段查找结果:`, {
                    找到的销量字段: salesFields,
                    找到的店铺销量字段: storeSalesFields,
                    找到的爬取时间字段: crawlTimeFields
                });

                // 选择实际存在的字段名
                const selectedSalesField = salesFields[0] || 'product_sales';
                const selectedStoreSalesField = storeSalesFields[0] || 'store_sales';
                const selectedCrawlTimeField = crawlTimeFields[0] || 'extracted_at';

                return {
                    salesField: selectedSalesField,
                    storeSalesField: selectedStoreSalesField,
                    crawlTimeField: selectedCrawlTimeField,
                    isTimeSeries: false,
                    salesValue: product[selectedSalesField] || 0,
                    storeSalesValue: product[selectedStoreSalesField] || 0,
                    crawlTimeValue: product[selectedCrawlTimeField] || null
                };
            }
        } catch (error) {
            console.warn('获取字段名称失败:', error);
        }

        // 返回默认字段名 (ultrathink调试)
        console.log(`⚠️ 使用默认字段名，商品ID: ${productId}`);
        return {
            salesField: 'product_sales',
            storeSalesField: 'store_sales',
            crawlTimeField: 'extracted_at',
            isTimeSeries: false,
            salesValue: 0,
            storeSalesValue: 0,
            crawlTimeValue: null
        };
    }

    /**
     * 从字段列表中获取最新的字段（按时间序列排序）
     */
    getLatestField(fields) {
        if (!fields || fields.length === 0) return null;

        // 如果只有一个字段，直接返回
        if (fields.length === 1) return fields[0];

        // 按时间序列排序，找到最新的字段
        const timeSeriesFields = fields.filter(field => field.includes('（') && field.includes('）'));

        if (timeSeriesFields.length > 0) {
            // 提取日期并排序
            const fieldsWithDates = timeSeriesFields.map(field => {
                const dateMatch = field.match(/（(.+?)）/);
                if (dateMatch) {
                    const dateStr = dateMatch[1];
                    // 尝试解析日期
                    const date = this.parseFieldDate(dateStr);
                    return { field, date, dateStr };
                }
                return { field, date: null, dateStr: '' };
            }).filter(item => item.date);

            // 按日期排序，最新的在前
            fieldsWithDates.sort((a, b) => b.date - a.date);

            if (fieldsWithDates.length > 0) {
                return fieldsWithDates[0].field;
            }
        }

        // 如果没有时间序列字段，返回第一个字段
        return fields[0];
    }

    /**
     * 解析字段中的日期字符串
     */
    parseFieldDate(dateStr) {
        try {
            // 处理各种日期格式
            if (dateStr.includes('月') && dateStr.includes('日')) {
                // 格式：9月11日
                const match = dateStr.match(/(\d+)月(\d+)日/);
                if (match) {
                    const month = parseInt(match[1]);
                    const day = parseInt(match[2]);
                    const year = new Date().getFullYear();
                    return new Date(year, month - 1, day);
                }
            } else if (dateStr.includes('-')) {
                // 格式：2025-09-11
                return new Date(dateStr);
            }

            // 尝试直接解析
            return new Date(dateStr);
        } catch (error) {
            return null;
        }
    }

    /**
     * 获取商品销量图表数据 - 异常商品悬浮图表功能
     * @param {string|number} productId - 商品ID
     * @returns {Object} 图表数据对象
     */
    async getProductSalesChart(productId) {
        console.log(`📊 开始获取商品 ${productId} 的销量图表数据...`);

        try {
            // 1. 获取完整商品数据
            const productResult = await this.sharedDataService.localDataManager.getProduct(productId);
            if (!productResult.success || !productResult.product) {
                console.warn(`⚠️ 商品 ${productId} 不存在`);
                return {
                    success: false,
                    error: '商品不存在',
                    productName: '未知商品',
                    productPrice: 0,
                    chartData: []
                };
            }

            const product = productResult.product; // 提取实际的商品对象
            console.log(`📦 成功获取商品数据: ${product.product_name}`);

            // 2. 使用TimeSeriesDataManager获取销量历史
            const timeSeriesManager = this.sharedDataService.localDataManager.timeSeriesManager;
            let salesHistory = [];

            if (timeSeriesManager) {
                console.log('⏰ 使用TimeSeriesDataManager获取销量历史...');
                salesHistory = timeSeriesManager.getSalesHistory(product);
                console.log(`📈 获取到 ${salesHistory.length} 个历史数据点:`, salesHistory);
            } else {
                console.warn('⚠️ TimeSeriesDataManager不可用，无法获取时间序列数据');
            }

            // 3. 格式化图表数据
            const chartData = salesHistory.map(item => ({
                date: item.date,           // 中文日期格式 "9月17日"
                sales: item.productSales || 0,  // 商品销量
                timestamp: this.parseFieldDate(item.date) // 用于排序的时间戳
            })).filter(item => item.timestamp) // 过滤掉无效日期
              .sort((a, b) => a.timestamp - b.timestamp); // 按时间排序

            // 4. 添加基础销量作为第一个数据点
            if (product.product_sales !== undefined) {
                console.log('📊 添加基础销量作为图表第一个数据点');
                // 创建基础销量数据点，时间戳设为最早
                const baseTimestamp = chartData.length > 0 ?
                    new Date(chartData[0].timestamp.getTime() - 24 * 60 * 60 * 1000) : // 比第一个数据点早一天
                    new Date(Date.now() - 24 * 60 * 60 * 1000); // 如果没有其他数据，设为一天前

                const baseSalesPoint = {
                    date: this.formatChartDate(product.extracted_at),  // 🎯 修复：基础销量点显示为日期格式
                    sales: product.product_sales || 0,
                    timestamp: new Date(product.extracted_at),
                    isBaseSales: true // 标记为基础销量点
                };

                // 将基础销量插入到数组开头
                chartData.unshift(baseSalesPoint);
            }

            const result = {
                success: true,
                productName: product.product_name || '未知商品',
                productPrice: product.product_price || 0,
                chartData: chartData,
                hasTimeSeriesData: salesHistory.length > 0,
                dataPoints: chartData.length
            };

            console.log(`✅ 图表数据生成完成:`, {
                商品名称: result.productName,
                数据点数量: result.dataPoints,
                有时间序列: result.hasTimeSeriesData
            });

            return result;

        } catch (error) {
            console.error(`❌ 获取商品 ${productId} 图表数据失败:`, error);
            return {
                success: false,
                error: error.message,
                productName: '加载失败',
                productPrice: 0,
                chartData: []
            };
        }
    }

    /**
     * 初始化悬浮图表功能
     */
    initializeHoverChart() {
        console.log('📊 初始化悬浮图表功能...');

        // 初始化图表实例变量
        this.hoverChart = {
            container: null,
            chart: null,
            isVisible: false,
            currentProductId: null,
            hideTimeout: null
        };

        // 创建悬浮图表容器
        this.createHoverChartContainer();

        // 绑定悬浮事件
        this.bindHoverChartEvents();

        console.log('✅ 悬浮图表功能初始化完成');
    }

    /**
     * 创建悬浮图表容器
     */
    createHoverChartContainer() {
        // 检查是否已存在
        let container = document.getElementById('anomalyChartTooltip');
        if (container) {
            container.remove();
        }

        // 创建新容器
        container = document.createElement('div');
        container.id = 'anomalyChartTooltip';
        container.className = 'anomaly-chart-tooltip';
        container.innerHTML = `
            <div class="chart-tooltip-header">
                <div class="chart-product-info">
                    <div class="chart-product-name" id="chartProductName">加载中...</div>
                    <div class="chart-product-price" id="chartProductPrice">¥0</div>
                </div>
                <button class="chart-close-btn" id="chartCloseBtn">×</button>
            </div>
            <div class="chart-canvas-container">
                <canvas class="chart-canvas" id="chartCanvas" width="280" height="100"></canvas>
            </div>
            <div class="chart-stats">
                <div class="chart-stat-item">
                    <span class="chart-stat-label">基础销量</span>
                    <span class="chart-stat-value" id="chartBaseSales">-</span>
                </div>
                <div class="chart-stat-item">
                    <span class="chart-stat-label">数据点</span>
                    <span class="chart-stat-value" id="chartDataPoints">-</span>
                </div>
            </div>
        `;

        document.body.appendChild(container);
        this.hoverChart.container = container;

        // 绑定关闭按钮事件
        document.getElementById('chartCloseBtn').addEventListener('click', () => {
            this.hideHoverChart();
        });

        console.log('📦 悬浮图表容器创建完成');
    }

    /**
     * 绑定悬浮图表事件
     */
    bindHoverChartEvents() {
        // 使用事件委托，监听异常表格容器的悬浮事件
        const anomalyContainer = document.getElementById('anomalyList');
        if (!anomalyContainer) {
            console.warn('⚠️ 异常表格容器未找到，跳过悬浮图表事件绑定');
            return;
        }

        // 鼠标进入事件
        anomalyContainer.addEventListener('mouseover', (event) => {
            const productNameElement = event.target.closest('.product-name');
            if (productNameElement) {
                const productId = this.extractProductIdFromRow(productNameElement);
                if (productId) {
                    this.handleProductHover(productId, event);
                }
            }
        });

        // 鼠标离开事件
        anomalyContainer.addEventListener('mouseout', (event) => {
            const productNameElement = event.target.closest('.product-name');
            if (productNameElement) {
                this.handleProductLeave(event);
            }
        });

        // 操作按钮点击事件委托
        anomalyContainer.addEventListener('click', (event) => {
            // 查看详情按钮
            const viewDetailsBtn = event.target.closest('.view-details-btn');
            if (viewDetailsBtn) {
                event.preventDefault();
                event.stopPropagation();
                const productId = viewDetailsBtn.getAttribute('data-product-id');
                if (productId) {
                    this.viewAnomalyDetails(parseInt(productId));
                }
                return;
            }

            // 删除商品按钮
            const deleteBtn = event.target.closest('.ignore-anomaly-btn');
            if (deleteBtn) {
                event.preventDefault();
                event.stopPropagation();
                const productId = deleteBtn.getAttribute('data-product-id');
                if (productId) {
                    this.deleteProduct(parseInt(productId));
                }
                return;
            }
        });

        console.log('🖱️ 悬浮图表事件和操作按钮事件绑定完成');
    }

    /**
     * 从表格行中提取商品ID
     */
    extractProductIdFromRow(productNameElement) {
        // 尝试从多个可能的属性中获取产品ID
        const row = productNameElement.closest('tr');
        if (!row) return null;

        // 尝试从data属性获取 (data-anomaly-id) - 转换为数字类型
        const productId = row.dataset.anomalyId;
        if (productId) return parseInt(productId);

        // 尝试从操作按钮中获取 (新的data-product-id属性)
        const actionButtons = row.querySelectorAll('button[data-product-id]');
        if (actionButtons.length > 0) {
            const productId = actionButtons[0].getAttribute('data-product-id');
            if (productId) {
                return parseInt(productId);
            }
        }

        console.warn('⚠️ 无法从表格行中提取商品ID');
        return null;
    }

    /**
     * 处理商品悬浮事件
     */
    async handleProductHover(productId, event) {
        // 清除之前的隐藏定时器
        if (this.hoverChart.hideTimeout) {
            clearTimeout(this.hoverChart.hideTimeout);
            this.hoverChart.hideTimeout = null;
        }

        // 如果已经显示相同商品，不重复加载
        if (this.hoverChart.isVisible && this.hoverChart.currentProductId === productId) {
            return;
        }

        console.log(`🖱️ 悬浮商品 ${productId}，准备显示图表`);

        // 延迟显示，避免快速划过触发
        setTimeout(async () => {
            await this.showHoverChart(productId, event.clientX, event.clientY);
        }, 200);
    }

    /**
     * 处理商品离开事件
     */
    handleProductLeave(event) {
        // 设置延迟隐藏，避免误触
        this.hoverChart.hideTimeout = setTimeout(() => {
            this.hideHoverChart();
        }, 300);
    }

    /**
     * 显示悬浮图表
     */
    async showHoverChart(productId, mouseX, mouseY) {
        try {
            console.log(`📊 开始显示商品 ${productId} 的悬浮图表`);

            // 显示加载状态
            this.showChartLoading();

            // 获取图表数据
            const chartData = await this.getProductSalesChart(productId);

            if (!chartData.success) {
                console.warn('⚠️ 获取图表数据失败:', chartData.error);
                this.showChartError(chartData.error);
                return;
            }

            // 更新图表内容
            this.updateChartContent(chartData);

            // 定位并显示图表
            this.positionAndShowChart(mouseX, mouseY);

            // 渲染图表
            this.renderChart(chartData.chartData);

            // 更新状态
            this.hoverChart.isVisible = true;
            this.hoverChart.currentProductId = productId;

            console.log('✅ 悬浮图表显示完成');

        } catch (error) {
            console.error('❌ 显示悬浮图表失败:', error);
            this.showChartError('加载失败');
        }
    }

    /**
     * 隐藏悬浮图表
     */
    hideHoverChart() {
        if (!this.hoverChart.container) return;

        this.hoverChart.container.classList.remove('visible');
        this.hoverChart.isVisible = false;
        this.hoverChart.currentProductId = null;

        // 销毁图表实例
        if (this.hoverChart.chart) {
            this.hoverChart.chart.destroy();
            this.hoverChart.chart = null;
        }

        console.log('📊 悬浮图表已隐藏');
    }

    /**
     * 显示图表加载状态
     */
    showChartLoading() {
        const canvas = document.getElementById('chartCanvas');
        const ctx = canvas.getContext('2d');

        // 清空画布
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // 绘制加载提示
        ctx.fillStyle = '#64748b';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('正在加载图表数据...', canvas.width / 2, canvas.height / 2);
    }

    /**
     * 显示图表错误状态
     */
    showChartError(errorMessage) {
        const canvas = document.getElementById('chartCanvas');
        const ctx = canvas.getContext('2d');

        // 清空画布
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // 绘制错误提示
        ctx.fillStyle = '#ef4444';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(`加载失败: ${errorMessage}`, canvas.width / 2, canvas.height / 2);
    }

    /**
     * 更新图表内容
     */
    updateChartContent(chartData) {
        // 更新商品信息
        document.getElementById('chartProductName').textContent = chartData.productName;
        document.getElementById('chartProductPrice').textContent = `¥${chartData.productPrice}`;

        // 更新统计信息
        // 查找基础销量点（如果存在）
        const baseSalesPoint = chartData.chartData.find(item => item.isBaseSales);
        const baseSales = baseSalesPoint ? baseSalesPoint.sales : 0;

        // 计算时间序列数据点数量（排除基础销量点）
        const timeSeriesPoints = chartData.chartData.filter(item => !item.isBaseSales).length;

        document.getElementById('chartBaseSales').textContent = baseSales.toLocaleString();
        document.getElementById('chartDataPoints').textContent = `${timeSeriesPoints}天`;
    }

    /**
     * 智能定位并显示图表
     */
    positionAndShowChart(mouseX, mouseY) {
        const container = this.hoverChart.container;
        const containerRect = container.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;

        let left = mouseX + 10; // 默认在鼠标右侧
        let top = mouseY - containerRect.height / 2; // 垂直居中对齐

        // 右侧空间不足，显示在左侧
        if (left + containerRect.width > viewportWidth - 10) {
            left = mouseX - containerRect.width - 10;
        }

        // 垂直空间不足，向上调整
        if (top < 10) {
            top = 10;
        } else if (top + containerRect.height > viewportHeight - 10) {
            top = viewportHeight - containerRect.height - 10;
        }

        // 应用位置
        container.style.left = `${left}px`;
        container.style.top = `${top}px`;

        // 显示容器
        container.classList.add('visible');
    }

    /**
     * 渲染图表
     */
    renderChart(chartData) {
        const canvas = document.getElementById('chartCanvas');

        // 创建或更新图表实例
        if (this.hoverChart.chart) {
            this.hoverChart.chart.destroy();
        }

        this.hoverChart.chart = new SimpleLineChart(canvas);
        this.hoverChart.chart.setData(chartData);
        this.hoverChart.chart.render();
    }

    /**
     * 查看异常详情 - 优化版：直接跳转到商品链接
     */
    async viewAnomalyDetails(productId) {
        try {
            console.log('🔍 查看异常商品详情:', productId);

            // 获取商品详细信息
            const result = await this.sharedDataService.localDataManager.getProduct(productId);

            if (!result.success || !result.product) {
                this.showToast('error', '错误', '商品不存在');
                return;
            }

            const product = result.product;

            // ✅ 优先检查是否有商品链接，有则直接跳转
            if (product.product_url || product.productUrl) {
                const productUrl = product.product_url || product.productUrl;
                console.log(`🔗 直接跳转到商品链接: ${productUrl}`);

                // 在新标签页打开商品链接
                window.open(productUrl, '_blank', 'noopener,noreferrer');

                // 显示成功提示
                this.showToast('success', '跳转成功', `已打开商品页面: ${product.product_name || '未知商品'}`);
                return;
            }

            // 如果没有商品链接，则显示传统的详情对话框
            console.log('⚠️ 商品无链接，显示详情对话框');

            // 创建详情对话框HTML
            const dialogHtml = this.createAnomalyDetailsDialog(product);

            // 显示对话框
            this.showModal(dialogHtml);

        } catch (error) {
            console.error('❌ 查看异常详情失败:', error);
            this.showToast('error', '错误', '查看详情失败: ' + error.message);
        }
    }

    /**
     * 忽略异常
     */
    async ignoreAnomaly(productId) {
        try {
            console.log('忽略异常:', productId);

            // 确认对话框
            if (!confirm('确定要忽略此商品的异常状态吗？')) {
                return;
            }

            // 更新商品的异常状态
            const success = await this.sharedDataService.localDataManager.updateProduct(productId, {
                is_anomaly: false,
                anomaly_ignored: true,
                anomaly_ignored_at: new Date().toISOString()
            });

            if (success) {
                // 刷新异常列表
                if (this.latestAnomalyResults && this.latestAnomalyResults.anomalies) {
                    // 从当前显示的列表中移除
                    this.latestAnomalyResults.anomalies = this.latestAnomalyResults.anomalies.filter(
                        anomaly => anomaly.productId !== productId
                    );
                    this.latestAnomalyResults.anomaliesFound = this.latestAnomalyResults.anomalies.length;

                    // 重新渲染列表
                    this.renderSimpleAnomalyList(this.latestAnomalyResults.anomalies);
                }

                this.showToast('success', '成功', '已忽略异常状态');
            } else {
                this.showToast('error', '错误', '忽略异常失败');
            }

        } catch (error) {
            console.error('忽略异常失败:', error);
            this.showToast('error', '错误', '操作失败');
        }
    }

    /**
     * 创建异常详情对话框
     */
    createAnomalyDetailsDialog(product) {
        // 获取字段名称
        const allFields = Object.keys(product);
        const timeSeriesFields = allFields.filter(field =>
            field.includes('（') && field.includes('）')
        );

        // 构建详情表格
        const fieldsHtml = timeSeriesFields.map(field => {
            const value = product[field];
            const displayValue = field.includes('时间') ?
                this.formatTime(value) :
                (typeof value === 'number' ? value.toLocaleString() : value);

            return `
                <tr>
                    <td class="field-name">${field}</td>
                    <td class="field-value">${displayValue || '无数据'}</td>
                </tr>
            `;
        }).join('');

        return `
            <div class="anomaly-details-dialog">
                <div class="modal-header">
                    <h3 class="modal-title">🔍 异常商品详情</h3>
                    <button class="modal-close" id="modalCloseBtn">&times;</button>
                </div>

                <div class="modal-body">
                    <div class="product-basic-info">
                        <h4>基础信息</h4>
                        <div class="info-grid">
                            <div class="info-item">
                                <span class="label">商品名称:</span>
                                <span class="value">${product.name || '未知'}</span>
                            </div>
                            <div class="info-item">
                                <span class="label">商品ID:</span>
                                <span class="value">${product.id}</span>
                            </div>
                            <div class="info-item">
                                <span class="label">商品价格:</span>
                                <span class="value">¥${product.price || 0}</span>
                            </div>
                            <div class="info-item">
                                <span class="label">商品分类:</span>
                                <span class="value">${product.category || '未分类'}</span>
                            </div>
                        </div>
                    </div>

                    <div class="product-time-series">
                        <h4>时间序列数据</h4>
                        <table class="details-table">
                            <thead>
                                <tr>
                                    <th>字段名称</th>
                                    <th>字段值</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${fieldsHtml}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="window.dataManagerApp.closeModal()">关闭</button>
                </div>
            </div>
        `;
    }

    /**
     * 创建简化异常商品项（保留用于兼容性）
     */
    createSimpleAnomalyItem(anomaly) {
        const types = [];
        if (anomaly.isSalesAnomaly) types.push('销量异常');
        if (anomaly.isRevenueAnomaly) types.push('销售额异常');
        const typeLabel = types.length > 0 ? types.join(' + ') : '未知异常';

        const crawlTime = anomaly.crawlTime ? this.formatTime(anomaly.crawlTime) : '未知时间';

        return `
            <div class="anomaly-item warning">
                <div class="anomaly-header">
                    <div class="anomaly-severity">
                        <span class="severity-icon">⚠️</span>
                        <span class="severity-text">${typeLabel}</span>
                    </div>
                    <div class="anomaly-time">${new Date().toLocaleString('zh-CN')}</div>
                </div>

                <div class="anomaly-details-grid">
                    <div class="detail-row">
                        <div class="detail-item">
                            <span class="detail-label">商品名称:</span>
                            <span class="detail-value">${anomaly.productName || '未知商品'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">商品价格:</span>
                            <span class="detail-value">¥${anomaly.productPrice || 0}</span>
                        </div>
                    </div>

                    <div class="detail-row">
                        <div class="detail-item">
                            <span class="detail-label">商品分类:</span>
                            <span class="detail-value">${anomaly.categoryName || '未分类'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">爬取时间(最新):</span>
                            <span class="detail-value">${crawlTime}</span>
                        </div>
                    </div>

                    <div class="detail-row">
                        <div class="detail-item">
                            <span class="detail-label">当前销量(最新):</span>
                            <span class="detail-value">${anomaly.sales || 0}件</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">店铺销量(最新):</span>
                            <span class="detail-value">${anomaly.storeSales || 0}件</span>
                        </div>
                    </div>

                    <div class="detail-row">
                        <div class="detail-item">
                            <span class="detail-label">24h新增销量:</span>
                            <span class="detail-value ${anomaly.isSalesAnomaly ? 'anomaly-highlight' : ''}">${anomaly.sales24h || 0}件</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">24h新增销售额:</span>
                            <span class="detail-value ${anomaly.isRevenueAnomaly ? 'anomaly-highlight' : ''}">${anomaly.revenue24h || 0}元</span>
                        </div>
                    </div>

                    <div class="detail-row">
                        <div class="detail-item">
                            <span class="detail-label">阈值设置:</span>
                            <span class="detail-value">${anomaly.salesThreshold || 50}件 / ${anomaly.revenueThreshold || 500}元</span>
                        </div>
                    </div>
                </div>

                <div class="anomaly-description">${anomaly.description || '商品数据异常'}</div>
            </div>
        `;
    }

    // ==================== 导出功能实现 ====================

    /**
     * 打开导出配置对话框
     */
    async openExportDialog() {
        try {
            this.showLoading('正在加载导出配置...');
            
            // 初始化导出管理器
            if (!this.exportManager) {
                this.exportManager = new ExportManager(this.localDataManager, this.categoryManager);
            }
            
            // 获取当前配置和统计信息
            const [config, stats] = await Promise.all([
                this.exportManager.getExportConfig(),
                this.exportManager.getExportStats()
            ]);
            
            this.hideLoading();
            
            // 创建对话框HTML
            const dialogHtml = await this.createExportDialogHtml(config, stats);
            
            // 显示对话框
            this.showModal(dialogHtml);
            
            // 绑定对话框事件
            this.bindExportDialogEvents(config);
            
        } catch (error) {
            this.hideLoading();
            console.error('❌ 打开导出对话框失败:', error);
            this.showToast('error', '打开失败', error.message);
        }
    }

    /**
     * 创建导出对话框HTML
     */
    async createExportDialogHtml(config, stats) {
        const categoryOptions = stats.categoryStats.map(cat => 
            `<option value="${cat.id}" ${config.selectedCategories.includes(cat.id) ? 'selected' : ''}>
                ${cat.name} (${cat.count}件)
            </option>`
        ).join('');

        return `
            <div class="export-dialog">
                <div class="modal-header">
                    <h3 class="modal-title">📤 数据导出配置</h3>
                    <button class="modal-close" id="modalCloseBtn">&times;</button>
                </div>

                <div class="modal-body">
                    <div class="export-config">
                        <!-- 导出类型选择 -->
                        <div class="config-section">
                            <h4>导出范围</h4>
                            <div class="export-type-selection">
                                <label class="radio-option">
                                    <input type="radio" name="exportType" value="all" ${config.exportType === 'all' ? 'checked' : ''}>
                                    <span>全部数据 (${stats.totalProducts}件商品)</span>
                                </label>
                                <label class="radio-option">
                                    <input type="radio" name="exportType" value="category" ${config.exportType === 'category' ? 'checked' : ''}>
                                    <span>按分类导出</span>
                                </label>
                            </div>

                            <div id="categorySelection" class="category-selection" style="${config.exportType === 'category' ? '' : 'display: none;'}">
                                <select multiple id="selectedCategories" class="form-select">
                                    ${categoryOptions}
                                </select>
                            </div>
                        </div>

                        <!-- 字段选择 -->
                        <div class="config-section">
                            <h4>导出字段</h4>
                            <div class="field-selection">
                                <div class="field-group">
                                    <h5>基础字段</h5>
                                    <div class="field-checkboxes" id="basicFields">
                                        <!-- 将通过JavaScript动态填充 -->
                                    </div>
                                </div>

                                <div class="field-group">
                                    <h5>扩展字段</h5>
                                    <div class="field-checkboxes" id="additionalFields">
                                        <!-- 将通过JavaScript动态填充 -->
                                    </div>
                                </div>

                                <div class="field-group">
                                    <h5>增长数据</h5>
                                    <div class="field-checkboxes" id="growthFields">
                                        <!-- 将通过JavaScript动态填充 -->
                                    </div>
                                </div>

                                <div class="field-group">
                                    <label class="checkbox-option">
                                        <input type="checkbox" id="includeTimeSeriesData" ${config.includeTimeSeriesData ? 'checked' : ''}>
                                        <span>包含时间序列数据 (${stats.timeSeriesStats.uniqueDates}个日期)</span>
                                    </label>
                                </div>
                            </div>
                        </div>

                        <!-- 导出设置 -->
                        <div class="config-section">
                            <h4>导出设置</h4>
                            <div class="export-settings">
                                <div class="form-group">
                                    <label for="exportFilename">文件名（可选）</label>
                                    <input type="text" id="exportFilename" class="form-input" 
                                           value="${config.filename || ''}" 
                                           placeholder="留空自动生成时间戳文件名">
                                </div>
                            </div>
                        </div>

                        <!-- 预览 -->
                        <div class="config-section">
                            <h4>导出预览</h4>
                            <div class="export-preview">
                                <button type="button" class="btn btn-secondary" id="previewExportBtn">
                                    <span class="btn-icon">👁️</span>
                                    预览数据
                                </button>
                                <div id="exportPreviewContent" class="preview-content">
                                    <!-- 预览内容将在这里显示 -->
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="modal-footer">
                    <div class="export-actions">
                        <button type="button" class="btn btn-secondary" id="modalCancelBtn">取消</button>
                        <button type="button" class="btn btn-primary" id="saveConfigBtn">
                            <span class="btn-icon">💾</span>
                            保存配置
                        </button>
                        <button type="button" class="btn btn-success" id="exportNowBtn">
                            <span class="btn-icon">📤</span>
                            立即导出
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * 绑定导出对话框事件
     */
    bindExportDialogEvents(initialConfig) {
        // 导出类型切换
        document.querySelectorAll('input[name="exportType"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                const categorySelection = document.getElementById('categorySelection');
                if (e.target.value === 'category') {
                    categorySelection.style.display = 'block';
                } else {
                    categorySelection.style.display = 'none';
                }
            });
        });

        // 填充字段选择框
        this.populateFieldSelections(initialConfig.selectedFields);

        // 预览按钮
        const previewBtn = document.getElementById('previewExportBtn');
        previewBtn.addEventListener('click', () => {
            this.previewExportData();
        });

        // 保存配置按钮
        const saveConfigBtn = document.getElementById('saveConfigBtn');
        saveConfigBtn.addEventListener('click', () => {
            this.saveExportConfig();
        });

        // 导出按钮
        const exportNowBtn = document.getElementById('exportNowBtn');
        exportNowBtn.addEventListener('click', () => {
            this.executeExport();
        });
    }

    /**
     * 填充字段选择框
     * 🚀 性能优化：使用数组拼接替代 innerHTML +=，避免重复DOM解析
     */
    populateFieldSelections(selectedFields) {
        // 基础字段 - 使用数组拼接优化
        const basicFieldsContainer = document.getElementById('basicFields');
        const basicFieldsHtml = [];
        this.exportManager.availableFields.basic.forEach(field => {
            const isSelected = selectedFields.includes(field.key);
            basicFieldsHtml.push(`
                <label class="checkbox-option">
                    <input type="checkbox" name="selectedFields" value="${field.key}" ${isSelected ? 'checked' : ''}>
                    <span>${field.label}</span>
                </label>
            `);
        });
        basicFieldsContainer.innerHTML = basicFieldsHtml.join('');

        // 扩展字段 - 使用数组拼接优化
        const additionalFieldsContainer = document.getElementById('additionalFields');
        const additionalFieldsHtml = [];
        this.exportManager.availableFields.additional.forEach(field => {
            const isSelected = selectedFields.includes(field.key);
            additionalFieldsHtml.push(`
                <label class="checkbox-option">
                    <input type="checkbox" name="selectedFields" value="${field.key}" ${isSelected ? 'checked' : ''}>
                    <span>${field.label}</span>
                </label>
            `);
        });
        additionalFieldsContainer.innerHTML = additionalFieldsHtml.join('');

        // 增长数据字段 - 使用数组拼接优化
        const growthFieldsContainer = document.getElementById('growthFields');
        const growthFieldsHtml = [];
        this.exportManager.availableFields.growth.forEach(field => {
            const isSelected = selectedFields.includes(field.key);
            growthFieldsHtml.push(`
                <label class="checkbox-option">
                    <input type="checkbox" name="selectedFields" value="${field.key}" ${isSelected ? 'checked' : ''}>
                    <span>${field.label}</span>
                </label>
            `);
        });
        growthFieldsContainer.innerHTML = growthFieldsHtml.join('');
    }

    /**
     * 收集当前的导出配置
     */
    collectExportConfig() {
        const exportType = document.querySelector('input[name="exportType"]:checked')?.value || 'all';
        const selectedCategories = Array.from(document.getElementById('selectedCategories').selectedOptions)
            .map(option => parseInt(option.value));
        const selectedFields = Array.from(document.querySelectorAll('input[name="selectedFields"]:checked'))
            .map(input => input.value);
        const includeTimeSeriesData = document.getElementById('includeTimeSeriesData').checked;
        const filename = document.getElementById('exportFilename').value.trim();

        return {
            exportType,
            selectedCategories,
            selectedFields,
            includeTimeSeriesData,
            filename
        };
    }

    /**
     * 预览导出数据
     */
    async previewExportData() {
        try {
            const config = this.collectExportConfig();
            
            // 验证配置
            const validation = this.exportManager.validateExportConfig(config);
            if (!validation.isValid) {
                this.showToast('warning', '配置错误', validation.errors.join(', '));
                return;
            }

            this.showLoading('正在生成预览...');

            const preview = await this.exportManager.previewExportData(config, 3);
            this.hideLoading();

            if (preview.success) {
                this.displayPreview(preview);
            } else {
                this.showToast('error', '预览失败', preview.error);
            }

        } catch (error) {
            this.hideLoading();
            console.error('❌ 预览失败:', error);
            this.showToast('error', '预览失败', error.message);
        }
    }

    /**
     * 显示预览数据
     */
    displayPreview(preview) {
        const previewContainer = document.getElementById('exportPreviewContent');
        
        if (preview.preview.length === 0) {
            previewContainer.innerHTML = '<p class="text-muted">没有找到匹配的数据</p>';
            return;
        }

        // 创建预览表格
        let tableHtml = `
            <div class="preview-info">
                <p>预览前3条记录，总计 ${preview.totalCount} 条数据</p>
            </div>
            <div class="preview-table-container">
                <table class="preview-table">
                    <thead>
                        <tr>
                            ${preview.headers.map(header => `<th>${header}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
        `;

        preview.preview.forEach(row => {
            tableHtml += '<tr>';
            preview.headers.forEach(header => {
                const cellValue = row[header] || '';
                const displayValue = String(cellValue).length > 30 ? 
                    String(cellValue).substring(0, 30) + '...' : cellValue;
                tableHtml += `<td title="${cellValue}">${displayValue}</td>`;
            });
            tableHtml += '</tr>';
        });

        tableHtml += `
                    </tbody>
                </table>
            </div>
        `;

        previewContainer.innerHTML = tableHtml;
    }

    /**
     * 保存导出配置
     */
    async saveExportConfig() {
        try {
            const config = this.collectExportConfig();
            
            // 验证配置
            const validation = this.exportManager.validateExportConfig(config);
            if (!validation.isValid) {
                this.showToast('warning', '配置错误', validation.errors.join(', '));
                return;
            }

            this.showLoading('正在保存配置...');
            await this.exportManager.saveExportConfig(config);
            this.hideLoading();

            this.showToast('success', '保存成功', '导出配置已保存');

        } catch (error) {
            this.hideLoading();
            console.error('❌ 保存配置失败:', error);
            this.showToast('error', '保存失败', error.message);
        }
    }

    /**
     * 执行导出
     */
    async executeExport() {
        try {
            const config = this.collectExportConfig();
            
            // 验证配置
            const validation = this.exportManager.validateExportConfig(config);
            if (!validation.isValid) {
                this.showToast('warning', '配置错误', validation.errors.join(', '));
                return;
            }

            this.showLoading('正在导出数据...');
            
            const result = await this.exportManager.exportToExcel(config);
            
            this.hideLoading();
            this.closeModal();

            this.showToast('success', '导出成功', 
                `文件：${result.filename}，共 ${result.recordCount} 条记录`);

        } catch (error) {
            this.hideLoading();
            console.error('❌ 导出失败:', error);
            this.showToast('error', '导出失败', error.message);
        }
    }

    /**
     * 🔬 系统诊断：事件系统完整性检查
     */
    diagnoseEventSystemIntegrity() {
        console.log('🔬 === 深度事件系统诊断 ===');
        
        // 1. 关键按钮元素检查
        const criticalButtons = [
            'batchDeleteBtn',
            'exportProductsBtn',
            'exportAllBtn',
            'refreshDataBtn',
            'addCategoryBtn'
        ];
        
        console.log('🔘 关键按钮存在性检查:');
        criticalButtons.forEach(btnId => {
            const btn = document.getElementById(btnId);
            console.log(`  ${btnId}:`, {
                exists: !!btn,
                eventsBound: btn?.dataset?.eventsBound || 'none',
                listenersCount: btn ? this.getEventListenersCount(btn) : 0,
                disabled: btn?.disabled,
                visible: btn ? btn.offsetHeight > 0 : false
            });
        });
        
        // 2. 事件绑定历史跟踪
        if (!window._eventBindingHistory) {
            window._eventBindingHistory = [];
        }
        
        console.log('📚 事件绑定历史:', window._eventBindingHistory.slice(-10));
        
        // 3. DOM变更观察
        if (!this._domObserver) {
            this._domObserver = new MutationObserver((mutations) => {
                mutations.forEach(mutation => {
                    if (mutation.type === 'childList') {
                        mutation.addedNodes.forEach(node => {
                            if (node.nodeType === 1 && (node.id || node.className)) {
                                console.log('🔄 DOM元素添加:', {
                                    element: `${node.tagName}${node.id ? '#' + node.id : ''}${node.className ? '.' + node.className.split(' ')[0] : ''}`,
                                    timestamp: Date.now()
                                });
                            }
                        });
                        
                        mutation.removedNodes.forEach(node => {
                            if (node.nodeType === 1 && (node.id || node.className)) {
                                console.log('❌ DOM元素移除:', {
                                    element: `${node.tagName}${node.id ? '#' + node.id : ''}${node.className ? '.' + node.className.split(' ')[0] : ''}`,
                                    timestamp: Date.now()
                                });
                            }
                        });
                    }
                });
            });
            
            this._domObserver.observe(document.body, {
                childList: true,
                subtree: true
            });
            
            console.log('👁️ DOM变更观察器已启用');
        }
        
        // 4. 全局错误监听
        if (!window._errorTracking) {
            window._errorTracking = [];
            
            window.addEventListener('error', (event) => {
                const errorInfo = {
                    message: event.message,
                    filename: event.filename,
                    lineno: event.lineno,
                    timestamp: Date.now(),
                    stack: event.error?.stack
                };
                window._errorTracking.push(errorInfo);
                console.error('🚨 JavaScript错误:', errorInfo);
            });
            
            window.addEventListener('unhandledrejection', (event) => {
                const errorInfo = {
                    reason: event.reason,
                    timestamp: Date.now(),
                    type: 'unhandledrejection'
                };
                window._errorTracking.push(errorInfo);
                console.error('🚨 未处理Promise拒绝:', errorInfo);
            });
            
            console.log('🚨 全局错误监听器已启用');
        }
        
        // 5. 事件系统健康度评估
        const healthScore = this.calculateEventSystemHealth();
        console.log('💊 事件系统健康度:', healthScore);
        
        // 6. 双重绑定检测
        console.log('🔄 bindProductPageEvents调用统计:');
        if (!window._bindProductPageEventsCount) {
            window._bindProductPageEventsCount = 0;
        }
        console.log(`  调用次数: ${window._bindProductPageEventsCount}`);
        
        console.log('🔬 === 事件系统诊断完成 ===');
    }
    
    /**
     * 计算事件系统健康度
     */
    calculateEventSystemHealth() {
        let score = 100;
        let issues = [];
        
        // 检查关键按钮
        const criticalButtons = ['batchDeleteBtn', 'exportProductsBtn'];
        criticalButtons.forEach(btnId => {
            const btn = document.getElementById(btnId);
            if (!btn) {
                score -= 20;
                issues.push(`缺少关键按钮: ${btnId}`);
            } else if (btn.disabled) {
                score -= 10;
                issues.push(`按钮被禁用: ${btnId}`);
            }
        });
        
        // 检查全局错误
        if (window._errorTracking && window._errorTracking.length > 0) {
            score -= Math.min(30, window._errorTracking.length * 5);
            issues.push(`发现${window._errorTracking.length}个JavaScript错误`);
        }
        
        return {
            score: Math.max(0, score),
            issues: issues,
            status: score >= 80 ? '良好' : score >= 60 ? '警告' : '严重'
        };
    }
    
    /**
     * 获取元素的事件监听器数量（近似）
     */
    getEventListenersCount(element) {
        // 这是一个近似方法，因为浏览器不直接暴露事件监听器信息
        if (!element._eventListeners) return '未知';
        return Object.keys(element._eventListeners).length;
    }

    /**
     * 验证时间序列功能修复是否成功
     */
    async validateTimeSeriesFix() {
        console.log('🔍 开始验证时间序列功能修复...');

        try {
            // 1. 验证关键类加载
            const coreClasses = {
                'DateFormatter': DateFormatter,
                'SimpleGrowthCalculator': SimpleGrowthCalculator,
                'TimeSeriesDataManager': TimeSeriesDataManager
            };

            for (const [name, clazz] of Object.entries(coreClasses)) {
                if (typeof clazz === 'function') {
                    console.log(`✅ ${name} 已正确加载`);
                } else {
                    console.error(`❌ ${name} 加载失败:`, typeof clazz);
                    throw new Error(`关键依赖 ${name} 加载失败`);
                }
            }

            // 2. 验证数据管理器初始化
            if (!this.localDataManager) {
                throw new Error('LocalDataManager 未初始化');
            }

            // 3. 验证时间序列管理器
            if (this.localDataManager.timeSeriesManager &&
                this.localDataManager.timeSeriesManager instanceof TimeSeriesDataManager) {
                console.log('✅ TimeSeriesDataManager 实例化成功');
            } else {
                console.warn('⚠️ TimeSeriesDataManager 未正确实例化，尝试手动初始化...');
                this.localDataManager.timeSeriesManager = new TimeSeriesDataManager();
            }

            // 4. 验证导出管理器
            if (!this.exportManager) {
                console.log('🔄 初始化 ExportManager...');
                this.exportManager = new ExportManager(this.localDataManager, this.categoryManager);
            }

            // 5. 测试时间序列数据统计
            console.log('🔄 测试时间序列数据统计...');
            const stats = await this.exportManager.getExportStats();

            console.log('📊 时间序列统计结果:', stats.timeSeriesStats);

            if (stats.timeSeriesStats.uniqueDates > 0) {
                console.log(`✅ 时间序列修复成功！检测到 ${stats.timeSeriesStats.uniqueDates} 个日期的数据`);
                this.showToast('success', '修复成功', `时间序列功能已恢复，检测到${stats.timeSeriesStats.uniqueDates}个日期的数据`);
            } else {
                console.warn('⚠️ 时间序列数据统计仍为0，可能需要进一步检查');
                this.showToast('warning', '部分修复', '服务已恢复，但时间序列数据统计仍需检查');
            }

            // 6. 验证数据访问链路
            console.log('🔄 验证数据访问链路...');
            const products = await this.localDataManager.getAllProducts();
            console.log(`📊 成功读取 ${products.length} 条商品记录`);

            if (products.length > 0) {
                const firstProduct = products[0];
                const timeSeriesFields = Object.keys(firstProduct).filter(key =>
                    key.includes('销量（') || key.includes('店铺（') || key.includes('爬取（') ||
                    key.includes('新增销量') || key.includes('新增销售额')
                );
                console.log(`✅ 首条记录包含 ${timeSeriesFields.length} 个时间序列字段:`, timeSeriesFields);
            }

            console.log('🎉 时间序列功能修复验证完成！');
            return true;

        } catch (error) {
            console.error('❌ 时间序列功能验证失败:', error);
            this.showToast('error', '验证失败', `时间序列功能验证失败: ${error.message}`);
            return false;
        }
    }

    // ==================== 分类编辑功能方法 ====================

    /**
     * 显示分类选择浮层
     * @param {Event} event - 点击事件对象
     * @param {number} productId - 商品ID
     * @param {number} currentCategoryId - 当前分类ID
     */
    async showCategoryFloatSelector(event, productId, currentCategoryId) {
        try {
            // 保存编辑上下文
            this.editingCategoryContext = {
                productId: productId,
                oldCategoryId: currentCategoryId
            };

            // 获取所有分类
            const categories = await this.categoryManager.getAllCategories();

            // 检查是否有分类
            const listContainer = document.getElementById('categoryFloatList');
            if (!categories || categories.length === 0) {
                listContainer.innerHTML = '<div class="category-empty">暂无分类</div>';
            } else {
                // 渲染分类列表
                listContainer.innerHTML = categories.map(cat => `
                    <div class="category-item ${cat.id === currentCategoryId ? 'active' : ''}"
                         data-category-id="${cat.id}">
                        <span class="category-name" title="${cat.name}">${cat.name}</span>
                        ${cat.id === currentCategoryId ? '<span class="check-icon">✓</span>' : ''}
                    </div>
                `).join('');

                // 绑定点击事件
                listContainer.querySelectorAll('.category-item').forEach(item => {
                    item.addEventListener('click', (e) => {
                        const newCategoryId = parseInt(e.currentTarget.dataset.categoryId);
                        this.handleCategoryChange(productId, currentCategoryId, newCategoryId);
                    });
                });
            }

            // 定位并显示浮层
            const floatSelector = document.getElementById('categoryFloatSelector');
            this.positionFloatSelector(event.target, floatSelector);
            floatSelector.style.display = 'flex';

            // 添加点击外部关闭事件（延迟添加，避免立即触发）
            setTimeout(() => {
                document.addEventListener('click', this.outsideClickHandler);
            }, 100);

        } catch (error) {
            console.error('显示分类浮层失败:', error);
            this.showToast('error', '打开分类选择失败');
        }
    }

    /**
     * 定位浮层元素（防溢出）
     * @param {HTMLElement} triggerElement - 触发元素（分类文字）
     * @param {HTMLElement} floatSelector - 浮层元素
     */
    positionFloatSelector(triggerElement, floatSelector) {
        const rect = triggerElement.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;

        // 临时显示以获取尺寸
        floatSelector.style.display = 'flex';
        floatSelector.style.visibility = 'hidden';
        const floatWidth = floatSelector.offsetWidth;
        const floatHeight = floatSelector.offsetHeight;
        floatSelector.style.visibility = 'visible';

        // 默认位置：分类文字下方
        let left = rect.left;
        let top = rect.bottom + 6;

        // 右侧溢出检测
        if (left + floatWidth > viewportWidth - 20) {
            left = viewportWidth - floatWidth - 20;
        }

        // 左侧溢出检测
        if (left < 20) {
            left = 20;
        }

        // 底部溢出检测 - 显示在分类文字上方
        if (top + floatHeight > viewportHeight - 20) {
            top = rect.top - floatHeight - 6;
        }

        // 顶部溢出检测
        if (top < 20) {
            top = 20;
        }

        // 应用定位
        floatSelector.style.position = 'fixed';
        floatSelector.style.left = left + 'px';
        floatSelector.style.top = top + 'px';
    }

    /**
     * 处理分类变更（自动保存）
     * @param {number} productId - 商品ID
     * @param {number} oldCategoryId - 原分类ID
     * @param {number} newCategoryId - 新分类ID
     */
    async handleCategoryChange(productId, oldCategoryId, newCategoryId) {
        // 检查是否变化
        if (newCategoryId === oldCategoryId) {
            this.hideCategoryFloatSelector();
            return;
        }

        try {
            // 显示加载状态
            const floatSelector = document.getElementById('categoryFloatSelector');
            floatSelector.classList.add('loading');

            // 获取完整商品对象
            const response = await this.localDataManager.getProduct(productId);
            if (!response.success || !response.product) {
                throw new Error('商品不存在');
            }

            // 提取商品对象
            const product = response.product;

            // 更新分类ID
            product.category_id = newCategoryId;
            product.updated_at = new Date().toISOString();

            // 保存到数据库
            await this.localDataManager.updateProduct(product);

            // 同步状态到其他页面
            if (this.stateSyncManager) {
                await this.stateSyncManager.syncProductState('update', {
                    productId: productId,
                    categoryIds: [oldCategoryId, newCategoryId],
                    operation: 'category_change'
                });
            }

            // 关闭浮层
            this.hideCategoryFloatSelector();

            // 刷新商品列表（实时更新显示）
            await this.loadProductsData();

            // 刷新分类树（更新商品数量）
            await this.loadCategoryTree();

            // 显示成功提示
            this.showToast('success', '更新成功', '商品分类已修改');

            console.log(`✅ 商品 ${productId} 分类已从 ${oldCategoryId} 更新为 ${newCategoryId}`);

        } catch (error) {
            console.error('分类更新失败:', error);
            this.showToast('error', '更新失败', error.message);
            this.hideCategoryFloatSelector();
        }
    }

    /**
     * 隐藏分类选择浮层
     */
    hideCategoryFloatSelector() {
        const floatSelector = document.getElementById('categoryFloatSelector');
        if (floatSelector) {
            floatSelector.style.display = 'none';
            floatSelector.classList.remove('loading');
        }
        this.editingCategoryContext = null;

        // 移除点击外部关闭事件
        document.removeEventListener('click', this.outsideClickHandler);
    }
}

// 全局应用实例
let app;

// DOM加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    app = new DataManagerApp();
    // 暴露到全局作用域，供侧边栏调用
    window.dataManagerApp = app;
});

// 全局错误处理
window.addEventListener('error', (event) => {
    console.error('全局错误:', event.error);
    if (app) {
        app.showToast('error', '系统错误', '发生未预期的错误，请刷新页面重试');
    }
});

/**
 * 全局函数：获取并显示异常商品
 * 用于在跨页面通信失败时手动刷新异常商品显示
 */
window.refreshAnomalyDisplay = async function() {
    if (!window.dataManagerApp) {
        console.error('❌ 数据管理器尚未初始化');
        return;
    }

    try {
        console.log('🔄 手动刷新异常商品显示...');

        // 从数据库获取商品数据
        const result = await window.dataManagerApp.sharedDataService.localDataManager.getProducts();
        const products = result.products || [];

        // 查找标记为异常的商品
        const anomalousProducts = products.filter(p => p.is_anomaly === true);
        console.log(`📊 找到 ${anomalousProducts.length} 个标记为异常的商品`);

        if (anomalousProducts.length > 0) {
            // 构造检测结果数据格式
            const mockResult = {
                success: true,
                checkedCount: products.length,
                anomaliesFound: anomalousProducts.length,
                anomalies: anomalousProducts.map(product => ({
                    product_id: product.id,
                    product_name: product.title || '未知商品',
                    product_price: product.price || 0,
                    category_name: '未分类',
                    current_sales: product.sales || 0,
                    store_sales: product.storeSales || 0,
                    crawl_time: product.crawl_time || product.extracted_at || new Date().toISOString(),
                    sales_24h: product.sales_24h || 0,
                    revenue_24h: product.revenue_24h || 0,
                    is_sales_anomaly: true,
                    is_revenue_anomaly: true,
                    sales_threshold: 50,
                    revenue_threshold: 500
                })),
                thresholds: { sales: 50, revenue: 500 },
                detectionTime: new Date().toISOString()
            };

            // 切换到异常监控页面并显示结果
            window.dataManagerApp.switchView('anomalies');
            window.dataManagerApp.displayAnomalyDetectionResults(mockResult);

            console.log(`✅ 成功显示 ${anomalousProducts.length} 个异常商品`);
            window.dataManagerApp.showToast('success', '刷新成功', `已显示 ${anomalousProducts.length} 个异常商品`);
        } else {
            console.log('ℹ️ 当前没有标记为异常的商品');
            window.dataManagerApp.showToast('info', '无异常商品', '当前数据库中没有标记为异常的商品');
        }
    } catch (error) {
        console.error('❌ 刷新异常商品显示失败:', error);
        if (window.dataManagerApp) {
            window.dataManagerApp.showToast('error', '刷新失败', `刷新异常商品显示失败: ${error.message}`);
        }
    }
};

// 导出全局访问
window.app = app;