/**
 * 统一数据服务管理器 - 单例模式
 * 解决sidepanel和data-manager双实例问题，提供统一的数据访问接口
 * 
 * @version 2.0
 * @author AI Assistant
 */

class SharedDataService {
    static instance = null;
    
    constructor() {
        if (SharedDataService.instance) {
            return SharedDataService.instance;
        }
        
        // 初始化状态
        this.isInitialized = false;
        this.initPromise = null;
        
        // 数据服务组件
        this.localDataManager = null;
        this.categoryManager = null;
        this.dataMigrator = null;
        this.simpleAnomalyDetector = null;
        this.categorySelectorManager = null;
        
        // 事件监听器
        this.eventListeners = new Map();
        
        SharedDataService.instance = this;
        
        console.log('🔧 SharedDataService 单例实例已创建');
    }
    
    /**
     * 获取单例实例
     */
    static getInstance() {
        if (!this.instance) {
            this.instance = new SharedDataService();
        }
        return this.instance;
    }
    
    /**
     * 初始化数据服务 - 确保只初始化一次
     */
    async init() {
        // 如果已经初始化，直接返回
        if (this.isInitialized) {
            return this;
        }
        
        // 如果正在初始化，等待完成
        if (this.initPromise) {
            return await this.initPromise;
        }
        
        // 开始初始化过程
        this.initPromise = this._doInit();
        
        try {
            await this.initPromise;
            this.isInitialized = true;
            console.log('✅ SharedDataService 初始化完成');
            this.emit('initialized', { success: true });
            return this;
        } catch (error) {
            console.error('❌ SharedDataService 初始化失败:', error);
            this.emit('initialized', { success: false, error });
            throw error;
        }
    }
    
    /**
     * 实际的初始化逻辑
     */
    async _doInit() {
        console.log('🔧 开始初始化统一数据服务...');
        
        // 1. 初始化本地数据管理器
        console.log('📦 初始化本地数据管理器...');
        this.localDataManager = new LocalDataManager();
        await this.localDataManager.init();
        
        // 2. 初始化分类管理器
        console.log('🏷️ 初始化分类管理器...');
        this.categoryManager = new CategoryManager(this.localDataManager);
        this.categoryManager.isSimpleMode = true;
        this.categoryManager.dataManager = this.localDataManager;
        await this.categoryManager.init();
        
        // 3. 初始化数据迁移器
        console.log('🔄 初始化数据迁移器...');
        this.dataMigrator = new DataMigrator(this.localDataManager);
        
        // 4. 初始化简化异常检测器
        console.log('🔍 初始化简化异常检测器...');
        this.simpleAnomalyDetector = new SimpleAnomalyDetector();

        // 5. 初始化分类选择器管理器
        console.log('🎛️ 初始化分类选择器管理器...');
        this.categorySelectorManager = new CategorySelectorManager();
        
        console.log('✅ 所有数据服务组件初始化完成');
    }
    
    /**
     * 获取本地数据管理器
     */
    getLocalDataManager() {
        this._ensureInitialized();
        return this.localDataManager;
    }
    
    /**
     * 获取分类管理器
     */
    getCategoryManager() {
        this._ensureInitialized();
        return this.categoryManager;
    }
    
    /**
     * 获取数据迁移器
     */
    getDataMigrator() {
        this._ensureInitialized();
        return this.dataMigrator;
    }
    
    /**
     * 获取简化异常检测器
     */
    getSimpleAnomalyDetector() {
        this._ensureInitialized();
        return this.simpleAnomalyDetector;
    }

    /**
     * 获取分类选择器管理器
     */
    getCategorySelectorManager() {
        this._ensureInitialized();
        return this.categorySelectorManager;
    }

    /**
     * 向后兼容：获取异常检测器 (返回简化版本)
     */
    getAnomalyDetector() {
        console.warn('⚠️ getAnomalyDetector() 已废弃，请使用 getSimpleAnomalyDetector()');
        return this.getSimpleAnomalyDetector();
    }
    
    /**
     * 确保已初始化
     */
    _ensureInitialized() {
        if (!this.isInitialized) {
            throw new Error('SharedDataService 尚未初始化，请先调用 init() 方法');
        }
    }
    
    /**
     * 事件监听
     */
    on(event, listener) {
        if (!this.eventListeners.has(event)) {
            this.eventListeners.set(event, []);
        }
        this.eventListeners.get(event).push(listener);
    }
    
    /**
     * 移除事件监听
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
                    console.error(`事件监听器执行失败 [${event}]:`, error);
                }
            });
        }
    }
    
    /**
     * 获取初始化状态
     */
    getInitializationStatus() {
        return {
            isInitialized: this.isInitialized,
            isInitializing: !!this.initPromise && !this.isInitialized,
            components: {
                localDataManager: !!this.localDataManager,
                categoryManager: !!this.categoryManager,
                dataMigrator: !!this.dataMigrator,
                simpleAnomalyDetector: !!this.simpleAnomalyDetector,
                categorySelectorManager: !!this.categorySelectorManager
            }
        };
    }
    
    /**
     * 重置服务 - 仅用于测试
     */
    static _resetForTesting() {
        if (this.instance) {
            this.instance.isInitialized = false;
            this.instance.initPromise = null;
            this.instance.localDataManager = null;
            this.instance.categoryManager = null;
            this.instance.dataMigrator = null;
            this.instance.simpleAnomalyDetector = null;
            this.instance.categorySelectorManager = null;
            this.instance.eventListeners.clear();
        }
        this.instance = null;
    }
}

// 全局导出
if (typeof window !== 'undefined') {
    window.SharedDataService = SharedDataService;
}

// CommonJS 导出 (如果需要)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SharedDataService;
}

console.log('📦 SharedDataService 类已加载');