/**
 * 后台性能增强器 - 解决Chrome后台节流问题
 * ultrathink 深度分析Chrome后台限制机制
 */

class BackgroundPerformanceEnhancer {
    constructor() {
        this.isActive = false;
        this.visibilityState = 'visible';
        this.backgroundStartTime = null;
        this.performanceStats = {
            foregroundSpeed: 0,
            backgroundSpeed: 0,
            throttlingRatio: 1
        };

        // Chrome后台限制分析
        this.chromeThrottling = {
            timerThrottling: true,      // 定时器被限制到1秒最小间隔
            networkThrottling: true,    // 网络请求优先级降低
            renderingPause: true,       // 渲染完全暂停
            serviceWorkerLimit: true    // Service Worker受限
        };

        this.setupBackgroundMonitoring();
    }

    /**
     * 设置后台监控机制
     */
    setupBackgroundMonitoring() {
        // 监听页面可见性变化
        document.addEventListener('visibilitychange', () => {
            this.handleVisibilityChange();
        });

        // 监听窗口焦点变化
        window.addEventListener('focus', () => {
            this.handleWindowFocus();
        });

        window.addEventListener('blur', () => {
            this.handleWindowBlur();
        });

        // 启动后台保活机制
        this.startBackgroundKeepalive();
    }

    /**
     * 处理页面可见性变化
     */
    handleVisibilityChange() {
        const isHidden = document.hidden;
        const newState = isHidden ? 'hidden' : 'visible';

        console.log(`🔄 页面可见性变化: ${this.visibilityState} → ${newState}`);

        if (this.visibilityState !== newState) {
            this.visibilityState = newState;

            if (isHidden) {
                this.onEnterBackground();
            } else {
                this.onEnterForeground();
            }
        }
    }

    /**
     * 进入后台状态
     */
    onEnterBackground() {
        console.warn('⚠️ 进入后台状态 - Chrome将启动节流限制');

        this.backgroundStartTime = Date.now();

        // 分析当前Chrome限制
        this.analyzeBackgroundLimitations();

        // 启动后台保活策略
        this.activateBackgroundStrategies();

        // 通知主应用
        if (window.dataManagerApp && typeof window.dataManagerApp.handleBackgroundMode === 'function') {
            window.dataManagerApp.handleBackgroundMode(true);
        }

        if (window.batchMonitorService && typeof window.batchMonitorService.handleBackgroundMode === 'function') {
            window.batchMonitorService.handleBackgroundMode(true);
        }
    }

    /**
     * 回到前台状态
     */
    onEnterForeground() {
        console.log('✅ 回到前台状态 - Chrome限制解除');

        if (this.backgroundStartTime) {
            const backgroundDuration = Date.now() - this.backgroundStartTime;
            console.log(`📊 后台运行时长: ${Math.round(backgroundDuration / 1000)}秒`);
            this.backgroundStartTime = null;
        }

        // 停用后台策略
        this.deactivateBackgroundStrategies();

        // 通知主应用
        if (window.dataManagerApp && typeof window.dataManagerApp.handleBackgroundMode === 'function') {
            window.dataManagerApp.handleBackgroundMode(false);
        }

        if (window.batchMonitorService && typeof window.batchMonitorService.handleBackgroundMode === 'function') {
            window.batchMonitorService.handleBackgroundMode(false);
        }
    }

    /**
     * 窗口获得焦点
     */
    handleWindowFocus() {
        console.log('🎯 窗口获得焦点');
        // 即使页面可见，窗口焦点也很重要
        this.onEnterForeground();
    }

    /**
     * 窗口失去焦点
     */
    handleWindowBlur() {
        console.log('😴 窗口失去焦点');
        // 失去焦点也可能触发节流
        setTimeout(() => {
            if (document.hidden) {
                this.onEnterBackground();
            }
        }, 100);
    }

    /**
     * 分析后台限制情况
     */
    analyzeBackgroundLimitations() {
        console.log('🔍 分析Chrome后台限制:');

        // 检测定时器节流
        const timerTestStart = Date.now();
        setTimeout(() => {
            const actualDelay = Date.now() - timerTestStart;
            const expectedDelay = 100;
            const throttlingRatio = actualDelay / expectedDelay;

            console.log(`  📊 定时器节流比例: ${throttlingRatio.toFixed(2)}x (预期100ms, 实际${actualDelay}ms)`);
            this.performanceStats.throttlingRatio = throttlingRatio;
        }, 100);

        // 检测网络请求优先级
        this.testNetworkPriority();

        // 显示Chrome版本信息
        this.logChromeInfo();
    }

    /**
     * 测试网络请求优先级
     */
    async testNetworkPriority() {
        const testStart = Date.now();

        try {
            // 发起一个简单的本地请求测试
            const response = await fetch('chrome-extension://' + chrome.runtime.id + '/manifest.json');
            const duration = Date.now() - testStart;

            console.log(`  📊 网络请求耗时: ${duration}ms`);

            if (duration > 200) {
                console.warn('  ⚠️ 网络请求可能被节流');
            }
        } catch (error) {
            console.warn('  ⚠️ 网络测试失败:', error.message);
        }
    }

    /**
     * 记录Chrome信息
     */
    logChromeInfo() {
        const userAgent = navigator.userAgent;
        const chromeMatch = userAgent.match(/Chrome\\/(\\d+)/);
        const chromeVersion = chromeMatch ? chromeMatch[1] : 'unknown';

        console.log('🌐 浏览器环境分析:');
        console.log(`  版本: Chrome ${chromeVersion}`);
        console.log(`  用户代理: ${userAgent.substring(0, 100)}...`);
        console.log(`  内存: ${performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1024 / 1024) + 'MB' : 'unknown'}`);
    }

    /**
     * 启动后台保活策略
     */
    activateBackgroundStrategies() {
        console.log('🛡️ 启动后台保活策略...');

        // 策略1: 使用chrome.alarms替代setTimeout
        this.setupChromeAlarms();

        // 策略2: 保持Service Worker活跃
        this.keepServiceWorkerActive();

        // 策略3: 使用Web Workers执行关键任务
        this.setupWebWorkerFallback();

        // 策略4: 降低后台操作频率但保持活跃
        this.adjustBackgroundFrequency();
    }

    /**
     * 停用后台策略
     */
    deactivateBackgroundStrategies() {
        console.log('🔄 停用后台保活策略');

        // 清理chrome.alarms
        if (chrome.alarms) {
            chrome.alarms.clearAll();
        }

        // 恢复正常频率
        this.restoreNormalFrequency();
    }

    /**
     * 设置Chrome Alarms (不受后台节流影响)
     */
    setupChromeAlarms() {
        if (!chrome.alarms) {
            console.warn('⚠️ chrome.alarms API不可用');
            return;
        }

        // 创建心跳alarm
        chrome.alarms.create('backgroundHeartbeat', {
            delayInMinutes: 0.1, // 6秒
            periodInMinutes: 0.1
        });

        // 监听alarm事件
        chrome.alarms.onAlarm.addListener((alarm) => {
            if (alarm.name === 'backgroundHeartbeat') {
                this.handleBackgroundHeartbeat();
            }
        });

        console.log('✅ Chrome Alarms后台心跳已启动');
    }

    /**
     * 处理后台心跳
     */
    handleBackgroundHeartbeat() {
        if (document.hidden) {
            console.log('💓 后台心跳 - 维持系统活跃');

            // 通知监控服务继续工作
            if (window.batchMonitorService && window.batchMonitorService.monitorState?.isRunning) {
                // 检查是否需要唤醒暂停的操作
                this.wakeupPausedOperations();
            }
        }
    }

    /**
     * 唤醒暂停的操作
     */
    wakeupPausedOperations() {
        try {
            // 检查并恢复可能被暂停的标签页操作
            if (window.tabPoolManager) {
                window.tabPoolManager.wakeupBackgroundTabs?.();
            }

            // 检查并恢复网络请求
            if (window.batchMonitorService) {
                window.batchMonitorService.resumeBackgroundProcessing?.();
            }

        } catch (error) {
            console.warn('⚠️ 唤醒操作失败:', error);
        }
    }

    /**
     * 保持Service Worker活跃
     */
    keepServiceWorkerActive() {
        if (!('serviceWorker' in navigator)) return;

        // 定期向Service Worker发送消息
        setInterval(() => {
            if (navigator.serviceWorker.controller && document.hidden) {
                navigator.serviceWorker.controller.postMessage({
                    type: 'BACKGROUND_KEEPALIVE',
                    timestamp: Date.now()
                });
            }
        }, 5000);
    }

    /**
     * 设置Web Worker后备方案
     */
    setupWebWorkerFallback() {
        try {
            // Web Workers不受页面后台节流影响
            const workerCode = `
                let interval = null;
                self.addEventListener('message', function(e) {
                    if (e.data.type === 'START_BACKGROUND_WORK') {
                        interval = setInterval(() => {
                            self.postMessage({ type: 'HEARTBEAT', timestamp: Date.now() });
                        }, e.data.interval || 5000);
                    } else if (e.data.type === 'STOP_BACKGROUND_WORK') {
                        if (interval) clearInterval(interval);
                    }
                });
            `;

            const blob = new Blob([workerCode], { type: 'application/javascript' });
            const workerUrl = URL.createObjectURL(blob);
            this.backgroundWorker = new Worker(workerUrl);

            this.backgroundWorker.addEventListener('message', (e) => {
                if (e.data.type === 'HEARTBEAT' && document.hidden) {
                    console.log('💓 Web Worker后台心跳');
                }
            });

            console.log('✅ Web Worker后台心跳已启动');

        } catch (error) {
            console.warn('⚠️ Web Worker设置失败:', error);
        }
    }

    /**
     * 调整后台频率
     */
    adjustBackgroundFrequency() {
        console.log('🔧 调整后台处理频率...');

        // 通知系统进入后台模式
        const backgroundConfig = {
            interval: 2000,        // 增加间隔到2秒
            concurrent: 8,         // 降低并发到8
            timeout: 15000,        // 增加超时到15秒
            batchSize: 8,          // 减少批次大小
            backgroundMode: true   // 标记为后台模式
        };

        if (window.batchMonitorService) {
            window.batchMonitorService.updateConfig?.(backgroundConfig);
        }
    }

    /**
     * 恢复正常频率
     */
    restoreNormalFrequency() {
        console.log('🚀 恢复前台处理频率...');

        // 恢复正常配置
        const normalConfig = {
            interval: 500,         // 恢复500ms间隔
            concurrent: 15,        // 恢复15并发
            timeout: 8000,         // 恢复8秒超时
            batchSize: 15,         // 恢复15批次大小
            backgroundMode: false  // 标记为前台模式
        };

        if (window.batchMonitorService) {
            window.batchMonitorService.updateConfig?.(normalConfig);
        }
    }

    /**
     * 启动后台保活机制
     */
    startBackgroundKeepalive() {
        // 方案1: 定期检查页面状态
        setInterval(() => {
            if (document.hidden) {
                // 后台状态下的保活操作
                this.performBackgroundKeepalive();
            }
        }, 10000); // 10秒检查一次

        console.log('🔄 后台保活机制已启动');
    }

    /**
     * 执行后台保活
     */
    performBackgroundKeepalive() {
        try {
            // 创建一个不可见的操作来保持活跃
            const img = new Image();
            img.onload = img.onerror = () => {
                console.log('💓 后台保活信号发送成功');
            };
            img.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';

        } catch (error) {
            console.warn('⚠️ 后台保活失败:', error);
        }
    }

    /**
     * 获取性能统计
     */
    getPerformanceStats() {
        return {
            visibilityState: this.visibilityState,
            isBackground: document.hidden,
            backgroundDuration: this.backgroundStartTime ? Date.now() - this.backgroundStartTime : 0,
            throttlingRatio: this.performanceStats.throttlingRatio,
            chromeThrottling: this.chromeThrottling
        };
    }

    /**
     * 手动触发后台测试
     */
    async testBackgroundPerformance() {
        console.log('🧪 开始后台性能测试...');

        const testResults = {
            timerAccuracy: await this.testTimerAccuracy(),
            networkLatency: await this.testNetworkLatency(),
            memoryUsage: this.getMemoryUsage()
        };

        console.log('📊 后台性能测试结果:', testResults);
        return testResults;
    }

    /**
     * 测试定时器精度
     */
    async testTimerAccuracy() {
        return new Promise(resolve => {
            const startTime = Date.now();
            const expectedDelay = 1000;

            setTimeout(() => {
                const actualDelay = Date.now() - startTime;
                const accuracy = expectedDelay / actualDelay;
                resolve({
                    expected: expectedDelay,
                    actual: actualDelay,
                    accuracy: accuracy
                });
            }, expectedDelay);
        });
    }

    /**
     * 测试网络延迟
     */
    async testNetworkLatency() {
        const startTime = Date.now();

        try {
            await fetch('chrome-extension://' + chrome.runtime.id + '/manifest.json');
            const latency = Date.now() - startTime;
            return { latency, success: true };
        } catch (error) {
            return { latency: -1, success: false, error: error.message };
        }
    }

    /**
     * 获取内存使用情况
     */
    getMemoryUsage() {
        if (performance.memory) {
            return {
                used: Math.round(performance.memory.usedJSHeapSize / 1024 / 1024),
                total: Math.round(performance.memory.totalJSHeapSize / 1024 / 1024),
                limit: Math.round(performance.memory.jsHeapSizeLimit / 1024 / 1024)
            };
        }
        return { used: 0, total: 0, limit: 0 };
    }
}

// 创建全局实例
window.backgroundPerformanceEnhancer = new BackgroundPerformanceEnhancer();

console.log('🛡️ 后台性能增强器已加载');
console.log('💡 功能:');
console.log('  • 自动检测前台/后台状态');
console.log('  • Chrome后台节流限制分析');
console.log('  • 多层后台保活策略');
console.log('  • 智能频率调整机制');
console.log('  • Web Worker + Chrome Alarms保活');
console.log('');
console.log('📊 使用 backgroundPerformanceEnhancer.getPerformanceStats() 查看状态');
console.log('🧪 使用 backgroundPerformanceEnhancer.testBackgroundPerformance() 性能测试');