/**
 * 简化异常检测管理器
 * 负责界面交互和异常检测逻辑的协调
 */
class EasyAnomalyManager {
    constructor() {
        this.detector = null;
        this.localDataManager = null;
        this.categoryManager = null;
        this.isRunning = false;
        this.lastResults = [];

        console.log('🎛️ EasyAnomalyManager 初始化');
    }

    /**
     * 初始化管理器
     */
    async init(localDataManager, categoryManager) {
        try {
            this.localDataManager = localDataManager;
            this.categoryManager = categoryManager;

            // 创建检测器实例
            this.detector = new EasyAnomalyDetector(localDataManager, categoryManager);

            // 绑定事件
            this.bindEvents();

            console.log('✅ EasyAnomalyManager 初始化完成');
            return true;
        } catch (error) {
            console.error('❌ EasyAnomalyManager 初始化失败:', error);
            return false;
        }
    }

    /**
     * 绑定事件监听器
     */
    bindEvents() {
        // 运行检测按钮
        const runBtn = document.getElementById('easyRunDetection');
        if (runBtn) {
            runBtn.addEventListener('click', () => {
                this.runDetection();
            });
        }

        // 阈值输入框的实时验证
        const salesInput = document.getElementById('easySalesThreshold');
        const revenueInput = document.getElementById('easyRevenueThreshold');

        if (salesInput) {
            salesInput.addEventListener('change', () => {
                this.validateThresholds();
            });
        }

        if (revenueInput) {
            revenueInput.addEventListener('change', () => {
                this.validateThresholds();
            });
        }

        console.log('🔗 事件监听器已绑定');
    }

    /**
     * 运行异常检测
     */
    async runDetection() {
        if (this.isRunning) {
            console.log('检测正在运行中...');
            return;
        }

        try {
            this.isRunning = true;

            // 更新UI状态
            this.updateDetectionStatus('running', '检测中...');

            // 获取用户设置的阈值
            const salesThreshold = this.getSalesThreshold();
            const revenueThreshold = this.getRevenueThreshold();

            // 更新检测器阈值
            this.detector.setThresholds(salesThreshold, revenueThreshold);

            // 执行检测
            const result = await this.detector.detectAllAnomalies();

            if (result.success) {
                // 保存结果
                this.lastResults = result.anomalies;

                // 更新状态
                this.updateDetectionStatus('success', '检测完成');

                // 发送结果到数据管理器页面
                this.sendResultsToDataManager(result);

                // 显示提示
                this.showNotification(`检测完成：发现 ${result.anomaliesFound} 个异常商品，请到数据管理器查看详情`, 'success');

                // 直接在控制台显示结果用于调试
                console.log('🔍 检测到的异常商品列表：');
                result.anomalies.forEach((anomaly, index) => {
                    console.log(`${index + 1}. ${anomaly.product_name} - 销量:${anomaly.sales_24h}, 销售额:${anomaly.revenue_24h}`);
                });
            } else {
                // 显示错误
                this.updateDetectionStatus('error', '检测失败');
                this.showNotification('异常检测失败', 'error');
            }

        } catch (error) {
            console.error('异常检测执行失败:', error);
            this.updateDetectionStatus('error', '检测失败');
            this.showNotification('检测过程中发生错误', 'error');
        } finally {
            this.isRunning = false;
        }
    }

    /**
     * 获取销量阈值
     */
    getSalesThreshold() {
        const input = document.getElementById('easySalesThreshold');
        if (!input) return 50;

        const value = parseInt(input.value);
        // 如果解析失败（NaN），返回默认值；如果是0或其他数字，返回该值
        return isNaN(value) ? 50 : value;
    }

    /**
     * 获取销售额阈值
     */
    getRevenueThreshold() {
        const input = document.getElementById('easyRevenueThreshold');
        if (!input) return 500;

        const value = parseInt(input.value);
        // 如果解析失败（NaN），返回默认值；如果是0或其他数字，返回该值
        return isNaN(value) ? 500 : value;
    }

    /**
     * 验证阈值设置
     */
    validateThresholds() {
        const salesThreshold = this.getSalesThreshold();
        const revenueThreshold = this.getRevenueThreshold();

        // 验证范围（允许0值）
        if (salesThreshold < 0 || salesThreshold > 9999) {
            this.showNotification('销量阈值应在0-9999之间', 'warning');
            return false;
        }

        if (revenueThreshold < 0 || revenueThreshold > 99999) {
            this.showNotification('销售额阈值应在0-99999之间', 'warning');
            return false;
        }

        return true;
    }

    /**
     * 更新检测状态
     */
    updateDetectionStatus(status, text) {
        const statusDot = document.getElementById('easyStatusDot');
        const statusText = document.getElementById('easyStatusText');

        if (statusDot) {
            statusDot.className = `status-dot ${status}`;
        }

        if (statusText) {
            statusText.textContent = text;
        }
    }

    /**
     * 发送检测结果到数据管理器页面
     */
    sendResultsToDataManager(result) {
        try {
            console.log('🔄 准备发送检测结果到数据管理器:', result);

            // 通过ComponentBridge发送消息到数据管理器页面
            const componentBridge = window.getComponentBridge ? window.getComponentBridge() : null;

            if (componentBridge) {
                const messageData = {
                    success: true,
                    result: {
                        anomaliesFound: result.anomaliesFound,
                        checkedCount: result.checkedCount,
                        anomalies: result.anomalies,
                        thresholds: result.thresholds,
                        detectionTime: result.detectionTime
                    }
                };

                console.log('📤 发送消息到数据管理器:', messageData);

                componentBridge.sendMessage('data-manager', 'ANOMALY_DETECTION_COMPLETED', messageData);
                console.log('✅ 异常检测结果已发送到数据管理器');

                // ultrathink: 增加调试信息
                console.log('🔍 调试信息 - window.dataManagerApp存在:', !!window.dataManagerApp);
                console.log('🔍 调试信息 - handleAnomalyDetectionCompleted方法存在:',
                    !!(window.dataManagerApp && window.dataManagerApp.handleAnomalyDetectionCompleted));
                console.log('🔍 调试信息 - 全局方法存在:', !!window.receiveAnomalyDetectionResults);

                // 如果有数据管理器实例，直接调用方法
                if (window.dataManagerApp && window.dataManagerApp.handleAnomalyDetectionCompleted) {
                    console.log('🔄 直接调用数据管理器方法');
                    window.dataManagerApp.handleAnomalyDetectionCompleted({ result: messageData.result });
                } else {
                    // 尝试通过opener访问数据管理器窗口
                    console.log('🔍 尝试访问其他窗口的数据管理器...');
                    try {
                        // 检查是否有其他窗口打开了数据管理器
                        if (window.opener && window.opener.dataManagerApp) {
                            console.log('🎯 找到opener窗口的数据管理器');
                            window.opener.dataManagerApp.handleAnomalyDetectionCompleted({ result: messageData.result });
                        }
                    } catch (e) {
                        console.log('⚠️ 无法访问opener窗口:', e.message);
                    }
                }

                // 全局方法备用方案
                if (window.receiveAnomalyDetectionResults) {
                    console.log('🔄 使用全局方法传递结果');
                    window.receiveAnomalyDetectionResults({ result: messageData.result });
                }

            } else {
                console.warn('⚠️ ComponentBridge不可用，尝试直接调用数据管理器');

                // 备用方案：直接调用数据管理器
                if (window.dataManagerApp && window.dataManagerApp.handleAnomalyDetectionCompleted) {
                    window.dataManagerApp.handleAnomalyDetectionCompleted({
                        result: {
                            anomaliesFound: result.anomaliesFound,
                            checkedCount: result.checkedCount,
                            anomalies: result.anomalies,
                            thresholds: result.thresholds,
                            detectionTime: result.detectionTime
                        }
                    });
                    console.log('✅ 直接调用数据管理器成功');
                } else if (window.receiveAnomalyDetectionResults) {
                    console.log('🔄 使用全局方法传递结果');
                    window.receiveAnomalyDetectionResults({
                        result: {
                            anomaliesFound: result.anomaliesFound,
                            checkedCount: result.checkedCount,
                            anomalies: result.anomalies,
                            thresholds: result.thresholds,
                            detectionTime: result.detectionTime
                        }
                    });
                    console.log('✅ 全局方法调用成功');
                } else {
                    console.error('❌ 数据管理器不可用');
                    this.showNotification('请先打开数据管理器页面', 'warning');
                }
            }
        } catch (error) {
            console.error('❌ 发送检测结果失败:', error);
        }
    }

    // UI展示功能已移至数据管理器页面，此处保留用于兼容性的空方法

    /**
     * 显示通知
     */
    showNotification(message, type = 'info') {
        // 这里可以集成现有的通知系统
        console.log(`📢 [${type.toUpperCase()}] ${message}`);

        // 如果有现有的通知方法，可以调用
        if (window.xiaohongShuMonitor && window.xiaohongShuMonitor.showNotification) {
            window.xiaohongShuMonitor.showNotification(message, type);
        }
    }

    /**
     * 获取最后的检测结果
     */
    getLastResults() {
        return this.lastResults;
    }

    /**
     * 重置状态
     */
    reset() {
        this.isRunning = false;
        this.lastResults = [];
        this.updateDetectionStatus('ready', '就绪');
        this.showResultsPanel(false);
    }
}

// 浏览器环境导出
if (typeof window !== 'undefined') {
    window.EasyAnomalyManager = EasyAnomalyManager;

    // ultrathink: 独立初始化异常检测系统
    const initStandaloneAnomalyDetection = () => {
        console.log('🔧 开始独立初始化异常检测系统...');

        // 检查是否已经有实例
        if (window.easyAnomalyManager) {
            console.log('✅ EasyAnomalyManager实例已存在');
            return;
        }

        // 等待必要的依赖加载
        if (!window.LocalDataManager || !window.CategoryManager) {
            console.log('⏳ 等待依赖加载完成...');
            setTimeout(initStandaloneAnomalyDetection, 500);
            return;
        }

        try {
            // 创建实例
            const manager = new EasyAnomalyManager();
            window.easyAnomalyManager = manager;

            // 创建简化的数据服务
            const localDataManager = new LocalDataManager();
            const categoryManager = new CategoryManager();

            // 尝试初始化
            Promise.all([
                localDataManager.init(),
                categoryManager.init()
            ]).then(() => {
                return manager.init(localDataManager, categoryManager);
            }).then(success => {
                if (success) {
                    console.log('✅ 独立异常检测系统初始化成功');
                } else {
                    console.error('❌ 独立异常检测系统初始化失败');
                }
            }).catch(error => {
                console.error('❌ 独立异常检测系统初始化异常:', error);
            });

        } catch (error) {
            console.error('❌ 创建独立异常检测系统失败:', error);
        }
    };

    // 页面加载完成后自动尝试初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(initStandaloneAnomalyDetection, 1000);
        });
    } else {
        setTimeout(initStandaloneAnomalyDetection, 1000);
    }
}

// Node.js环境导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EasyAnomalyManager;
}