/**
 * 简单折线图渲染器 - 异常商品悬浮图表专用
 * Simple Line Chart Renderer for Anomaly Product Hover Charts
 *
 * 功能特点：
 * 1. 轻量级Canvas绘制，无外部依赖
 * 2. 专门为销量时间序列数据优化
 * 3. 支持中文日期标签显示
 * 4. 自动缩放和布局计算
 */
class SimpleLineChart {
    constructor(canvas, options = {}) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');

        // 默认配置
        this.options = {
            width: 280,
            height: 100,
            padding: {
                top: 15,
                right: 15,
                bottom: 25,
                left: 40
            },
            colors: {
                line: '#3b82f6',           // 蓝色折线
                point: '#1d4ed8',          // 深蓝数据点
                pointBase: '#10b981',      // 🎯 基础销量点绿色
                pointAnomaly: '#ef4444',   // 🎯 异常数据点红色
                grid: '#f1f5f9',           // 浅灰网格
                text: '#475569',           // 🎯 更深的文字色
                background: '#ffffff'       // 白色背景
            },
            line: {
                width: 2,
                tension: 0.3  // 曲线张力
            },
            point: {
                radius: 3,
                hoverRadius: 5
            },
            font: {
                size: 11,  // 🎯 稍大字号
                family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif',  // 🎯 现代字体栈
                weight: '500'  // 🎯 中等字重
            },
            ...options
        };

        // 图表数据
        this.data = [];
        this.chartArea = {};

        console.log('📊 SimpleLineChart 初始化完成');
    }

    /**
     * 设置图表数据
     * @param {Array} data - 图表数据 [{date, sales, timestamp}]
     */
    setData(data) {
        this.data = data || [];
        console.log(`📈 设置图表数据，共 ${this.data.length} 个数据点:`, this.data);
    }

    /**
     * 渲染图表
     */
    render() {
        if (!this.data || this.data.length === 0) {
            this.renderNoData();
            return;
        }

        console.log('🎨 开始渲染图表...');

        // 清空画布
        this.clearCanvas();

        // 计算布局
        this.calculateChartArea();

        // 计算数据范围
        this.calculateDataRange();

        // 绘制图表元素
        this.drawBackground();
        this.drawGrid();
        this.drawLine();
        this.drawPoints();
        this.drawDataLabels();  // 🎯 新增：绘制数据标签
        this.drawLabels();

        console.log('✅ 图表渲染完成');
    }

    /**
     * 清空画布
     */
    clearCanvas() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }

    /**
     * 计算图表区域
     */
    calculateChartArea() {
        const { padding } = this.options;

        this.chartArea = {
            x: padding.left,
            y: padding.top,
            width: this.options.width - padding.left - padding.right,
            height: this.options.height - padding.top - padding.bottom
        };

        console.log('📐 图表区域计算完成:', this.chartArea);
    }

    /**
     * 计算数据范围
     */
    calculateDataRange() {
        if (this.data.length === 0) return;

        const salesValues = this.data.map(d => d.sales);

        this.dataRange = {
            minSales: Math.min(...salesValues),
            maxSales: Math.max(...salesValues),
            salesSpan: Math.max(...salesValues) - Math.min(...salesValues)
        };

        // 添加一些padding让图表看起来更好
        const padding = this.dataRange.salesSpan * 0.1 || 50;
        this.dataRange.minSales = Math.max(0, this.dataRange.minSales - padding);
        this.dataRange.maxSales = this.dataRange.maxSales + padding;
        this.dataRange.salesSpan = this.dataRange.maxSales - this.dataRange.minSales;

        console.log('📊 数据范围计算完成:', this.dataRange);
    }

    /**
     * 绘制背景
     */
    drawBackground() {
        this.ctx.fillStyle = this.options.colors.background;
        this.ctx.fillRect(0, 0, this.options.width, this.options.height);
    }

    /**
     * 绘制网格线
     */
    drawGrid() {
        const { ctx, chartArea, options } = this;

        ctx.strokeStyle = options.colors.grid;
        ctx.lineWidth = 1;
        ctx.setLineDash([2, 2]);

        // 水平网格线 (Y轴)
        const yLines = 4;
        for (let i = 0; i <= yLines; i++) {
            const y = chartArea.y + (chartArea.height / yLines) * i;

            ctx.beginPath();
            ctx.moveTo(chartArea.x, y);
            ctx.lineTo(chartArea.x + chartArea.width, y);
            ctx.stroke();
        }

        // 垂直网格线 (X轴) - 根据数据点数量
        if (this.data.length > 1) {
            const xStep = chartArea.width / (this.data.length - 1);
            for (let i = 0; i < this.data.length; i++) {
                const x = chartArea.x + xStep * i;

                ctx.beginPath();
                ctx.moveTo(x, chartArea.y);
                ctx.lineTo(x, chartArea.y + chartArea.height);
                ctx.stroke();
            }
        }

        ctx.setLineDash([]); // 重置虚线
    }

    /**
     * 绘制折线
     */
    drawLine() {
        if (this.data.length < 2) return;

        const { ctx, chartArea, dataRange, options } = this;

        // 🎯 创建渐变色彩
        const lineGradient = ctx.createLinearGradient(chartArea.x, 0, chartArea.x + chartArea.width, 0);
        lineGradient.addColorStop(0, '#93c5fd');  // 淡蓝
        lineGradient.addColorStop(0.5, '#3b82f6'); // 中蓝
        lineGradient.addColorStop(1, '#1d4ed8');   // 深蓝

        // 🎯 设置阴影效果
        ctx.shadowColor = 'rgba(59, 130, 246, 0.3)';
        ctx.shadowBlur = 4;
        ctx.shadowOffsetY = 2;

        ctx.strokeStyle = lineGradient;
        ctx.lineWidth = options.line.width;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        // 计算坐标点
        const points = this.data.map((d, index) => ({
            x: chartArea.x + (chartArea.width / (this.data.length - 1)) * index,
            y: chartArea.y + chartArea.height -
               ((d.sales - dataRange.minSales) / dataRange.salesSpan) * chartArea.height
        }));

        // 绘制折线
        ctx.beginPath();
        ctx.moveTo(points[0].x, points[0].y);

        for (let i = 1; i < points.length; i++) {
            ctx.lineTo(points[i].x, points[i].y);
        }

        ctx.stroke();

        // 🎯 清除阴影效果
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
        ctx.shadowOffsetY = 0;

        // 保存点坐标供绘制数据点使用
        this.calculatedPoints = points;
    }

    /**
     * 绘制数据点
     */
    drawPoints() {
        if (!this.calculatedPoints) return;

        const { ctx, options } = this;

        this.calculatedPoints.forEach((point, index) => {
            const dataPoint = this.data[index];

            // 🎯 根据数据类型选择颜色
            let pointColor = options.colors.point;
            if (dataPoint?.isBaseSales) {
                pointColor = options.colors.pointBase;  // 基础销量：绿色
            } else if (dataPoint?.isAnomaly) {
                pointColor = options.colors.pointAnomaly;  // 异常数据：红色
            }

            // 🎯 设置数据点光晕效果
            ctx.shadowColor = pointColor + '60';  // 添加透明度
            ctx.shadowBlur = 6;
            ctx.shadowOffsetX = 0;
            ctx.shadowOffsetY = 0;

            ctx.fillStyle = pointColor;
            ctx.beginPath();
            ctx.arc(point.x, point.y, options.point.radius, 0, Math.PI * 2);
            ctx.fill();

            // 🎯 添加内部高光点
            ctx.shadowColor = 'transparent';
            ctx.shadowBlur = 0;
            ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
            ctx.beginPath();
            ctx.arc(point.x - 0.5, point.y - 0.5, options.point.radius * 0.4, 0, Math.PI * 2);
            ctx.fill();
        });

        // 清除阴影效果
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
    }

    /**
     * 绘制数据标签 - 在每个数据点上方显示具体数值
     */
    drawDataLabels() {
        if (!this.calculatedPoints || !this.data) return;

        const { ctx, chartArea, options } = this;

        // 🎯 设置优化的标签样式
        ctx.fillStyle = options.colors.text;
        ctx.font = `${options.font.weight} ${options.font.size}px ${options.font.family}`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';  // 🎯 改为居中对齐

        this.calculatedPoints.forEach((point, index) => {
            const dataPoint = this.data[index];
            if (!dataPoint) return;

            // 格式化销量数值
            const formattedValue = this.formatSalesValue(dataPoint.sales);

            // 在数据点上方绘制标签，留出一定间距避免重叠
            const labelY = point.y - options.point.radius - 8;

            // 🎯 绘制优化的圆角背景，添加边界检测
            const textWidth = ctx.measureText(formattedValue).width;
            const padding = 6;  // 更大内边距
            const bgWidth = textWidth + padding * 2;
            const bgHeight = 16;
            const radius = 8;  // 更大圆角

            // 🎯 边界检测和自适应定位
            let bgX = point.x - textWidth / 2 - padding;
            let bgY = labelY - 14;

            // 检测右边界
            if (bgX + bgWidth > chartArea.x + chartArea.width) {
                bgX = chartArea.x + chartArea.width - bgWidth;
            }

            // 检测左边界
            if (bgX < chartArea.x) {
                bgX = chartArea.x;
            }

            // 检测上边界
            if (bgY < chartArea.y) {
                bgY = chartArea.y;
            }

            // 🎯 背景阴影效果
            ctx.shadowColor = 'rgba(0, 0, 0, 0.12)';
            ctx.shadowBlur = 6;
            ctx.shadowOffsetY = 2;

            // 绘制圆角矩形背景
            ctx.fillStyle = 'rgba(255, 255, 255, 0.98)';
            ctx.beginPath();
            ctx.roundRect(bgX, bgY, bgWidth, bgHeight, radius);
            ctx.fill();

            // 清除阴影
            ctx.shadowColor = 'transparent';
            ctx.shadowBlur = 0;
            ctx.shadowOffsetY = 0;

            // 🎯 添加细微边框
            ctx.strokeStyle = 'rgba(59, 130, 246, 0.2)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.roundRect(bgX, bgY, bgWidth, bgHeight, radius);
            ctx.stroke();

            // 🎯 绘制文字，根据调整后的背景位置居中
            ctx.fillStyle = options.colors.text;
            const textX = bgX + bgWidth / 2;  // 在调整后的背景中心
            const textY = bgY + bgHeight / 2;  // 在背景垂直中心
            ctx.fillText(formattedValue, textX, textY);
        });

        console.log('📊 数据标签绘制完成');
    }

    /**
     * 格式化销量数值显示 - 显示具体数值
     */
    formatSalesValue(sales) {
        // 🎯 修复：直接显示具体数值，添加千分位分隔符提升可读性
        return Number(sales).toLocaleString('zh-CN');
    }

    /**
     * 绘制标签
     */
    drawLabels() {
        this.drawXLabels();
        this.drawYLabels();
    }

    /**
     * 绘制X轴标签（日期）
     */
    drawXLabels() {
        const { ctx, chartArea, options } = this;

        ctx.fillStyle = options.colors.text;
        ctx.font = `${options.font.weight} ${options.font.size}px ${options.font.family}`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';

        // 根据数据点数量决定显示哪些标签
        const maxLabels = 5; // 最多显示5个标签
        const step = Math.max(1, Math.ceil(this.data.length / maxLabels));

        this.data.forEach((d, index) => {
            if (index % step === 0 || index === this.data.length - 1) {
                const x = chartArea.x + (chartArea.width / (this.data.length - 1)) * index;
                const y = chartArea.y + chartArea.height + 5;

                // 处理长日期标签
                let label = d.date;
                if (label.length > 6) {
                    label = label.substring(0, 5) + '..';
                }

                ctx.fillText(label, x, y);
            }
        });
    }

    /**
     * 绘制Y轴标签（销量）
     */
    drawYLabels() {
        const { ctx, chartArea, dataRange, options } = this;

        ctx.fillStyle = options.colors.text;
        ctx.font = `${options.font.weight} ${options.font.size}px ${options.font.family}`;
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';

        const yLines = 4;
        for (let i = 0; i <= yLines; i++) {
            const value = dataRange.minSales + (dataRange.salesSpan / yLines) * (yLines - i);
            const y = chartArea.y + (chartArea.height / yLines) * i;

            // 格式化数值显示
            const formattedValue = value >= 1000 ?
                Math.round(value / 1000) + 'k' :
                Math.round(value).toString();

            ctx.fillText(formattedValue, chartArea.x - 5, y);
        }
    }

    /**
     * 渲染无数据状态
     */
    renderNoData() {
        const { ctx, options } = this;

        console.log('📊 渲染无数据状态');

        this.clearCanvas();

        // 背景
        ctx.fillStyle = options.colors.background;
        ctx.fillRect(0, 0, options.width, options.height);

        // 🎯 优化无数据文字样式
        ctx.fillStyle = options.colors.text;
        ctx.font = `${options.font.weight} 12px ${options.font.family}`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        ctx.fillText(
            '暂无时间序列数据',
            options.width / 2,
            options.height / 2 - 5
        );

        ctx.font = `400 10px ${options.font.family}`;  // 🎯 更轻的字重
        ctx.fillText(
            '该商品尚未建立销量历史记录',
            options.width / 2,
            options.height / 2 + 10
        );
    }

    /**
     * 更新画布尺寸
     */
    resize(width, height) {
        this.options.width = width;
        this.options.height = height;
        this.canvas.width = width;
        this.canvas.height = height;

        console.log(`📐 图表尺寸更新: ${width}x${height}`);
    }

    /**
     * 销毁图表
     */
    destroy() {
        this.clearCanvas();
        this.data = null;
        this.calculatedPoints = null;
        console.log('🗑️ SimpleLineChart 已销毁');
    }
}

// 浏览器环境导出
if (typeof window !== 'undefined') {
    window.SimpleLineChart = SimpleLineChart;
}

// Node.js环境导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SimpleLineChart;
}