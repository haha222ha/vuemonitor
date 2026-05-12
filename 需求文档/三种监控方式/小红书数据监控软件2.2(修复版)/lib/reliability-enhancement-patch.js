/**
 * 可靠性增强补丁 - 修复后台运行中断问题
 * ultrathink 深度故障分析和解决方案
 */

class ReliabilityEnhancer {
    constructor() {
        this.activeListeners = new Map(); // 跟踪所有活跃监听器
        this.activeTimeouts = new Set(); // 跟踪所有超时器
        this.activeIntervals = new Set(); // 跟踪所有定时器
        this.emergencyCleanupTriggered = false;

        // 全局错误监控
        this.setupGlobalErrorHandling();

        // 定期健康检查
        this.startHealthMonitoring();
    }

    /**
     * 设置全局错误处理
     */
    setupGlobalErrorHandling() {
        // 捕获未处理的Promise拒绝
        window.addEventListener('unhandledrejection', (event) => {
            console.error('🚨 未处理的Promise拒绝:', event.reason);
            this.handleCriticalError('unhandled_promise_rejection', event.reason);
            event.preventDefault(); // 防止错误冒泡导致程序崩溃
        });

        // 捕获全局JavaScript错误
        window.addEventListener('error', (event) => {
            console.error('🚨 全局JavaScript错误:', event.error);
            this.handleCriticalError('javascript_error', event.error);
        });

        // Chrome扩展特定错误监控
        if (chrome && chrome.runtime) {
            chrome.runtime.onSuspend?.addListener(() => {
                console.warn('⚠️ Chrome扩展即将挂起，执行紧急清理');
                this.performEmergencyCleanup();
            });
        }
    }

    /**
     * 安全的事件监听器管理
     */
    safeAddListener(target, event, listener, options = {}) {
        const listenerId = `${target.constructor.name}_${event}_${Date.now()}`;

        // 包装监听器以添加错误处理
        const wrappedListener = (...args) => {
            try {
                return listener(...args);
            } catch (error) {
                console.error(`🚨 监听器执行错误 (${listenerId}):`, error);
                this.handleCriticalError('listener_error', error);
            }
        };

        // 记录监听器
        this.activeListeners.set(listenerId, {
            target,
            event,
            listener: wrappedListener,
            originalListener: listener,
            addedAt: Date.now()
        });

        // 添加监听器
        target.addListener ?
            target.addListener(wrappedListener) :
            target.addEventListener(event, wrappedListener, options);

        console.log(`✅ 安全添加监听器: ${listenerId}`);
        return listenerId;
    }

    /**
     * 安全移除监听器
     */
    safeRemoveListener(listenerId) {
        const listenerInfo = this.activeListeners.get(listenerId);
        if (listenerInfo) {
            try {
                const { target, event, listener } = listenerInfo;
                target.removeListener ?
                    target.removeListener(listener) :
                    target.removeEventListener(event, listener);

                this.activeListeners.delete(listenerId);
                console.log(`✅ 安全移除监听器: ${listenerId}`);
            } catch (error) {
                console.warn(`⚠️ 移除监听器失败 (${listenerId}):`, error);
            }
        }
    }

    /**
     * 安全的超时管理
     */
    safeSetTimeout(callback, delay) {
        const timeoutId = setTimeout(() => {
            this.activeTimeouts.delete(timeoutId);
            try {
                callback();
            } catch (error) {
                console.error('🚨 超时回调执行错误:', error);
                this.handleCriticalError('timeout_callback_error', error);
            }
        }, delay);

        this.activeTimeouts.add(timeoutId);
        return timeoutId;
    }

    /**
     * 安全的定时器管理
     */
    safeSetInterval(callback, interval) {
        const intervalId = setInterval(() => {
            try {
                callback();
            } catch (error) {
                console.error('🚨 定时器回调执行错误:', error);
                this.handleCriticalError('interval_callback_error', error);
                // 出错时清理定时器
                this.safeClearInterval(intervalId);
            }
        }, interval);

        this.activeIntervals.add(intervalId);
        return intervalId;
    }

    /**
     * 安全清理超时
     */
    safeClearTimeout(timeoutId) {
        if (timeoutId) {
            clearTimeout(timeoutId);
            this.activeTimeouts.delete(timeoutId);
        }
    }

    /**
     * 安全清理定时器
     */
    safeClearInterval(intervalId) {
        if (intervalId) {
            clearInterval(intervalId);
            this.activeIntervals.delete(intervalId);
        }
    }

    /**
     * 增强的Promise处理
     */
    async safePromiseRace(promises, timeoutMs = 30000) {
        return new Promise((resolve, reject) => {
            let settled = false;

            // 超时保护
            const timeoutId = this.safeSetTimeout(() => {
                if (!settled) {
                    settled = true;
                    reject(new Error(`Promise竞争超时: ${timeoutMs}ms`));
                }
            }, timeoutMs);

            // 处理Promise数组
            Promise.race(promises)
                .then(result => {
                    if (!settled) {
                        settled = true;
                        this.safeClearTimeout(timeoutId);
                        resolve(result);
                    }
                })
                .catch(error => {
                    if (!settled) {
                        settled = true;
                        this.safeClearTimeout(timeoutId);
                        reject(error);
                    }
                });
        });
    }

    /**
     * 健康监控
     */
    startHealthMonitoring() {
        const healthCheckInterval = this.safeSetInterval(() => {
            this.performHealthCheck();
        }, 60000); // 每分钟检查一次

        console.log('🔄 启动健康监控');
    }

    /**
     * 执行健康检查
     */
    performHealthCheck() {
        const stats = {
            activeListeners: this.activeListeners.size,
            activeTimeouts: this.activeTimeouts.size,
            activeIntervals: this.activeIntervals.size,
            memoryUsage: performance.memory ?
                Math.round(performance.memory.usedJSHeapSize / 1024 / 1024) : 'unknown'
        };

        console.log('📊 系统健康状态:', stats);

        // 检查资源泄漏
        if (stats.activeListeners > 50) {
            console.warn('⚠️ 检测到监听器可能泄漏:', stats.activeListeners);
            this.cleanupOldListeners();
        }

        if (stats.activeTimeouts > 100 || stats.activeIntervals > 20) {
            console.warn('⚠️ 检测到定时器可能泄漏:', {
                timeouts: stats.activeTimeouts,
                intervals: stats.activeIntervals
            });
        }

        // 内存使用检查
        if (stats.memoryUsage !== 'unknown' && stats.memoryUsage > 500) {
            console.warn('⚠️ 内存使用过高:', stats.memoryUsage, 'MB');
            this.handleCriticalError('high_memory_usage', { memoryUsage: stats.memoryUsage });
        }
    }

    /**
     * 清理旧监听器
     */
    cleanupOldListeners() {
        const now = Date.now();
        const maxAge = 10 * 60 * 1000; // 10分钟

        for (const [listenerId, listenerInfo] of this.activeListeners) {
            if (now - listenerInfo.addedAt > maxAge) {
                console.log(`🧹 清理过期监听器: ${listenerId}`);
                this.safeRemoveListener(listenerId);
            }
        }
    }

    /**
     * 处理关键错误
     */
    handleCriticalError(errorType, error) {
        console.error(`🚨 关键错误 [${errorType}]:`, error);

        // 错误统计
        this.errorStats = this.errorStats || {};
        this.errorStats[errorType] = (this.errorStats[errorType] || 0) + 1;

        // 如果错误频率过高，触发紧急清理
        if (this.errorStats[errorType] > 5 && !this.emergencyCleanupTriggered) {
            console.warn('⚠️ 错误频率过高，触发紧急清理');
            this.performEmergencyCleanup();
        }
    }

    /**
     * 紧急清理
     */
    performEmergencyCleanup() {
        if (this.emergencyCleanupTriggered) return;
        this.emergencyCleanupTriggered = true;

        console.warn('🚨 执行紧急清理...');

        // 清理所有监听器
        for (const [listenerId] of this.activeListeners) {
            this.safeRemoveListener(listenerId);
        }

        // 清理所有定时器
        for (const timeoutId of this.activeTimeouts) {
            clearTimeout(timeoutId);
        }
        this.activeTimeouts.clear();

        for (const intervalId of this.activeIntervals) {
            clearInterval(intervalId);
        }
        this.activeIntervals.clear();

        // 通知其他组件
        if (window.dataManagerApp && typeof window.dataManagerApp.handleEmergencyCleanup === 'function') {
            window.dataManagerApp.handleEmergencyCleanup();
        }

        if (window.batchMonitorService && typeof window.batchMonitorService.emergencyStop === 'function') {
            window.batchMonitorService.emergencyStop();
        }

        console.log('✅ 紧急清理完成');

        // 5分钟后重置紧急状态
        setTimeout(() => {
            this.emergencyCleanupTriggered = false;
            console.log('🔄 紧急状态重置');
        }, 5 * 60 * 1000);
    }

    /**
     * 获取系统状态
     */
    getSystemStatus() {
        return {
            healthy: !this.emergencyCleanupTriggered,
            activeListeners: this.activeListeners.size,
            activeTimeouts: this.activeTimeouts.size,
            activeIntervals: this.activeIntervals.size,
            errorStats: this.errorStats || {},
            lastHealthCheck: this.lastHealthCheck || 'never'
        };
    }
}

// 创建全局可靠性增强器
window.reliabilityEnhancer = new ReliabilityEnhancer();

console.log('🛡️ 可靠性增强补丁已加载');
console.log('💡 功能:');
console.log('  • 全局错误捕获和处理');
console.log('  • 安全的事件监听器管理');
console.log('  • Promise超时保护');
console.log('  • 资源泄漏检测和清理');
console.log('  • 紧急故障恢复机制');
console.log('');
console.log('📊 使用 reliabilityEnhancer.getSystemStatus() 查看系统状态');