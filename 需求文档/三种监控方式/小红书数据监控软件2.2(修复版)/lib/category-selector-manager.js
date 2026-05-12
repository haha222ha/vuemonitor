/**
 * 分类选择器管理器
 * 统一管理批量监控和异常检测功能的分类选择器
 * 提供可复用的分类选择UI逻辑和状态管理
 */
class CategorySelectorManager {
    constructor(options = {}) {
        this.options = {
            containerId: options.containerId || 'category-selector-container',
            multiple: options.multiple !== false, // 默认支持多选
            includeSelectAll: options.includeSelectAll !== false, // 默认包含"全选"选项
            showProductCount: options.showProductCount !== false, // 默认显示商品数量
            theme: options.theme || 'default', // UI主题
            onSelectionChange: options.onSelectionChange || null, // 选择变化回调
            filterEmptyCategories: options.filterEmptyCategories || false // 是否过滤空分类
        };

        this.dataManager = null;
        this.categoryManager = null;
        this.isInitialized = false;
        this.currentSelection = new Set(); // 当前选中的分类ID
        this.categories = []; // 缓存的分类列表
        this.container = null; // DOM容器元素

        console.log('🎛️ 分类选择器管理器已创建', this.options);
    }

    /**
     * 初始化管理器
     */
    async init(dataManager = null, categoryManager = null) {
        try {
            console.log('🔧 初始化分类选择器管理器...');

            // 初始化数据管理器
            if (dataManager) {
                this.dataManager = dataManager;
            } else {
                this.dataManager = new LocalDataManager();
                await this.dataManager.init();
            }

            // 初始化分类管理器
            if (categoryManager) {
                this.categoryManager = categoryManager;
            } else {
                this.categoryManager = new CategoryManager();
                await this.categoryManager.init();
            }

            // 🔧 修复：不再在init阶段获取容器，而是在render时获取
            // 这样可以支持多个不同的容器使用同一个管理器实例

            // 加载分类数据
            await this.loadCategories();

            // 监听分类变化事件
            this.setupEventListeners();

            this.isInitialized = true;
            console.log('✅ 分类选择器管理器初始化完成');

        } catch (error) {
            console.error('❌ 分类选择器管理器初始化失败:', error);
            throw error;
        }
    }

    /**
     * 加载分类数据
     */
    async loadCategories() {
        try {
            const allCategories = await this.categoryManager.getAllCategories();

            // 过滤空分类（如果启用）
            if (this.options.filterEmptyCategories) {
                this.categories = allCategories.filter(cat => cat.product_count > 0);
            } else {
                this.categories = allCategories;
            }

            console.log(`📂 已加载 ${this.categories.length} 个分类`);
            return this.categories;

        } catch (error) {
            console.error('❌ 加载分类数据失败:', error);
            this.categories = [];
            throw error;
        }
    }

    /**
     * 渲染分类选择器UI
     */
    async render(containerElement = null) {
        if (!this.isInitialized) {
            throw new Error('管理器未初始化，请先调用init()方法');
        }

        try {
            // 🔧 修复：支持动态容器参数
            let targetContainer = containerElement;

            if (!targetContainer) {
                // 如果没有传入容器，尝试使用配置的容器ID
                targetContainer = document.getElementById(this.options.containerId);
            }

            if (!targetContainer) {
                throw new Error(`找不到容器元素。请传入容器元素或确保存在ID为'${this.options.containerId}'的元素`);
            }

            // 设置当前容器（用于事件处理等）
            this.container = targetContainer;

            await this.loadCategories(); // 确保数据是最新的

            const html = this.generateSelectorHTML();
            this.container.innerHTML = html;

            // 绑定事件处理器
            this.bindEventHandlers();

            // 恢复之前的选择状态
            this.restoreSelection();

            console.log('🎨 分类选择器UI渲染完成');

        } catch (error) {
            console.error('❌ 渲染分类选择器失败:', error);

            // 如果有容器，显示错误信息
            if (this.container || containerElement) {
                const errorContainer = this.container || containerElement;
                errorContainer.innerHTML = `<div class="error-message">加载分类选择器失败: ${error.message}</div>`;
            }

            throw error;
        }
    }

    /**
     * 生成选择器HTML
     */
    generateSelectorHTML() {
        let html = '<div class="category-selector-wrapper">';

        // 标题和全选按钮
        html += '<div class="selector-header">';
        html += '<h4 class="selector-title">选择分类</h4>';

        if (this.options.includeSelectAll && this.categories.length > 0) {
            html += `
                <div class="select-all-controls">
                    <button type="button" class="btn-select-all" data-action="select-all">
                        全选 (${this.categories.length})
                    </button>
                    <button type="button" class="btn-clear-all" data-action="clear-all">
                        清空
                    </button>
                </div>
            `;
        }
        html += '</div>';

        // 分类列表
        html += '<div class="category-list">';

        if (this.categories.length === 0) {
            html += '<div class="empty-message">暂无可用分类</div>';
        } else {
            this.categories.forEach(category => {
                const inputType = this.options.multiple ? 'checkbox' : 'radio';
                const productCountText = this.options.showProductCount ?
                    `<span class="product-count">(${category.product_count || 0})</span>` : '';

                html += `
                    <label class="category-item" data-category-id="${category.id}">
                        <input type="${inputType}"
                               name="category-selection"
                               value="${category.id}"
                               class="category-checkbox">
                        <span class="category-color" style="background-color: ${category.color || '#666'}"></span>
                        <span class="category-name">${category.name}</span>
                        ${productCountText}
                    </label>
                `;
            });
        }

        html += '</div>';

        // 选择状态显示
        html += '<div class="selection-status">';
        html += '<span class="selected-count">已选择: <strong>0</strong> 个分类</span>';
        html += '</div>';

        html += '</div>';

        return html;
    }

    /**
     * 绑定事件处理器
     */
    bindEventHandlers() {
        const container = this.container;

        // 分类选择变化
        container.addEventListener('change', (e) => {
            if (e.target.classList.contains('category-checkbox')) {
                this.handleSelectionChange(e);
            }
        });

        // 全选/清空按钮
        container.addEventListener('click', (e) => {
            if (e.target.hasAttribute('data-action')) {
                const action = e.target.getAttribute('data-action');

                if (action === 'select-all') {
                    this.selectAll();
                } else if (action === 'clear-all') {
                    this.clearAll();
                }
            }
        });
    }

    /**
     * 处理选择变化
     */
    handleSelectionChange(event) {
        const categoryId = parseInt(event.target.value);

        if (this.options.multiple) {
            // 多选模式
            if (event.target.checked) {
                this.currentSelection.add(categoryId);
            } else {
                this.currentSelection.delete(categoryId);
            }
        } else {
            // 单选模式
            this.currentSelection.clear();
            if (event.target.checked) {
                this.currentSelection.add(categoryId);
            }
        }

        this.updateUI();
        this.notifySelectionChange();
    }

    /**
     * 全选分类
     */
    selectAll() {
        if (!this.options.multiple) return;

        this.categories.forEach(category => {
            this.currentSelection.add(category.id);
        });

        this.updateUI();
        this.notifySelectionChange();
    }

    /**
     * 清空选择
     */
    clearAll() {
        this.currentSelection.clear();
        this.updateUI();
        this.notifySelectionChange();
    }

    /**
     * 更新UI状态
     */
    updateUI() {
        const container = this.container;

        // 更新复选框状态
        const checkboxes = container.querySelectorAll('.category-checkbox');
        checkboxes.forEach(checkbox => {
            const categoryId = parseInt(checkbox.value);
            checkbox.checked = this.currentSelection.has(categoryId);
        });

        // 更新选择计数
        const countElement = container.querySelector('.selected-count strong');
        if (countElement) {
            countElement.textContent = this.currentSelection.size;
        }

        // 更新全选按钮状态
        const selectAllBtn = container.querySelector('.btn-select-all');
        if (selectAllBtn && this.options.multiple) {
            const isAllSelected = this.currentSelection.size === this.categories.length;
            selectAllBtn.textContent = isAllSelected ?
                `取消全选 (${this.categories.length})` :
                `全选 (${this.categories.length})`;
            selectAllBtn.setAttribute('data-action', isAllSelected ? 'clear-all' : 'select-all');
        }
    }

    /**
     * 恢复之前的选择状态
     */
    restoreSelection() {
        this.updateUI();
    }

    /**
     * 通知选择变化
     */
    notifySelectionChange() {
        const selectionData = {
            selectedIds: Array.from(this.currentSelection),
            selectedCategories: this.categories.filter(cat => this.currentSelection.has(cat.id)),
            selectionCount: this.currentSelection.size
        };

        // 调用回调函数
        if (typeof this.options.onSelectionChange === 'function') {
            this.options.onSelectionChange(selectionData);
        }

        // 触发自定义事件
        const event = new CustomEvent('categorySelectionChanged', {
            detail: selectionData
        });
        this.container.dispatchEvent(event);

        console.log('📋 分类选择已更新:', selectionData);
    }

    /**
     * 设置事件监听器
     */
    setupEventListeners() {
        // 监听分类变化事件
        window.addEventListener('categoryChanged', (e) => {
            console.log('🔄 检测到分类变化，重新加载分类列表');
            this.render(); // 重新渲染
        });
    }

    /**
     * 获取当前选中的分类ID数组
     */
    getSelectedIds() {
        return Array.from(this.currentSelection);
    }

    /**
     * 获取当前选中的分类对象数组
     */
    getSelectedCategories() {
        return this.categories.filter(cat => this.currentSelection.has(cat.id));
    }

    /**
     * 程序化设置选中的分类
     */
    setSelection(categoryIds) {
        this.currentSelection.clear();

        if (Array.isArray(categoryIds)) {
            categoryIds.forEach(id => {
                if (typeof id === 'number' || typeof id === 'string') {
                    this.currentSelection.add(parseInt(id));
                }
            });
        }

        this.updateUI();
        this.notifySelectionChange();
    }

    /**
     * 清理和销毁
     */
    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
        }
        this.currentSelection.clear();
        this.categories = [];
        this.isInitialized = false;

        console.log('🧹 分类选择器管理器已销毁');
    }

    /**
     * 获取选择器状态信息
     */
    getState() {
        return {
            isInitialized: this.isInitialized,
            selectedCount: this.currentSelection.size,
            totalCategories: this.categories.length,
            selectedIds: Array.from(this.currentSelection),
            options: this.options
        };
    }

    /**
     * 重新加载并刷新
     */
    async refresh() {
        if (!this.isInitialized) return;

        try {
            await this.loadCategories();
            await this.render();
            console.log('🔄 分类选择器已刷新');
        } catch (error) {
            console.error('❌ 刷新分类选择器失败:', error);
        }
    }

    /**
     * 检查是否有选中的分类
     */
    hasSelection() {
        return this.currentSelection.size > 0;
    }

    /**
     * 获取选择摘要文本
     */
    getSelectionSummary() {
        if (this.currentSelection.size === 0) {
            return '未选择任何分类';
        }

        if (this.currentSelection.size === 1) {
            const selectedCategory = this.categories.find(cat => this.currentSelection.has(cat.id));
            return selectedCategory ? selectedCategory.name : '已选择1个分类';
        }

        if (this.currentSelection.size === this.categories.length) {
            return '已选择全部分类';
        }

        return `已选择${this.currentSelection.size}个分类`;
    }
}

// 浏览器环境导出
if (typeof window !== 'undefined') {
    window.CategorySelectorManager = CategorySelectorManager;
}

// Node.js环境导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CategorySelectorManager;
}