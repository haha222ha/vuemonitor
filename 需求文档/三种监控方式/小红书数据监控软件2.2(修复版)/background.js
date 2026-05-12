/**
 * 流量蜂小红书数据监控助手 - 后台脚本
 * Background Service Worker for Xiaohongshu Data Monitor Extension
 */

class XiaohongshuBackground {
    constructor() {
        this.init();
    }

    /**
     * 初始化后台脚本
     */
    init() {
        console.log('🚀 流量蜂小红书数据监控助手后台脚本开始初始化');
        console.log('Chrome版本信息:', navigator.userAgent);
        console.log('可用API检查:', {
            sidePanel: !!chrome.sidePanel,
            sidePanelOpen: !!(chrome.sidePanel && chrome.sidePanel.open),
            sidePanelSetOptions: !!(chrome.sidePanel && chrome.sidePanel.setOptions),
            windows: !!chrome.windows,
            tabs: !!chrome.tabs
        });

        // 监听插件安装和更新
        chrome.runtime.onInstalled.addListener((details) => {
            console.log('📦 插件安装/更新事件:', details);
            this.handleInstallation(details);
        });

        // 监听侧边栏动作按钮点击
        chrome.action.onClicked.addListener((tab) => {
            console.log('🔘 动作按钮被点击');
            this.handleActionClick(tab);
        });

        // 监听标签页更新
        chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
            this.handleTabUpdate(tabId, changeInfo, tab);
        });

        // 监听标签页激活
        chrome.tabs.onActivated.addListener((activeInfo) => {
            this.handleTabActivation(activeInfo);
        });

        // 监听来自其他脚本的消息
        chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
            this.handleMessage(message, sender, sendResponse);
            return true; // 保持消息通道开放
        });

        // 监听侧边栏状态变化
        if (chrome.sidePanel && chrome.sidePanel.onVisibilityChanged) {
            chrome.sidePanel.onVisibilityChanged.addListener((details) => {
                this.handleSidePanelVisibilityChange(details);
            });
        }

        console.log('流量蜂小红书数据监控助手后台脚本已启动');
    }

    /**
     * 处理插件安装和更新
     */
    async handleInstallation(details) {
        console.log('插件安装/更新:', details.reason);

        switch (details.reason) {
            case 'install':
                await this.handleFirstInstall();
                break;
            case 'update':
                await this.handleUpdate(details.previousVersion);
                break;
            case 'chrome_update':
                console.log('Chrome浏览器更新');
                break;
        }
    }

    /**
     * 处理首次安装
     */
    async handleFirstInstall() {
        console.log('首次安装插件');

        try {
            // 检查是否存在数据恢复机会
            await this.checkForDataRecovery();

            // 设置默认配置
            await chrome.storage.sync.set({
                settings: {
                    autoExtract: false,
                    soundNotification: true,
                    theme: 'light'
                }
            });

            // 初始化历史记录
            await chrome.storage.local.set({
                history: [],
                statistics: {
                    totalExtractions: 0,
                    successfulExtractions: 0,
                    firstInstallDate: new Date().toISOString()
                }
            });

            // 显示欢迎页面（可选）
            // chrome.tabs.create({
            //     url: chrome.runtime.getURL('welcome.html')
            // });

            console.log('插件初始化完成');
        } catch (error) {
            console.error('插件初始化失败:', error);
        }
    }

    /**
     * 处理插件更新
     */
    async handleUpdate(previousVersion) {
        console.log(`插件从版本 ${previousVersion} 更新到当前版本`);

        try {
            // 获取现有设置
            const result = await chrome.storage.sync.get(['settings']);
            const currentSettings = result.settings || {};

            // 合并新的默认设置
            const defaultSettings = {
                autoExtract: false,
                soundNotification: true,
                theme: 'light'
            };

            const mergedSettings = { ...defaultSettings, ...currentSettings };
            await chrome.storage.sync.set({ settings: mergedSettings });

            // 更新统计信息
            const statsResult = await chrome.storage.local.get(['statistics']);
            const stats = statsResult.statistics || {};
            stats.lastUpdateDate = new Date().toISOString();
            stats.previousVersion = previousVersion;
            
            await chrome.storage.local.set({ statistics: stats });

            console.log('插件更新完成');
        } catch (error) {
            console.error('插件更新处理失败:', error);
        }
    }

    /**
     * 处理工具栏按钮点击
     * 强制使用侧边栏模式：不再使用弹窗备选方案，专注于侧边栏打开
     */
    async handleActionClick(tab) {
        console.log('🔘 工具栏按钮被点击');
        console.log('📋 标签页信息:', {
            id: tab.id,
            url: tab.url,
            windowId: tab.windowId,
            active: tab.active
        });
        
        try {
            // 获取当前窗口信息
            const currentWindow = await chrome.windows.getCurrent();
            console.log('🪟 当前窗口:', currentWindow);
            
            // 检查Chrome版本和侧边栏API可用性
            const hasSidePanelAPI = chrome.sidePanel && typeof chrome.sidePanel.open === 'function';
            
            if (hasSidePanelAPI) {
                console.log('✓ 检测到侧边栏API可用');
                
                // 尝试使用windowId打开侧边栏（优先）
                try {
                    await chrome.sidePanel.open({ 
                        windowId: tab.windowId || currentWindow.id 
                    });
                    console.log('✅ 侧边栏已通过sidePanel.open(windowId)打开');
                    return;
                } catch (windowError) {
                    console.warn('⚠️ windowId方式打开失败:', windowError.message);
                    
                    // 尝试使用tabId打开侧边栏
                    try {
                        await chrome.sidePanel.open({ tabId: tab.id });
                        console.log('✅ 侧边栏已通过sidePanel.open(tabId)打开');
                        return;
                    } catch (tabError) {
                        console.warn('⚠️ tabId方式打开失败:', tabError.message);
                    }
                }
                
                // 尝试设置侧边栏选项
                if (chrome.sidePanel.setOptions) {
                    try {
                        await chrome.sidePanel.setOptions({
                            tabId: tab.id,
                            path: 'sidepanel.html',
                            enabled: true
                        });
                        
                        if (chrome.sidePanel.setPanelBehavior) {
                            await chrome.sidePanel.setPanelBehavior({ 
                                openPanelOnActionClick: true 
                            });
                        }
                        
                        // 再次尝试打开
                        await chrome.sidePanel.open({ windowId: tab.windowId || currentWindow.id });
                        console.log('✅ 侧边栏已通过setOptions+open打开');
                        return;
                    } catch (setOptionsError) {
                        console.warn('⚠️ setOptions方法失败:', setOptionsError.message);
                    }
                }
            } else {
                console.log('⚠️ 当前Chrome版本不支持侧边栏API');
            }

            // 强制使用侧边栏：不使用弹窗备选方案
            console.log('🔄 侧边栏打开失败，请重新点击插件图标或检查Chrome版本');

            // 显示通知告知用户
            if (chrome.notifications) {
                chrome.notifications.create({
                    type: 'basic',
                    iconUrl: 'icons/icon48.png',
                    title: '流量蜂小红书数据监控助手',
                    message: '侧边栏打开失败，请重新点击插件图标或更新Chrome浏览器'
                });
            }
            
        } catch (error) {
            console.error('❌ 侧边栏打开失败:', error);

            // 显示错误通知
            if (chrome.notifications) {
                chrome.notifications.create({
                    type: 'basic',
                    iconUrl: 'icons/icon48.png',
                    title: '流量蜂小红书数据监控助手',
                    message: `打开失败: ${error.message}，请重试或检查浏览器版本`
                });
            }
        }
    }

    /**
     * 处理标签页更新
     */
    handleTabUpdate(tabId, changeInfo, tab) {
        // 只处理状态为完成的更新
        if (changeInfo.status !== 'complete') return;
        
        // 检查是否为小红书页面
        if (this.isXiaohongshuUrl(tab.url)) {
            console.log('检测到小红书页面:', tab.url);
            
            // 可以在这里设置特定的行为，比如显示特殊图标
            this.updateActionIcon(tabId, true);
            
            // 通知侧边栏页面变化
            this.notifySidePanel('pageUpdate', { url: tab.url, tabId });
        } else {
            this.updateActionIcon(tabId, false);
        }
    }

    /**
     * 处理标签页激活
     */
    async handleTabActivation(activeInfo) {
        try {
            const tab = await chrome.tabs.get(activeInfo.tabId);
            
            if (this.isXiaohongshuUrl(tab.url)) {
                this.updateActionIcon(activeInfo.tabId, true);
                this.notifySidePanel('tabActivated', { url: tab.url, tabId: activeInfo.tabId });
            } else {
                this.updateActionIcon(activeInfo.tabId, false);
            }
        } catch (error) {
            console.error('处理标签页激活失败:', error);
        }
    }

    /**
     * 处理消息
     */
    async handleMessage(message, sender, sendResponse) {
        try {
            switch (message.action) {
                case 'openTab':
                    await this.openTab(message.url);
                    sendResponse({ success: true });
                    break;

                case 'updateStatistics':
                    await this.updateStatistics(message.data);
                    sendResponse({ success: true });
                    break;

                case 'getTabInfo':
                    const tabInfo = await this.getActiveTabInfo();
                    sendResponse({ success: true, data: tabInfo });
                    break;

                case 'closeTab':
                    if (message.tabId) {
                        await chrome.tabs.remove(message.tabId);
                        sendResponse({ success: true });
                    }
                    break;

                case 'syncIncognitoData':
                    await this.syncIncognitoData(message.data);
                    sendResponse({ success: true });
                    break;

                case 'getIncognitoStatus':
                    const incognitoStatus = await this.getIncognitoStatus(sender);
                    sendResponse({ success: true, data: incognitoStatus });
                    break;

                default:
                    console.log('收到未知消息:', message);
                    sendResponse({ success: false, error: '未知消息类型' });
            }
        } catch (error) {
            console.error('处理消息失败:', error);
            sendResponse({ success: false, error: error.message });
        }
    }

    /**
     * 处理侧边栏可见性变化
     */
    handleSidePanelVisibilityChange(details) {
        console.log('侧边栏可见性变化:', details);
        
        if (details.isVisible) {
            console.log('侧边栏已打开');
        } else {
            console.log('侧边栏已关闭');
        }
    }

    /**
     * 检查是否为小红书URL
     */
    isXiaohongshuUrl(url) {
        if (!url) return false;
        const xiaohongshuPattern = /^https?:\/\/(www\.)?xiaohongshu\.com/i;
        return xiaohongshuPattern.test(url);
    }

    /**
     * 更新动作图标
     */
    async updateActionIcon(tabId, isXiaohongshuPage) {
        try {
            // 首先检查标签页是否仍然存在
            const tab = await new Promise((resolve) => {
                chrome.tabs.get(tabId, (tab) => {
                    if (chrome.runtime.lastError) {
                        // 标签页不存在，返回 null
                        resolve(null);
                    } else {
                        resolve(tab);
                    }
                });
            });

            if (!tab) {
                // 标签页已关闭，无需更新图标
                return;
            }

            if (isXiaohongshuPage) {
                // 在小红书页面时显示活跃图标
                await chrome.action.setIcon({
                    tabId: tabId,
                    path: {
                        "16": "icons/icon16.png",
                        "32": "icons/icon32.png",
                        "48": "icons/icon48.png",
                        "128": "icons/icon128.png"
                    }
                });
                await chrome.action.setTitle({
                    tabId: tabId,
                    title: "小红书数据监控 - 点击提取数据"
                });
            } else {
                // 在其他页面时显示默认图标
                await chrome.action.setTitle({
                    tabId: tabId,
                    title: "小红书数据监控 - 在小红书商品页面可用"
                });
            }
        } catch (error) {
            // 只在不是标签页不存在的错误时才记录
            if (!error.message.includes('No tab with id')) {
                console.error('更新图标失败:', error);
            }
        }
    }

    /**
     * 通知侧边栏
     */
    async notifySidePanel(action, data) {
        try {
            // 尝试发送消息给侧边栏
            await chrome.runtime.sendMessage({
                action: action,
                data: data,
                sender: 'background'
            });
        } catch (error) {
            // 侧边栏可能未打开，忽略错误
            console.debug('发送给侧边栏的消息失败:', error.message);
        }
    }

    /**
     * 打开新标签页
     */
    async openTab(url) {
        return chrome.tabs.create({ 
            url: url,
            active: false  // 在后台打开
        });
    }

    /**
     * 获取当前活跃标签页信息
     */
    async getActiveTabInfo() {
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            return {
                id: tab.id,
                url: tab.url,
                title: tab.title,
                isXiaohongshu: this.isXiaohongshuUrl(tab.url)
            };
        } catch (error) {
            console.error('获取标签页信息失败:', error);
            return null;
        }
    }

    /**
     * 更新统计信息
     */
    async updateStatistics(data) {
        try {
            const result = await chrome.storage.local.get(['statistics']);
            const stats = result.statistics || {
                totalExtractions: 0,
                successfulExtractions: 0,
                firstInstallDate: new Date().toISOString()
            };

            if (data.type === 'extraction_attempt') {
                stats.totalExtractions++;
            } else if (data.type === 'extraction_success') {
                stats.successfulExtractions++;
            }

            stats.lastExtractionDate = new Date().toISOString();
            
            await chrome.storage.local.set({ statistics: stats });
            console.log('统计信息已更新:', stats);
        } catch (error) {
            console.error('更新统计信息失败:', error);
        }
    }

    /**
     * 清理存储数据
     */
    async cleanupStorage() {
        try {
            // 清理过期的历史记录（保留最近30天）
            const result = await chrome.storage.local.get(['history']);
            const history = result.history || [];
            
            const thirtyDaysAgo = new Date();
            thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
            
            const filteredHistory = history.filter(item => {
                const itemDate = new Date(item.timestamp);
                return itemDate > thirtyDaysAgo;
            });
            
            if (filteredHistory.length !== history.length) {
                await chrome.storage.local.set({ history: filteredHistory });
                console.log(`清理了 ${history.length - filteredHistory.length} 条过期历史记录`);
            }
        } catch (error) {
            console.error('清理存储失败:', error);
        }
    }
}

// 创建后台脚本实例
const background = new XiaohongshuBackground();

// 定期清理存储（每天运行一次）
if (chrome.alarms) {
    try {
        chrome.alarms.create('cleanup', { periodInMinutes: 24 * 60 });
        chrome.alarms.onAlarm.addListener((alarm) => {
            if (alarm.name === 'cleanup') {
                background.cleanupStorage();
            }
        });
        console.log('✅ 定期清理任务已设置');
    } catch (error) {
        console.warn('⚠️ 定期清理任务设置失败:', error.message);
    }
} else {
    console.warn('⚠️ chrome.alarms API不可用，跳过定期清理任务');
}