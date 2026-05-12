/**
 * 中断防护系统 - 彻底解决后台运行中断问题
 * ultrathink 深度分析解决方案
 */

class InterruptPreventionSystem {
    constructor() {
        this.activeOperations = new Map(); // 跟踪所有活跃操作
        this.healthCheckInterval = null;
        this.lastHeartbeat = Date.now();
        this.interruptionCount = 0;
        this.recoveryInProgress = false;

        // Chrome扩展生命周期监控
        this.setupExtensionLifecycleMonitoring();

        // 启动心跳检测
        this.startHeartbeatMonitoring();
    }

    /**
     * 安全的标签页消息发送 - 带超时和重试
     */
    async safeTabMessage(tabId, message, options = {}) {
        const {
            timeout = 10000,     // 10秒超时
            retries = 2,         // 重试2次
            validateTab = true   // 验证标签页状态
        } = options;

        const operationId = `tab_message_${tabId}_${Date.now()}`;
        this.activeOperations.set(operationId, {
            type: 'tab_message',
            tabId,
            message,
            startTime: Date.now()
        });

        try {
            // 预检查：验证标签页状态
            if (validateTab) {
                await this.validateTabState(tabId);
            }

            // 执行消息发送，带超时保护
            for (let attempt = 0; attempt <= retries; attempt++) {
                try {
                    const response = await this.sendMessageWithTimeout(tabId, message, timeout);

                    // 成功，清理操作记录
                    this.activeOperations.delete(operationId);
                    return response;

                } catch (error) {
                    console.warn(`⚠️ 标签页 ${tabId} 消息发送失败 (尝试 ${attempt + 1}/${retries + 1}):`, error.message);

                    if (attempt < retries) {
                        // 重试前等待和验证
                        await this.sleep(1000 * (attempt + 1));
                        if (validateTab) {
                            await this.validateTabState(tabId);
                        }
                    }
                }
            }

            throw new Error(`标签页 ${tabId} 消息发送彻底失败，已重试 ${retries} 次`);

        } finally {
            this.activeOperations.delete(operationId);
        }
    }

    /**
     * 带超时的消息发送
     */
    async sendMessageWithTimeout(tabId, message, timeout) {
        return new Promise((resolve, reject) => {
            let completed = false;

            // 超时保护
            const timeoutHandle = setTimeout(() => {
                if (!completed) {
                    completed = true;
                    reject(new Error(`标签页 ${tabId} 消息超时 (${timeout}ms)`));
                }
            }, timeout);

            // 发送消息
            chrome.tabs.sendMessage(tabId, message, (response) => {
                if (!completed) {
                    completed = true;
                    clearTimeout(timeoutHandle);

                    if (chrome.runtime.lastError) {
                        reject(new Error(`Chrome Runtime错误: ${chrome.runtime.lastError.message}`));
                    } else if (response && response.success) {
                        resolve(response);
                    } else {
                        reject(new Error(response?.error || '标签页响应失败'));
                    }
                }
            });
        });
    }

    /**
     * 验证标签页状态
     */
    async validateTabState(tabId) {
        try {
            const tab = await chrome.tabs.get(tabId);

            if (!tab) {
                throw new Error(`标签页 ${tabId} 不存在`);
            }

            if (tab.status === 'unloaded') {
                throw new Error(`标签页 ${tabId} 已卸载`);
            }

            // 检查是否是有效的小红书页面
            if (!tab.url || (!tab.url.includes('xiaohongshu.com') && !tab.url.includes('about:blank'))) {
                console.warn(`⚠️ 标签页 ${tabId} URL异常: ${tab.url}`);
            }

            return tab;

        } catch (error) {
            if (chrome.runtime.lastError) {
                throw new Error(`标签页状态检查失败: ${chrome.runtime.lastError.message}`);
            } else {
                throw error;
            }
        }
    }

    /**
     * 检测和处理Chrome扩展被暂停
     */
    setupExtensionLifecycleMonitoring() {
        // 监控扩展暂停事件
        if (chrome.runtime && chrome.runtime.onSuspend) {
            chrome.runtime.onSuspend.addListener(() => {
                console.warn('🚨 Chrome扩展即将暂停，执行紧急保存');
                this.handleExtensionSuspend();
            });
        }

        // 监控标签页关闭事件
        if (chrome.tabs && chrome.tabs.onRemoved) {
            chrome.tabs.onRemoved.addListener((tabId, removeInfo) => {
                console.log(`📝 标签页 ${tabId} 已关闭`);
                this.handleTabClosed(tabId);
            });
        }

        // 监控标签页更新事件
        if (chrome.tabs && chrome.tabs.onUpdated) {
            chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
                if (changeInfo.status === 'complete') {
                    this.handleTabLoaded(tabId, tab);
                }
            });
        }
    }

    /**
     * 处理扩展暂停
     */
    async handleExtensionSuspend() {
        console.warn('⚠️ 处理扩展暂停事件');

        // 保存当前状态
        const currentState = {
            activeOperations: Array.from(this.activeOperations.entries()),
            timestamp: Date.now(),
            interruptionCount: this.interruptionCount + 1
        };

        // 尝试保存到本地存储
        try {
            await chrome.storage.local.set({
                'interrupt_recovery_data': currentState
            });
            console.log('✅ 中断恢复数据已保存');
        } catch (error) {
            console.error('❌ 保存中断恢复数据失败:', error);
        }

        // 通知主应用
        if (window.dataManagerApp && typeof window.dataManagerApp.handleExtensionSuspend === 'function') {
            window.dataManagerApp.handleExtensionSuspend();
        }
    }

    /**
     * 处理标签页关闭
     */
    handleTabClosed(tabId) {
        // 清理相关操作
        for (const [operationId, operation] of this.activeOperations) {
            if (operation.tabId === tabId) {
                console.log(`🧹 清理标签页 ${tabId} 的操作: ${operationId}`);
                this.activeOperations.delete(operationId);
            }
        }

        // 通知标签页池管理器
        if (window.tabPoolManager && typeof window.tabPoolManager.handleTabClosed === 'function') {
            window.tabPoolManager.handleTabClosed(tabId);
        }
    }

    /**
     * 处理标签页加载完成
     */
    handleTabLoaded(tabId, tab) {
        // 更新操作状态
        for (const [operationId, operation] of this.activeOperations) {
            if (operation.tabId === tabId && operation.type === 'tab_loading') {
                operation.loadedAt = Date.now();
                operation.finalUrl = tab.url;
                console.log(`✅ 标签页 ${tabId} 加载完成: ${tab.url}`);
            }
        }
    }

    /**
     * 启动心跳监控
     */
    startHeartbeatMonitoring() {
        this.healthCheckInterval = setInterval(() => {
            this.performHeartbeatCheck();
        }, 30000); // 每30秒检查一次

        console.log('💓 启动心跳监控');
    }

    /**
     * 执行心跳检查
     */
    async performHeartbeatCheck() {
        const now = Date.now();
        this.lastHeartbeat = now;

        // 检查长时间运行的操作
        const longRunningOperations = [];
        for (const [operationId, operation] of this.activeOperations) {
            const runtime = now - operation.startTime;
            if (runtime > 60000) { // 超过1分钟
                longRunningOperations.push({ operationId, operation, runtime });
            }
        }

        if (longRunningOperations.length > 0) {
            console.warn('⚠️ 检测到长时间运行的操作:', longRunningOperations.length);

            for (const { operationId, operation, runtime } of longRunningOperations) {
                console.warn(`  - ${operationId}: ${runtime}ms (${operation.type})`);

                // 超过5分钟的操作强制清理
                if (runtime > 300000) {
                    console.error(`🚨 强制清理超时操作: ${operationId}`);
                    this.activeOperations.delete(operationId);
                }
            }
        }

        // 尝试恢复中断
        await this.attemptInterruptionRecovery();

        console.log(`💓 心跳检查完成 - 活跃操作: ${this.activeOperations.size}`);
    }

    /**
     * 尝试从中断中恢复
     */
    async attemptInterruptionRecovery() {
        if (this.recoveryInProgress) return;

        try {
            const recoveryData = await chrome.storage.local.get('interrupt_recovery_data');

            if (recoveryData.interrupt_recovery_data) {
                const data = recoveryData.interrupt_recovery_data;
                const timeSinceInterrupt = Date.now() - data.timestamp;

                // 如果中断时间在5分钟内，尝试恢复
                if (timeSinceInterrupt < 300000 && data.activeOperations.length > 0) {
                    console.log('🔄 检测到中断恢复数据，尝试恢复操作');
                    this.recoveryInProgress = true;

                    await this.performRecoveryProcess(data);

                    // 清理恢复数据
                    await chrome.storage.local.remove('interrupt_recovery_data');
                    this.recoveryInProgress = false;
                }
            }
        } catch (error) {
            console.error('❌ 中断恢复过程失败:', error);
            this.recoveryInProgress = false;
        }
    }

    /**
     * 执行恢复过程
     */
    async performRecoveryProcess(recoveryData) {
        console.log('🚀 开始执行中断恢复...');

        // 通知主应用恢复开始
        if (window.dataManagerApp && typeof window.dataManagerApp.handleRecoveryStart === 'function') {
            window.dataManagerApp.handleRecoveryStart(recoveryData);
        }

        // 恢复操作统计
        this.interruptionCount = recoveryData.interruptionCount || 0;

        console.log(`✅ 中断恢复完成 - 历史中断次数: ${this.interruptionCount}`);
    }

    /**
     * 安全的标签页导航
     */
    async safeNavigateTab(tabId, url, options = {}) {
        const { timeout = 15000, waitForLoad = true } = options;

        const operationId = `navigate_${tabId}_${Date.now()}`;
        this.activeOperations.set(operationId, {
            type: 'tab_navigation',
            tabId,
            url,
            startTime: Date.now()
        });

        try {
            // 导航标签页
            await chrome.tabs.update(tabId, { url });

            if (waitForLoad) {
                // 等待加载完成
                await this.waitForTabNavigation(tabId, url, timeout);
            }

            this.activeOperations.delete(operationId);
            return true;

        } catch (error) {
            this.activeOperations.delete(operationId);
            throw error;
        }
    }

    /**
     * 等待标签页导航完成
     */
    async waitForTabNavigation(tabId, expectedUrl, timeout) {
        return new Promise((resolve, reject) => {
            let completed = false;

            const timeoutHandle = setTimeout(() => {
                if (!completed) {
                    completed = true;
                    chrome.tabs.onUpdated.removeListener(listener);
                    reject(new Error(`标签页 ${tabId} 导航超时`));
                }
            }, timeout);

            const listener = (updatedTabId, changeInfo, tab) => {
                if (updatedTabId === tabId && changeInfo.status === 'complete') {
                    if (!completed) {
                        completed = true;
                        clearTimeout(timeoutHandle);
                        chrome.tabs.onUpdated.removeListener(listener);
                        resolve(tab);
                    }
                }
            };

            chrome.tabs.onUpdated.addListener(listener);
        });
    }

    /**
     * 工具方法：睡眠
     */
    async sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * 获取系统状态
     */
    getSystemStatus() {
        return {
            activeOperations: this.activeOperations.size,
            lastHeartbeat: this.lastHeartbeat,
            interruptionCount: this.interruptionCount,
            recoveryInProgress: this.recoveryInProgress,
            uptime: Date.now() - (this.startTime || Date.now())
        };
    }

    /**
     * 手动触发健康检查
     */
    async forceHealthCheck() {
        await this.performHeartbeatCheck();
    }

    /**
     * 清理所有资源
     */
    cleanup() {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
            this.healthCheckInterval = null;
        }

        this.activeOperations.clear();
        console.log('🧹 中断防护系统已清理');
    }
}

// 创建全局中断防护系统
window.interruptPreventionSystem = new InterruptPreventionSystem();

// 导出增强的Chrome API包装器
window.safeTabMessage = (tabId, message, options) =>
    window.interruptPreventionSystem.safeTabMessage(tabId, message, options);

window.safeNavigateTab = (tabId, url, options) =>
    window.interruptPreventionSystem.safeNavigateTab(tabId, url, options);

console.log('🛡️ 中断防护系统已加载');
console.log('💡 新功能:');
console.log('  • safeTabMessage() - 安全的标签页消息发送');
console.log('  • safeNavigateTab() - 安全的标签页导航');
console.log('  • 自动中断检测和恢复');
console.log('  • Chrome扩展生命周期监控');
console.log('  • 心跳监控和长操作检测');
console.log('');
console.log('📊 使用 interruptPreventionSystem.getSystemStatus() 查看状态');