/**
 * 日期格式化工具类
 * 用于生成动态时间序列字段名
 */
class DateFormatter {
    /**
     * 获取中文日期格式：9月11日
     * @param {Date} date - 日期对象，默认为当前日期
     * @returns {string} 格式化的中文日期字符串
     */
    static getChineseDateFormat(date = new Date()) {
        const month = date.getMonth() + 1;  // 0-based月份+1
        const day = date.getDate();
        return `${month}月${day}日`;
    }
    
    /**
     * 生成动态字段名
     * @param {Date} date - 日期对象，默认为当前日期
     * @returns {Object} 包含所有字段名的对象
     */
    static generateFieldNames(date = new Date()) {
        const dateStr = this.getChineseDateFormat(date);
        return {
            productSales: `商品销量（${dateStr}）`,
            storeSales: `店铺销量（${dateStr}）`,
            crawlTime: `爬取时间（${dateStr}）`
        };
    }
    
    /**
     * 检查字段名是否为指定日期的字段
     * @param {string} fieldName - 字段名
     * @param {Date} date - 目标日期
     * @returns {boolean} 是否为指定日期的字段
     */
    static isDateField(fieldName, date = new Date()) {
        const dateStr = this.getChineseDateFormat(date);
        return fieldName.includes(`（${dateStr}）`);
    }
    
    /**
     * 检查是否为今天的字段
     * @param {string} fieldName - 字段名
     * @returns {boolean} 是否为今天的字段
     */
    static isTodayField(fieldName) {
        return this.isDateField(fieldName, new Date());
    }
    
    /**
     * 从字段名中提取日期字符串
     * @param {string} fieldName - 字段名，如"商品销量（9月11日）"
     * @returns {string|null} 日期字符串，如"9月11日"，提取失败返回null
     */
    static extractDateFromFieldName(fieldName) {
        const match = fieldName.match(/（(.+)）/);
        return match ? match[1] : null;
    }
    
    /**
     * 获取所有时间序列相关的字段前缀
     * @returns {string[]} 字段前缀数组
     */
    static getTimeSeriesFieldPrefixes() {
        return ['商品销量', '店铺销量', '爬取时间'];
    }
    
    /**
     * 检查字段名是否为时间序列字段
     * @param {string} fieldName - 字段名
     * @returns {boolean} 是否为时间序列字段
     */
    static isTimeSeriesField(fieldName) {
        const prefixes = this.getTimeSeriesFieldPrefixes();
        return prefixes.some(prefix => fieldName.startsWith(prefix + '（'));
    }
    
    /**
     * 获取标准化的日期对象（去除时分秒，只保留年月日）
     * @param {Date} date - 输入日期
     * @returns {Date} 标准化的日期对象
     */
    static getStandardizedDate(date = new Date()) {
        const standardized = new Date(date);
        standardized.setHours(0, 0, 0, 0);
        return standardized;
    }
    
    /**
     * 解析中文日期格式为Date对象（仅支持当年）
     * @param {string} chineseDateStr - 中文日期字符串，如"9月11日"
     * @returns {Date|null} Date对象，解析失败返回null
     */
    static parseChineseDateString(chineseDateStr) {
        try {
            const match = chineseDateStr.match(/(\d+)月(\d+)日/);
            if (!match) return null;
            
            const month = parseInt(match[1]) - 1; // 0-based month
            const day = parseInt(match[2]);
            const year = new Date().getFullYear(); // 使用当前年份
            
            const date = new Date(year, month, day);
            return date;
        } catch (error) {
            console.warn('解析中文日期失败:', chineseDateStr, error);
            return null;
        }
    }
}

// 如果在Node.js环境中运行，导出模块
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DateFormatter;
}

// 在浏览器环境中，添加到全局对象
if (typeof window !== 'undefined') {
    window.DateFormatter = DateFormatter;
}