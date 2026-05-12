/**
 * 组件通信桥梁 - 统一消息协议
 * 处理sidepanel ↔ data-manager ↔ background之间的通信
 * 
 * @version 2.0
 * @author AI Assistant
 */

class ComponentBridge {
    constructor() {
        this.messageHandlers = new Map();
        this.componentId = this.detectComponentType();
        this.setupMessageListening();
        
        console.log(`📡 ComponentBridge 已初始化 - 组件类型: ${this.componentId}`);
    }
    
    /**
     * 检测当前组件类型
     */
    detectComponentType() {
        // 检测是否在sidepanel环境
        if (window.location.pathname.includes('sidepanel') || 
            document.title.includes('sidepanel') ||
            window.chrome?.sidePanel) {
            return 'sidepanel';
        }
        
        // 检测是否在data-manager环境
        if (window.location.pathname.includes('data-manager') ||
            document.title.includes('数据管理器')) {
            return 'data-manager';
        }
        
        // 检测是否在background环境
        if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.getBackgroundPage) {
            return 'background';
        }
        
        // 默认为unknown
        return 'unknown';
    }
    
    /**
     * 设置消息监听
     */
    setupMessageListening() {
        // 监听来自background的消息
        if (chrome?.runtime?.onMessage) {
            chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
                this.handleIncomingMessage(message, sender, sendResponse);
                return true; // 保持消息通道开放
            });
        }
        
        // 监听来自其他页面的消息
        window.addEventListener('message', (event) => {
            if (event.source !== window && event.data && event.data.type === 'COMPONENT_BRIDGE_MESSAGE') {
                this.handleIncomingMessage(event.data.payload, { origin: event.origin }, null);
            }
        });
    }
    
    /**
     * 处理传入消息
     */
    handleIncomingMessage(message, sender, sendResponse) {
        try {
            // 检查消息格式
            if (!this.isValidBridgeMessage(message)) {
                return;
            }
            
            // 检查目标组件
            if (message.target && message.target !== this.componentId && message.target !== 'all') {
                return;
            }
            
            console.log(`📥 收到消息 [${message.action}] from ${message.source || 'unknown'} to ${message.target || 'any'}`);
            
            // 执行消息处理器
            if (this.messageHandlers.has(message.action)) {
                const handler = this.messageHandlers.get(message.action);
                const result = handler(message.data, sender);
                
                // 发送响应
                if (sendResponse && result !== undefined) {
                    if (result instanceof Promise) {
                        result.then(res => sendResponse({ success: true, data: res }))
                              .catch(err => sendResponse({ success: false, error: err.message }));
                    } else {
                        sendResponse({ success: true, data: result });
                    }
                }
            }
            
        } catch (error) {
            console.error('消息处理失败:', error);
            if (sendResponse) {
                sendResponse({ success: false, error: error.message });
            }
        }
    }
    
    /**
     * 验证消息格式
     */
    isValidBridgeMessage(message) {
        return message && 
               typeof message === 'object' &&
               message.action &&
               message.timestamp;
    }
    
    /**
     * 发送消息到指定组件
     */
    sendMessage(target, action, data = null) {
        const message = {
            action: action,
            source: this.componentId,
            target: target,
            data: data,
            timestamp: Date.now()
        };
        
        console.log(`📤 发送消息 [${action}] from ${this.componentId} to ${target}`);
        
        // 发送到background
        if (chrome?.runtime?.sendMessage) {
            chrome.runtime.sendMessage(message).catch(error => {
                console.warn('发送到background失败:', error);
            });
        }
        
        // 如果目标是data-manager，尝试直接发送到页面
        if (target === 'data-manager') {
            this.sendToDataManagerPage(message);
        }
        
        // 如果目标是sidepanel，通过background转发
        if (target === 'sidepanel' && this.componentId !== 'sidepanel') {
            this.sendToSidepanelViaBackground(message);
        }
    }
    
    /**
     * 发送到data-manager页面
     */
    sendToDataManagerPage(message) {
        // 尝试通过tabs API发送
        if (chrome?.tabs?.query) {
            chrome.tabs.query({ url: '*://*/data-manager.html' }, (tabs) => {
                tabs.forEach(tab => {
                    chrome.tabs.sendMessage(tab.id, message).catch(error => {
                        console.warn('发送到data-manager页面失败:', error);
                    });
                });
            });
        }
    }
    
    /**
     * 通过background发送到sidepanel
     */
    sendToSidepanelViaBackground(message) {
        const backgroundMessage = {
            ...message,
            action: 'FORWARD_TO_SIDEPANEL',
            originalAction: message.action
        };
        
        if (chrome?.runtime?.sendMessage) {
            chrome.runtime.sendMessage(backgroundMessage).catch(error => {
                console.warn('转发到sidepanel失败:', error);
            });
        }
    }
    
    /**
     * 注册消息处理器
     */
    onMessage(action, handler) {
        this.messageHandlers.set(action, handler);
        console.log(`📋 已注册消息处理器: ${action}`);
    }
    
    /**
     * 移除消息处理器
     */
    offMessage(action) {
        this.messageHandlers.delete(action);
        console.log(`📋 已移除消息处理器: ${action}`);
    }
    
    /**
     * 广播消息到所有组件
     */
    broadcast(action, data = null) {
        this.sendMessage('all', action, data);
    }
    
    // ==================== 预定义的消息类型 ====================

    /**
     * sidepanel → data-manager 消息
     */
    static MESSAGES = {
        // 数据更新通知
        DATA_UPDATED: 'DATA_UPDATED',
        PRODUCTS_UPDATED: 'PRODUCTS_UPDATED',
        CATEGORIES_UPDATED: 'CATEGORIES_UPDATED',

        // 操作状态通知
        EXTRACTION_STARTED: 'EXTRACTION_STARTED',
        EXTRACTION_PROGRESS: 'EXTRACTION_PROGRESS',
        EXTRACTION_COMPLETED: 'EXTRACTION_COMPLETED',

        MONITORING_STARTED: 'MONITORING_STARTED',
        MONITORING_PROGRESS: 'MONITORING_PROGRESS',
        MONITORING_COMPLETED: 'MONITORING_COMPLETED',
        MONITORING_PAUSED: 'MONITORING_PAUSED',
        MONITORING_STOPPED: 'MONITORING_STOPPED',

        // 异常检测通知
        ANOMALY_DETECTED: 'ANOMALY_DETECTED',
        ANOMALY_STATS_UPDATED: 'ANOMALY_STATS_UPDATED',

        // 请求响应消息
        REQUEST_DATA_REFRESH: 'REQUEST_DATA_REFRESH',
        REQUEST_OPERATION: 'REQUEST_OPERATION',

        // UI状态同步
        UI_FILTER_CHANGED: 'UI_FILTER_CHANGED',
        UI_VIEW_CHANGED: 'UI_VIEW_CHANGED',

        // 🆕 新增：状态同步消息
        STATE_SYNC_REQUEST: 'STATE_SYNC_REQUEST',
        EXCEL_UPLOAD_COMPLETED: 'EXCEL_UPLOAD_COMPLETED',
        CATEGORY_CREATED: 'CATEGORY_CREATED',
        PRODUCT_DATA_UPDATED: 'PRODUCT_DATA_UPDATED',
        ANOMALY_DETECTION_UPDATED: 'ANOMALY_DETECTION_UPDATED',
        BATCH_MONITORING_COMPLETED: 'BATCH_MONITORING_COMPLETED'
    };
    
    // ==================== 便捷方法 ====================
    
    /**
     * 通知数据更新
     */
    notifyDataUpdate(type, data) {
        this.sendMessage('data-manager', ComponentBridge.MESSAGES.DATA_UPDATED, {
            type: type,
            data: data,
            timestamp: Date.now()
        });
    }
    
    /**
     * 通知提取状态
     */
    notifyExtractionStatus(status, data = {}) {
        const action = {
            'started': ComponentBridge.MESSAGES.EXTRACTION_STARTED,
            'progress': ComponentBridge.MESSAGES.EXTRACTION_PROGRESS,
            'completed': ComponentBridge.MESSAGES.EXTRACTION_COMPLETED
        }[status];
        
        if (action) {
            this.sendMessage('data-manager', action, data);
        }
    }
    
    /**
     * 通知监控状态
     */
    notifyMonitoringStatus(status, data = {}) {
        const action = {
            'started': ComponentBridge.MESSAGES.MONITORING_STARTED,
            'progress': ComponentBridge.MESSAGES.MONITORING_PROGRESS,
            'completed': ComponentBridge.MESSAGES.MONITORING_COMPLETED,
            'paused': ComponentBridge.MESSAGES.MONITORING_PAUSED,
            'stopped': ComponentBridge.MESSAGES.MONITORING_STOPPED
        }[status];
        
        if (action) {
            this.sendMessage('data-manager', action, data);
        }
    }
    
    /**
     * 通知异常检测结果
     */
    notifyAnomalyDetected(anomaly) {
        this.sendMessage('data-manager', ComponentBridge.MESSAGES.ANOMALY_DETECTED, anomaly);
    }
    
    /**
     * 请求数据刷新
     */
    requestDataRefresh(type = 'all') {
        this.sendMessage('all', ComponentBridge.MESSAGES.REQUEST_DATA_REFRESH, { type });
    }

    /**
     * 🆕 新增：通知状态同步
     * @param {string} operation 操作类型
     * @param {Object} data 相关数据
     */
    notifyStateSync(operation, data = {}) {
        console.log(`📡 发送状态同步通知 [${operation}] from ${this.componentId}`);

        this.sendMessage('data-manager', ComponentBridge.MESSAGES.STATE_SYNC_REQUEST, {
            operation,
            data,
            timestamp: Date.now(),
            source: this.componentId
        });
    }

    /**
     * 🆕 新增：便捷的状态同步方法
     */
    notifyExcelUploadCompleted(categoryId, result) {
        this.notifyStateSync('excel_upload_completed', {
            categoryId,
            successCount: result.success,
            createdCount: result.created,
            updatedCount: result.updated,
            failedCount: result.failed
        });
    }

    notifyCategoryCreated(categoryId, categoryName) {
        this.notifyStateSync('category_created', {
            categoryId,
            categoryName
        });
    }

    notifyProductDataUpdated(categoryIds, operation) {
        this.notifyStateSync('product_data_updated', {
            categoryIds,
            operation,
            affectedCategories: categoryIds.length
        });
    }

    notifyAnomalyDetectionUpdated(results) {
        this.notifyStateSync('anomaly_detection_updated', {
            anomaliesCount: results.length,
            detectionTime: Date.now()
        });
    }

    notifyBatchMonitoringCompleted(result) {
        this.notifyStateSync('batch_monitoring_completed', {
            successCount: result.successCount,
            errorCount: result.errorCount,
            affectedCategories: result.categoryCount || 0
        });
    }

    /**
     * 获取组件状态
     */
    getComponentStatus() {
        return {
            componentId: this.componentId,
            handlersCount: this.messageHandlers.size,
            handlers: Array.from(this.messageHandlers.keys())
        };
    }
}

// 创建全局实例
let bridgeInstance = null;

/**
 * 获取ComponentBridge实例
 */
function getComponentBridge() {
    if (!bridgeInstance) {
        bridgeInstance = new ComponentBridge();
    }
    return bridgeInstance;
}

// 全局导出
if (typeof window !== 'undefined') {
    window.ComponentBridge = ComponentBridge;
    window.getComponentBridge = getComponentBridge;
}

// CommonJS 导出 (如果需要)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ComponentBridge, getComponentBridge };
}

console.log('📡 ComponentBridge 类已加载');