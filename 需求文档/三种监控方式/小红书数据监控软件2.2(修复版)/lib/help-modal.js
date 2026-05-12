// ==================== 使用说明帮助功能 ====================

/**
 * 初始化使用说明功能
 */
function initHelpModal() {
    const helpBtn = document.getElementById('helpBtn');
    const helpModal = document.getElementById('helpModal');
    const closeHelpBtn = document.getElementById('closeHelpBtn');
    const helpModalOverlay = helpModal?.querySelector('.help-modal-overlay');

    // 打开帮助弹窗
    if (helpBtn) {
        helpBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            if (helpModal) {
                helpModal.style.display = 'flex';
                console.log('📖 打开使用说明');
            }
        });
    }

    // 关闭帮助弹窗
    function closeModal() {
        if (helpModal) {
            helpModal.style.display = 'none';
            console.log('📖 关闭使用说明');
        }
    }

    if (closeHelpBtn) {
        closeHelpBtn.addEventListener('click', closeModal);
    }

    // 点击遮罩层关闭
    if (helpModalOverlay) {
        helpModalOverlay.addEventListener('click', closeModal);
    }

    // 按ESC键关闭
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && helpModal && helpModal.style.display === 'flex') {
            closeModal();
        }
    });

    // 初始化标签切换功能
    initHelpTabs();
}

/**
 * 初始化帮助标签切换
 */
function initHelpTabs() {
    const helpTabs = document.querySelectorAll('.help-tab');
    const helpContents = document.querySelectorAll('.help-content');

    helpTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');

            // 移除所有active类
            helpTabs.forEach(t => t.classList.remove('active'));
            helpContents.forEach(c => c.classList.remove('active'));

            // 添加active类到当前标签
            this.classList.add('active');
            const targetContent = document.getElementById('help-' + targetTab);
            if (targetContent) {
                targetContent.classList.add('active');
            }

            console.log('📖 切换到标签: ' + targetTab);
        });
    });
}

// 在DOM加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initHelpModal);
} else {
    // DOM已经加载完成，直接初始化
    initHelpModal();
}
