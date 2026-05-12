/**
 * 流量蜂小红书数据监控助手 - 侧边栏脚本 v2.0
 * Side Panel Script for Xiaohongshu Data Monitor Extension
 * 
 * 版本 2.0.0 - 完全移除Feishu依赖，采用本地IndexedDB存储
 */

// 检查必要的依赖库加载状态
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 流量蜂小红书数据监控助手 v2.0 正在加载...');
    
    // 检查XLSX库
    if (typeof XLSX === 'undefined') {
        console.error('❌ XLSX库未加载成功');
        setTimeout(() => {
            if (typeof XLSX === 'undefined') {
                console.error('❌ XLSX库延迟检查仍未成功，可能存在加载问题');
            } else {
                console.log('✅ XLSX库延迟加载成功，版本:', XLSX.version || '未知');
            }
        }, 1000);
    } else {
        console.log('✅ XLSX库加载成功，版本:', XLSX.version || '未知');
    }

    // 检查本地存储组件
    const requiredComponents = ['LocalDataManager', 'CategoryManager', 'DataMigrator'];
    const missingComponents = requiredComponents.filter(comp => typeof window[comp] === 'undefined');
    
    if (missingComponents.length > 0) {
        console.error('❌ 缺少必要组件:', missingComponents);
    } else {
        console.log('✅ 所有必要组件已加载');
    }
});

/**
 * 输入模式管理器 - 处理单行和多行输入模式的切换
 * 保持原有功能不变
 */
class InputModeManager {
    constructor() {
        this.isBatchMode = false;
        this.singleInput = document.getElementById('productUrl');
        this.batchInput = document.getElementById('batchUrlInput');
        this.inputGroup = this.singleInput?.closest('.input-group');
        
        this.initEventListeners();
    }
    
    initEventListeners() {
        // Ctrl+Enter快捷键切换模式
        this.singleInput?.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                this.switchToBatchMode(this.singleInput.value);
            }
        });
        
        this.batchInput?.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                this.switchToSingleMode();
            }
        });
        
        // 自动检测换行符
        this.singleInput?.addEventListener('paste', (e) => {
            setTimeout(() => {
                const text = this.singleInput.value;
                if (text.includes('\n')) {
                    this.switchToBatchMode(text);
                }
            }, 10);
        });
        
        // 实时更新URL计数
        this.batchInput?.addEventListener('input', () => this.updateUrlCount());
        this.singleInput?.addEventListener('input', () => this.updateUrlCount());
    }
    
    switchToBatchMode(initialText = '') {
        if (this.isBatchMode) return;
        
        this.isBatchMode = true;
        this.singleInput.style.display = 'none';
        this.batchInput.style.display = 'block';
        this.inputGroup?.classList.add('batch-mode');
        
        if (initialText) {
            this.batchInput.value = initialText.replace(/\n+/g, '\n').trim();
        }
        
        this.batchInput.focus();
        this.updateModeDisplay();
        this.updateUrlCount();
        
        console.log('✅ 切换到多行输入模式');
    }
    
    switchToSingleMode() {
        if (!this.isBatchMode) return;
        
        const urls = this.getCurrentUrls();
        this.isBatchMode = false;
        this.batchInput.style.display = 'none';
        this.singleInput.style.display = 'block';
        this.inputGroup?.classList.remove('batch-mode');
        
        if (urls.length > 0) {
            this.singleInput.value = urls[0];
        }
        
        this.singleInput.focus();
        this.updateModeDisplay();
        this.updateUrlCount();
        
        console.log('✅ 切换到单行输入模式');
    }
    
    getCurrentUrls() {
        if (this.isBatchMode) {
            return this.batchInput.value.split('\n')
                .map(url => url.trim())
                .filter(url => url.length > 0);
        } else {
            const url = this.singleInput.value.trim();
            return url ? [url] : [];
        }
    }
    
    updateModeDisplay() {
        console.log(`当前模式: ${this.isBatchMode ? '批量输入模式' : '单链接模式'}`);
    }
    
    updateUrlCount() {
        const urls = this.getCurrentUrls();
        console.log(`当前链接数量: ${urls.length}`);
    }
    
    clear() {
        this.singleInput.value = '';
        this.batchInput.value = '';
        this.updateUrlCount();
    }
    
    setValue(text) {
        if (text.includes('\n')) {
            this.switchToBatchMode(text);
        } else {
            if (this.isBatchMode) {
                this.switchToSingleMode();
            }
            this.singleInput.value = text;
        }
        this.updateUrlCount();
    }
}

/**
 * 批量输入适配器 - 将URL数组转换为现有批量监控格式
 * 保持原有功能，优化错误处理
 */
class BatchInputAdapter {
    static convertUrlsToProducts(urls) {
        return urls.map((url, index) => {
            const trimmedUrl = url?.trim();
            
            console.log('🔍 BatchInputAdapter 处理URL:', {
                index: index,
                originalUrl: url,
                trimmedUrl: trimmedUrl
            });

            // 验证URL格式
            if (!trimmedUrl || typeof trimmedUrl !== 'string') {
                console.error(`❌ URL无效 (索引 ${index}):`, { url, trimmedUrl });
                throw new Error(`第${index + 1}个链接格式无效：不是有效的字符串`);
            }

            const xiaohongshuPattern = /^https?:\/\/(www\.)?xiaohongshu\.com/i;
            if (!xiaohongshuPattern.test(trimmedUrl)) {
                console.error(`❌ URL不是小红书链接 (索引 ${index}):`, trimmedUrl);
                throw new Error(`第${index + 1}个链接不是有效的小红书商品链接：${trimmedUrl.substring(0, 50)}...`);
            }

            return {
                productId: null,
                productName: `批量输入商品 ${index + 1}`,
                productUrl: trimmedUrl,
                recordId: null,
                isFromBatchInput: true,
                tempIndex: index
            };
        });
    }
    
    static generateMockRecordId() {
        return 'rec' + Date.now() + Math.random().toString(36).substr(2, 9);
    }
}

/**
 * ❌ 已废弃：销量数据过滤器
 * 说明：该过滤器之前用于过滤零销量商品，现已移除该功能
 * 保留代码以备将来需要时参考
 */
/*
class SalesDataFilter {
    constructor() {
        this.filterStats = {
            total: 0,
            filtered: 0
        };
    }

    filterProduct(product, rowIndex = 0) {
        this.filterStats.total++;
        const sales = this.extractSalesValue(product);

        if (sales === 0) {
            this.filterStats.filtered++;
            return {
                isValid: false,
                reason: '销量为0',
                category: 'zero_sales'
            };
        }

        return { isValid: true, reason: null };
    }

    extractSalesValue(product) {
        const salesFields = [
            'product_sales', 'productSales', 'sales',
            '商品销量', '产品销量', '销量'
        ];

        for (const field of salesFields) {
            if (product[field] !== undefined && product[field] !== null) {
                return this.parseSales(product[field]);
            }
        }

        return 0;
    }

    parseSales(salesText) {
        if (typeof salesText === 'number') return salesText;
        if (!salesText) return 0;

        const text = String(salesText).trim();
        const match = text.match(/([\d,]+(?:\.\d+)?)\s*([万千kK])?/);

        if (!match) return 0;

        let number = parseFloat(match[1].replace(/,/g, ''));
        const unit = match[2];

        if (unit) {
            switch (unit.toLowerCase()) {
                case '万':
                    number *= 10000;
                    break;
                case '千':
                case 'k':
                    number *= 1000;
                    break;
            }
        }

        return Math.max(0, Math.floor(number));
    }

    getFilterStats() {
        const { total, filtered } = this.filterStats;

        return {
            total,
            filtered,
            filteredPercentage: total > 0 ? (filtered / total * 100).toFixed(1) : '0.0',
            summary: filtered === 0
                ? '✅ 所有商品均符合要求，无需过滤'
                : `🔍 已过滤 ${filtered}/${total} 个零销量商品`
        };
    }

    reset() {
        this.filterStats = {
            total: 0,
            filtered: 0
        };
    }
}
*/

/**
 * Excel处理器 - 保持原有功能
 */
class ExcelProcessor {
    constructor() {
        this.supportedFormats = ['.xlsx', '.xls'];
        this.requiredColumns = ['商品链接'];
        this.fieldMapping = {
            '商品链接': 'product_url',
            '商品ID': 'product_id',
            '商品名称': 'product_name',
            '商品销量': 'product_sales',
            '商品价格': 'product_price',
            '店铺销量': 'store_sales',
            '店铺名称': 'store_name',
            '好评人数': 'good_reviews',
            '加购件数': 'cart_count',
            '近3个月销量': 'recent_sales',
            '店铺粉丝数': 'store_followers',
            '备注': 'notes',
            '采集时间': 'extracted_at'
        };

        // 扩展字段映射 - 支持更多可能的列标题变体
        this.extendedFieldMapping = {
            // 商品名称的各种可能表示
            '商品名称': 'product_name',
            '产品名称': 'product_name',
            '商品标题': 'product_name',
            '产品标题': 'product_name',
            '标题': 'product_name',
            'title': 'product_name',
            'name': 'product_name',
            'productName': 'product_name',

            // 商品链接的各种可能表示
            '商品链接': 'product_url',
            '产品链接': 'product_url',
            '链接': 'product_url',
            'url': 'product_url',
            'link': 'product_url',
            'productUrl': 'product_url',

            // 其他字段
            '商品ID': 'product_id',
            '产品ID': 'product_id',
            'id': 'product_id',
            'productId': 'product_id',

            '商品销量': 'product_sales',
            '产品销量': 'product_sales',
            '销量': 'product_sales',
            'sales': 'product_sales',
            'productSales': 'product_sales',

            '商品价格': 'product_price',
            '产品价格': 'product_price',
            '价格': 'product_price',
            'price': 'product_price',
            'productPrice': 'product_price',

            '店铺销量': 'store_sales',
            '店铺总销量': 'store_sales',
            'storeSales': 'store_sales',

            '店铺名称': 'store_name',
            '店铺': 'store_name',
            'storeName': 'store_name',
            'store': 'store_name',

            // additional_data字段映射 - ultrathink修复
            '好评人数': 'good_reviews',
            '好评': 'good_reviews',
            '评价人数': 'good_reviews',
            'goodReviews': 'good_reviews',
            'good_reviews': 'good_reviews',

            '加购件数': 'cart_count',
            '购物车': 'cart_count',
            '加购数量': 'cart_count',
            '加购': 'cart_count',
            'cartCount': 'cart_count',
            'cart_count': 'cart_count',

            '近3个月销量': 'recent_sales',
            '3个月销量': 'recent_sales',
            '月销量': 'recent_sales',
            '最近销量': 'recent_sales',
            'recentSales': 'recent_sales',
            'recent_sales': 'recent_sales',

            '店铺粉丝数': 'store_followers',
            '粉丝数': 'store_followers',           // ✅ 修复：匹配用户Excel列名
            '关注数': 'store_followers',
            '店铺关注': 'store_followers',
            'storeFollowers': 'store_followers',
            'store_followers': 'store_followers',

            // 🎯 ultrathink 增强：更多近3个月销量变体
            '近3个月销量': 'recent_sales',
            '3个月销量': 'recent_sales',
            '3个月内销量': 'recent_sales',
            '3个月内购买': 'recent_sales',         // ✅ 修复：匹配 "3个月内600+人购买"
            '月销量': 'recent_sales',
            '最近销量': 'recent_sales',
            'recentSales': 'recent_sales',
            'recent_sales': 'recent_sales'
        };
    }

    async parseFile(file) {
        return new Promise((resolve, reject) => {
            if (!this.validateFile(file)) {
                reject(new Error('文件格式不支持，请上传 Excel 文件'));
                return;
            }

            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const data = new Uint8Array(e.target.result);
                    const workbook = XLSX.read(data, { type: 'array' });
                    
                    if (!workbook.SheetNames.length) {
                        reject(new Error('Excel文件中没有找到工作表'));
                        return;
                    }

                    const firstSheetName = workbook.SheetNames[0];
                    const worksheet = workbook.Sheets[firstSheetName];
                    const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });

                    const result = this.processSheetData(jsonData);
                    resolve(result);

                } catch (error) {
                    console.error('Excel解析失败:', error);
                    reject(new Error('Excel文件解析失败: ' + error.message));
                }
            };

            reader.onerror = () => {
                reject(new Error('文件读取失败'));
            };

            reader.readAsArrayBuffer(file);
        });
    }

    validateFile(file) {
        const fileName = file.name.toLowerCase();
        return this.supportedFormats.some(format => fileName.endsWith(format));
    }

    processSheetData(jsonData) {
        if (!jsonData || jsonData.length < 2) {
            throw new Error('Excel文件数据不足，至少需要包含标题行和一行数据');
        }

        const headers = jsonData[0];
        const dataRows = jsonData.slice(1);

        // 验证必需列 - 使用扩展字段映射进行更灵活的检查
        const hasRequiredColumns = this.requiredColumns.some(requiredCol => {
            // 检查是否有任何标题映射到required column
            return headers.some(header => {
                const mappedField = this.extendedFieldMapping[header] || this.fieldMapping[header];
                const requiredField = this.extendedFieldMapping[requiredCol] || this.fieldMapping[requiredCol];
                return header === requiredCol || mappedField === requiredField;
            });
        });

        if (!hasRequiredColumns) {
            console.log('🚨 Excel文件标题行:', headers);
            console.log('🚨 需要的列标题:', this.requiredColumns);
            console.log('🚨 支持的列标题变体:', Object.keys(this.extendedFieldMapping).filter(key =>
                this.extendedFieldMapping[key] === 'product_url'
            ));
            throw new Error(`Excel文件缺少必需的列: ${this.requiredColumns.join('、')}。支持的列名变体包括: 商品链接、产品链接、链接、url、link、product_url`);
        }

        // 🚨 ultrathink 修复：处理列名连接问题
        const processedHeaders = headers.map(header => {
            // 修复 "加购件数粉丝数" 这种连接的列名
            if (header === '加购件数粉丝数') {
                console.log('🔧 [修复] 检测到连接列名:', header, '→ 拆分处理');
                return '加购件数'; // 优先映射为加购件数
            }
            // 🎯 ultrathink 增强：处理更多可能的连接列名情况
            if (header && typeof header === 'string') {
                // 处理可能的列名连接情况
                if (header.includes('加购件数') && header.includes('粉丝数')) {
                    console.log('🔧 [修复] 检测到连接列名:', header, '→ 优先映射为加购件数');
                    return '加购件数';
                }
                // 处理其他可能的连接情况
                if (header.includes('好评人数') && header.length > 4) {
                    console.log('🔧 [修复] 检测到连接列名:', header, '→ 优先映射为好评人数');
                    return '好评人数';
                }
            }
            return header;
        });

        console.log('📋 [修复] 原始标题:', headers);
        console.log('📋 [修复] 处理后标题:', processedHeaders);

        // 转换数据
        const products = dataRows.map((row, index) => {
            const product = {};

            processedHeaders.forEach((header, headerIndex) => {
                // 首先尝试扩展映射，然后尝试基础映射，最后使用原始标题
                const fieldName = this.extendedFieldMapping[header] ||
                                  this.fieldMapping[header] ||
                                  header;
                const cellValue = row[headerIndex];

                // 🚨 ultrathink 调试：additional_data字段特别监控
                const isAdditionalDataField = ['good_reviews', 'cart_count', 'recent_sales', 'store_followers'].includes(fieldName);
                if (isAdditionalDataField && index === 0) { // 只记录第一行避免日志过多
                    console.log(`🎯 [ULTRATHINK调试] additional_data字段处理:`, {
                        原始标题: header,
                        映射字段: fieldName,
                        原始值: cellValue,
                        值类型: typeof cellValue,
                        值为空: cellValue === '' || cellValue === null || cellValue === undefined
                    });
                }

                // 🎯 ultrathink 关键修复：处理所有字段，包括空值
                if (cellValue !== undefined && cellValue !== null) {
                    const processedValue = this.formatCellValue(fieldName, cellValue);

                    // 🚨 核心修复：对于additional_data字段，即使是空字符串也要设置，避免undefined
                    if (isAdditionalDataField) {
                        // additional_data字段必须设置，空值设为空字符串
                        product[fieldName] = processedValue !== undefined ? processedValue : '';

                        if (index === 0) {
                            console.log(`🎯 [ULTRATHINK调试] additional_data强制设置:`, {
                                字段: fieldName,
                                原始值: cellValue,
                                处理后: processedValue,
                                最终值: product[fieldName],
                                是否为空: cellValue === ''
                            });
                        }
                    } else {
                        // 普通字段只有非空时才设置
                        if (cellValue !== '') {
                            product[fieldName] = processedValue;
                        }

                        if (fieldName === 'product_id' && index === 0) {
                            console.log(`📝 [ULTRATHINK调试] 基础字段设置:`, {
                                字段: fieldName,
                                原始值: cellValue,
                                最终值: product[fieldName]
                            });
                        }
                    }
                }
            });

            // 验证必要字段 - 🚨 ultrathink 修复：字段名不一致问题
            if (!product.product_url && !product.productUrl) {
                console.warn(`❌ 第${index + 2}行缺少商品链接，跳过。行数据:`, {
                    原始行数据: row,
                    解析后字段: Object.keys(product),
                    product_url: product.product_url,
                    productUrl: product.productUrl
                });
                return null;
            }

            // 🚨 ultrathink 修复：字段标准化 - 统一字段命名
            if (product.product_url && !product.productUrl) {
                product.productUrl = product.product_url;
            } else if (product.productUrl && !product.product_url) {
                product.product_url = product.productUrl;
            }

            // 🎯 ultrathink 彻底重写：直接构建additional_data对象，确保完整性
            product.additional_data = {
                good_reviews: product.good_reviews !== undefined ? product.good_reviews : '',
                cart_count: product.cart_count !== undefined ? product.cart_count : '',
                recent_sales: product.recent_sales !== undefined ? product.recent_sales : '',
                store_followers: product.store_followers !== undefined ? product.store_followers : ''
            };


            // 兼容性支持：保持双重命名，但以additional_data为准
            const additionalDataMapping = {
                'good_reviews': 'goodReviews',
                'cart_count': 'cartCount',
                'recent_sales': 'recentSales',
                'store_followers': 'storeFollowers'
            };

            Object.entries(additionalDataMapping).forEach(([underscoreName, camelCaseName]) => {
                // 从additional_data中获取正确值，确保一致性
                const correctValue = product.additional_data[underscoreName];
                product[underscoreName] = correctValue;
                product[camelCaseName] = correctValue;
            });

            // 智能生成商品名称
            if (!product.productName && !product.product_name) {
                product.productName = this.generateProductName(product, index);
                product.product_name = product.productName;
            } else if (product.product_name && !product.productName) {
                product.productName = product.product_name;
            } else if (product.productName && !product.product_name) {
                product.product_name = product.productName;
            }

            // 添加Excel来源标识
            product.isFromExcel = true;
            product.excelRowIndex = index + 2;

            return product;
        }).filter(Boolean);

        // 🚨 ultrathink 调试信息：记录解析结果
        console.log('📊 Excel解析结果:', {
            totalRows: dataRows.length,
            validProducts: products.length,
            invalidRows: dataRows.length - products.length,
            headers: headers,
            sampleProduct: products[0] || null
        });

        // 🎯 ultrathink 专项调试：检查第一个商品的additional_data字段
        if (products.length > 0) {
            const firstProduct = products[0];
            console.log('🎯 [ULTRATHINK专项调试] 第一个商品的additional_data相关字段:', {
                good_reviews: firstProduct.good_reviews,
                goodReviews: firstProduct.goodReviews,
                cart_count: firstProduct.cart_count,
                cartCount: firstProduct.cartCount,
                recent_sales: firstProduct.recent_sales,
                recentSales: firstProduct.recentSales,
                store_followers: firstProduct.store_followers,
                storeFollowers: firstProduct.storeFollowers,
                所有字段: Object.keys(firstProduct)
            });
        }

        if (products.length === 0) {
            console.error('❌ 没有有效的商品数据！可能的原因:');
            console.error('   1. 缺少必需的"商品链接"列');
            console.error('   2. 所有行的商品链接都为空');
            console.error('   3. 商品链接格式不正确');
            console.error('   4. 字段映射问题');
        }

        // ✅ 已移除销量过滤：保存所有商品（包括销量为0的商品）
        console.log('✅ 跳过销量过滤，保存所有商品，总商品数:', products.length);

        return {
            success: true,
            totalRows: dataRows.length,
            validProducts: products.length,
            products: products,
            headers: headers,
            // 无过滤统计信息
            filterStats: null,
            filteredCount: 0,
            originalProductsCount: products.length
        };
    }

    formatCellValue(fieldName, value) {
        if (typeof value === 'string') {
            value = value.trim();
            // 移除新增销量和新增销售额前面的"+"号
            if ((fieldName === '新增销量' || fieldName === '新增销售额') && value.startsWith('+')) {
                value = value.substring(1).trim();
            }
        }

        // 数字字段处理（包括新增销量和新增销售额）- ultrathink修复：移除additional_data字段，保持原始文本
        if (['productSales', 'storeSales', 'productPrice', '新增销量', '新增销售额'].includes(fieldName)) {
            return this.parseNumericValue(value);
        }

        // 日期字段处理
        if (fieldName === 'extractedAt') {
            return this.parseDate(value);
        }

        return value;
    }


    parseNumericValue(value) {
        if (typeof value === 'number') return value;
        if (!value) return 0;

        // 移除逗号、"+"号等符号，只保留数字和单位
        const strValue = String(value).replace(/[,，\+]/g, '');
        const match = strValue.match(/([\d.]+)\s*([万千kK])?/);

        if (!match) return 0;

        let number = parseFloat(match[1]);
        const unit = match[2];

        if (unit) {
            switch (unit.toLowerCase()) {
                case '万':
                    number *= 10000;
                    break;
                case '千':
                case 'k':
                    number *= 1000;
                    break;
            }
        }

        return Math.floor(number);
    }

    parseDate(value) {
        if (!value) return new Date();
        if (value instanceof Date) return value;
        
        try {
            return new Date(value);
        } catch {
            return new Date();
        }
    }

    /**
     * 智能生成商品名称
     * @param {Object} product 商品数据对象
     * @param {number} rowIndex 行索引
     * @returns {string} 生成的商品名称
     */
    generateProductName(product, rowIndex) {
        console.log('🤖 为商品生成名称:', { product, rowIndex });

        // 方案1: 尝试从店铺名称和其他信息组合生成 - 🚨 ultrathink 修复：兼容两种字段命名
        const storeName = product.storeName || product.store_name;
        if (storeName) {
            let name = storeName;
            const productPrice = product.productPrice || product.product_price;
            const productSales = product.productSales || product.product_sales;

            if (productPrice) {
                name += ` 商品(¥${productPrice})`;
            }
            if (productSales) {
                name += ` 销量${productSales}`;
            }
            console.log('✅ 使用店铺信息生成名称:', name);
            return name.substring(0, 100); // 限制长度
        }

        // 方案2: 尝试从URL提取商品ID或关键信息 - 🚨 ultrathink 修复：兼容两种字段命名
        const productUrl = product.productUrl || product.product_url;
        if (productUrl) {
            try {
                const url = new URL(productUrl);
                const pathParts = url.pathname.split('/').filter(part => part.length > 0);
                
                // 查找可能的商品ID
                for (let part of pathParts) {
                    if (/^[a-fA-F0-9]{24}$/.test(part) || // MongoDB ObjectId格式
                        /^\d{10,}$/.test(part) || // 长数字ID
                        /^[a-zA-Z0-9]{8,}$/.test(part)) { // 字母数字组合ID
                        const name = `商品_${part.substring(0, 12)}`;
                        console.log('✅ 从URL提取生成名称:', name);
                        return name;
                    }
                }

                // 提取域名作为标识
                const hostname = url.hostname.replace(/^www\./, '');
                const name = `${hostname}商品_${rowIndex + 1}`;
                console.log('✅ 使用域名生成名称:', name);
                return name;
            } catch (error) {
                console.warn('URL解析失败:', error);
            }
        }

        // 方案3: 根据其他可用信息生成
        let nameComponents = [];
        
        if (product.productPrice) {
            nameComponents.push(`价格¥${product.productPrice}`);
        }
        
        if (product.productSales) {
            nameComponents.push(`销量${product.productSales}`);
        }
        
        if (nameComponents.length > 0) {
            const name = `商品(${nameComponents.join(', ')})`;
            console.log('✅ 使用价格销量信息生成名称:', name);
            return name;
        }

        // 方案4: 最后的备用方案
        const name = `Excel导入商品_第${rowIndex + 2}行`;
        console.log('✅ 使用默认方案生成名称:', name);
        return name;
    }
}

/**
 * 主业务逻辑类 - 完全重构，移除Feishu依赖
 */
class XiaohongshuSidePanel {
    constructor() {
        this.isExtracting = false;
        this.currentData = null;
        this.history = [];
        
        // ✅ 新架构：本地数据管理组件
        this.localDataManager = null;
        this.categoryManager = null;
        this.dataMigrator = null;
        this.currentCategoryId = 1; // 默认"未分类"
        
        // 保留的组件
        this.excelProcessor = new ExcelProcessor();
        this.inputModeManager = null;
        
        // 批量监控相关
        this.isBatchMode = false;
        this.productList = [];
        this.selectedProducts = [];
        this.isBatchMonitoring = false;
        this.currentBatchIndex = 0;
        this.batchResults = [];
        this.batchPaused = false;

        // 状态管理
        this.isUploading = false;

        // 使用说明
        this.guideContentInitialized = false;
        this.guideOverlay = null;
        this.guideContentEl = null;
        this.guideEventsBound = false;
        
        // 批量监控服务
        this.batchMonitorService = null;
        
        this.init();
    }

    /**
     * 初始化应用
     */
    async init() {
        try {
            console.log('🔧 初始化流量蜂小红书数据监控助手 v2.0...');
            
            // 初始化本地数据组件
            await this.initializeLocalComponents();
            
            // 检查数据迁移需求
            await this.checkAndRunMigration();
            
            // 初始化UI组件
            this.initializeUI();
            
            // 加载分类数据
            await this.loadCategories();
            
            // 加载历史数据
            await this.loadHistory();

            // 加载分类复选框（延迟到切换批量监控模式时加载）
            // await this.loadCategoryCheckboxes();  // ✅ 优化：改为按需加载，避免在隐藏状态下加载导致显示问题

            // 加载异常统计
            await this.loadAnomalyStats();
            
            // 初始化监控预览状态
            await this.updateMonitorPreview();
            
            // 初始化5并发架构
            await this.initializeConcurrentArchitecture();
            
            console.log('✅ 应用初始化完成');
            // this.updateStatus('ready', '准备提取数据'); // 已删除status section
            
        } catch (error) {
            console.error('❌ 应用初始化失败:', error);
            // this.updateStatus('error', '初始化失败: ' + error.message); // 已删除status section
            console.error('❌ 应用初始化失败:', error.message);
        }
    }

    /**
     * 初始化本地数据组件
     */
    async initializeLocalComponents() {
        console.log('🔧 初始化本地数据组件...');
        
        try {
            // 等待必要的类加载完成
            await this.waitForRequiredComponents();
            
            // 使用统一数据服务管理器 - 解决双实例问题
            console.log('🔧 初始化统一数据服务...');
            this.sharedDataService = SharedDataService.getInstance();
            await this.sharedDataService.init();
            
            // 获取数据服务组件引用
            this.localDataManager = this.sharedDataService.getLocalDataManager();
            this.categoryManager = this.sharedDataService.getCategoryManager();
            this.dataMigrator = this.sharedDataService.getDataMigrator();
            // 改用简化的异常检测管理器
            this.easyAnomalyManager = new EasyAnomalyManager();
            this.categorySelectorManager = this.sharedDataService.getCategorySelectorManager();

            console.log('✅ 统一数据服务初始化完成');
            
            // 初始化ComponentBridge通信
            this.initializeComponentBridge();
            
        } catch (error) {
            console.error('❌ 本地数据组件初始化失败:', error);
            throw error;
        }
    }

    /**
     * 等待必要的组件类加载完成
     */
    async waitForRequiredComponents() {
        console.log('⏳ 等待必要的组件类加载...');
        
        const requiredComponents = ['LocalDataManager', 'CategoryManager', 'DataMigrator', 'EasyAnomalyManager'];
        
        for (const componentName of requiredComponents) {
            await this.waitForComponent(componentName);
        }
        
        console.log('✅ 所有必要的组件类已加载完成');
    }
    
    /**
     * 等待单个组件加载完成
     */
    async waitForComponent(componentName) {
        return new Promise((resolve) => {
            if (typeof window[componentName] !== 'undefined') {
                console.log(`✅ ${componentName} 已加载`);
                resolve();
                return;
            }
            
            let attempts = 0;
            const maxAttempts = 100; // 10秒超时
            const checkInterval = setInterval(() => {
                attempts++;
                if (typeof window[componentName] !== 'undefined') {
                    clearInterval(checkInterval);
                    console.log(`✅ ${componentName} 加载完成`);
                    resolve();
                } else if (attempts >= maxAttempts) {
                    clearInterval(checkInterval);
                    console.error(`❌ ${componentName} 加载超时`);
                    resolve(); // 即使超时也继续，避免卡死
                }
            }, 100);
        });
    }

    /**
     * 检查并运行数据迁移
     */
    async checkAndRunMigration() {
        try {
            console.log('🔍 检查数据迁移需求...');
            
            const migrationCheck = await this.dataMigrator.checkMigrationNeeded();
            
            if (migrationCheck.needed) {
                console.log('🔄 发现需要迁移的数据:', migrationCheck.reason);
                
                // 显示迁移提示
                this.updateStatus('info', `正在迁移历史数据 (${migrationCheck.dataCount} 条)...`);
                
                // 执行迁移
                const migrationResult = await this.dataMigrator.runMigration();
                
                if (migrationResult.success) {
                    console.log('✅ 数据迁移完成:', migrationResult.statistics);
                    this.showNotification('数据迁移完成', 'success');
                } else {
                    console.warn('⚠️ 数据迁移部分失败:', migrationResult.message);
                    this.showNotification('数据迁移完成，但存在部分问题', 'warning');
                }
                
            } else {
                console.log('ℹ️ 无需数据迁移:', migrationCheck.reason);
            }
            
        } catch (error) {
            console.error('❌ 数据迁移检查失败:', error);
            this.showNotification('数据迁移检查失败: ' + error.message, 'error');
        }
    }

    /**
     * 初始化UI组件和事件监听
     */
    initializeUI() {
        console.log('🔧 初始化UI组件...');
        
        try {
            // 初始化输入模式管理器
            this.inputModeManager = new InputModeManager();
            
            // 绑定事件监听器
            this.bindEventListeners();
            
            // 初始化模式切换
            this.initializeModeSwitch();
            
            // 初始化分类选择器
            this.initializeCategorySelector();
            
            console.log('✅ UI组件初始化完成');

            // 初始化简化的异常检测管理器
            setTimeout(() => {
                this.initEasyAnomalyManager().catch(error => {
                    console.error('🔴 初始化异常检测管理器失败:', error);
                });
            }, 500);

        } catch (error) {
            console.error('❌ UI组件初始化失败:', error);
        }
    }

    /**
     * 绑定事件监听器
     */
    bindEventListeners() {
        // 提取按钮事件
        const extractBtn = document.getElementById('extractBtn');
        extractBtn?.addEventListener('click', () => this.handleExtraction());

        // Excel导入相关事件
        this.bindExcelUploadEvents();

        // 数据管理按钮
        const openDataManagerBtn = document.getElementById('openDataManagerBtn');
        openDataManagerBtn?.addEventListener('click', () => this.openDataManager());

        // 分类管理按钮
        const manageCategoriesBtn = document.getElementById('manageCategoriesBtn');
        manageCategoriesBtn?.addEventListener('click', () => this.openCategoryManager());

        // 数据工具按钮
        const clearAllDataBtn = document.getElementById('clearAllDataBtn');
        clearAllDataBtn?.addEventListener('click', () => this.handleClearAllData());

        const exportDataBtn = document.getElementById('exportDataBtn');
        exportDataBtn?.addEventListener('click', () => this.handleExportAllData());

        // 使用说明按钮
        const guideOverlay = document.getElementById('userGuideOverlay');
        const guideContent = document.getElementById('guideContent');
        const openGuideBtn = document.getElementById('openGuideBtn');
        const closeGuideBtn = document.getElementById('closeGuideBtn');

        if (guideOverlay) {
            this.guideOverlay = guideOverlay;
        }
        if (guideContent) {
            this.guideContentEl = guideContent;
        }

        openGuideBtn?.addEventListener('click', () => this.openUserGuide());

        if (guideOverlay && closeGuideBtn && guideContent) {
            closeGuideBtn.addEventListener('click', () => this.closeUserGuide());

            guideOverlay.addEventListener('click', (event) => {
                if (event.target === guideOverlay) {
                    this.closeUserGuide();
                }
            });

            document.addEventListener('keydown', (event) => {
                if (event.key === 'Escape') {
                    this.closeUserGuide();
                }
            });

            this.guideEventsBound = true;
        }

        // 高级批量监控事件
        this.bindAdvancedBatchMonitoringEvents();
        
        // 异常检测控制面板事件
        this.bindAnomalyDetectionEvents();

        // 直接异常检测备用绑定
        // this.setupDirectAnomalyDetectionFallback();  // ⚠️ 临时注释：该方法在类外部定义，导致初始化失败

        console.log('✅ 事件监听器绑定完成');
    }

    /**
     * 初始化模式切换
     */
    initializeModeSwitch() {
        const modeRadios = document.querySelectorAll('input[name="monitorMode"]');
        console.log(`🔧 初始化模式切换器，找到 ${modeRadios.length} 个单选按钮`);
        modeRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                console.log(`📻 模式切换事件触发: ${e.target.value}`);
                this.isBatchMode = e.target.value === 'batch';
                console.log(`✅ isBatchMode 设置为: ${this.isBatchMode}`);
                this.toggleModeDisplay();
            });
        });
    }

    /**
     * 初始化分类选择器
     */
    initializeCategorySelector() {
        const categorySelect = document.getElementById('categorySelect');
        if (categorySelect) {
            categorySelect.addEventListener('change', (e) => {
                this.currentCategoryId = parseInt(e.target.value) || 1;
                console.log('✅ 当前分类切换到:', this.currentCategoryId);
            });
        } else {
            console.warn('⚠️ 分类选择器元素未找到');
        }

        // ✅ 新增: 手动输入分类选择器事件监听
        const manualCategorySelect = document.getElementById('manualCategorySelect');
        if (manualCategorySelect) {
            manualCategorySelect.addEventListener('change', (e) => {
                this.manualCategoryId = parseInt(e.target.value) || 1;
                console.log('✅ 手动输入分类切换到:', this.manualCategoryId);
            });

            // 初始化为未分类
            this.manualCategoryId = 1;
            console.log('✅ 手动输入分类选择器事件已绑定');
        } else {
            console.warn('⚠️ 手动输入分类选择器元素未找到');
        }
    }

    /**
     * 加载分类数据到选择器
     */
    async loadCategories() {
        try {
            console.log('🔄 加载分类数据...');
            
            const categories = await this.categoryManager.getAllCategories();
            
            // 填充主分类选择器
            const categorySelect = document.getElementById('categorySelect');
            if (categorySelect && categories) {
                categorySelect.innerHTML = '';
                
                categories.forEach(category => {
                    const option = document.createElement('option');
                    option.value = category.id;
                    option.textContent = `${category.name} (${category.product_count || 0})`;
                    if (category.id === 1) option.selected = true;
                    categorySelect.appendChild(option);
                });
            }
            
            // 填充Excel导入区域的分类选择器
            const uploadCategorySelect = document.getElementById('uploadCategorySelect');
            if (uploadCategorySelect && categories) {
                // 保留"请选择分类..."选项
                const currentValue = uploadCategorySelect.value;
                uploadCategorySelect.innerHTML = '<option value="">请选择分类...</option>';
                
                categories.forEach(category => {
                    const option = document.createElement('option');
                    option.value = category.id;
                    option.textContent = `${category.name} (${category.product_count || 0})`;
                    uploadCategorySelect.appendChild(option);
                });
                
                // 恢复之前选择的值（如果有）
                if (currentValue && currentValue !== '') {
                    uploadCategorySelect.value = currentValue;
                }
                
                // 更新上传按钮状态
                this.updateUploadButtonState();
            }

            // ✅ 新增: 填充手动输入的分类选择器
            const manualCategorySelect = document.getElementById('manualCategorySelect');
            if (manualCategorySelect && categories) {
                // 保留"请选择分类..."选项
                manualCategorySelect.innerHTML = '<option value="">请选择分类...</option>';

                categories.forEach(category => {
                    const option = document.createElement('option');
                    option.value = category.id;
                    option.textContent = `${category.name} (${category.product_count || 0})`;

                    // 默认选中"未分类"
                    if (category.id === 1) {
                        option.selected = true;
                    }

                    manualCategorySelect.appendChild(option);
                });

                console.log('✅ 手动输入分类选择器已加载');
            }

            console.log(`✅ 已加载 ${categories.length} 个分类到所有选择器`);
        
            
            // 更新统计信息
            await this.updateStatistics();
            
        } catch (error) {
            console.error('❌ 加载分类失败:', error);
        }
    }

    /**
     * 更新统计信息 - 与data-manager保持一致
     */
    async updateStatistics() {
        try {
            console.log('🔄 [Sidepanel] 开始更新统计信息...');
            
            // ✅ 使用优化后的统计方法
            const statistics = await this.localDataManager.getStatistics();
            
            // 更新侧边栏统计显示
            const totalCountElement = document.getElementById('totalProductCount');
            const categoryCountElement = document.getElementById('activeCategoryCount');
            
            if (totalCountElement) {
                totalCountElement.textContent = statistics.totalProducts;
                totalCountElement.title = `总计 ${statistics.totalProducts} 件商品`;
            }
            
            if (categoryCountElement) {
                categoryCountElement.textContent = statistics.categoriesWithData;
                categoryCountElement.title = `${statistics.categoriesWithData}/${statistics.totalCategories} 个分类有商品数据`;
            }
            
            console.log('✅ [Sidepanel] 统计信息更新完成:', {
                总商品数: statistics.totalProducts,
                总分类数: statistics.totalCategories,
                有数据分类数: statistics.categoriesWithData,
                分类详情: statistics.categories?.map(c => `${c.name}: ${c.product_count}`)
            });
            
            return statistics;
            
        } catch (error) {
            console.error('❌ [Sidepanel] 统计信息更新失败:', error);
            
            // 显示错误状态
            const totalCountElement = document.getElementById('totalProductCount');
            const categoryCountElement = document.getElementById('activeCategoryCount');
            
            if (totalCountElement) {
                totalCountElement.textContent = '错误';
                totalCountElement.title = '数据加载失败: ' + error.message;
            }
            
            if (categoryCountElement) {
                categoryCountElement.textContent = '错误';
                categoryCountElement.title = '数据加载失败: ' + error.message;
            }
            
            throw error;
        }
    }

    /**
     * 加载历史记录
     */
    async loadHistory() {
        try {
            console.log('🔄 加载历史记录...');
            
            const result = await this.localDataManager.getProducts(
                null, // 获取所有分类
                { sortBy: 'extracted_at_desc' },
                { page: 1, limit: 10 }
            );
            
            this.history = result.products || [];
            
            console.log(`✅ 已加载 ${this.history.length} 条历史记录`);
            
        } catch (error) {
            console.error('❌ 加载历史记录失败:', error);
        }
    }


    /**
     * 处理数据提取
     */
    async handleExtraction() {
        if (this.isExtracting) {
            console.warn('⚠️ 提取正在进行中，请等待完成');
            return;
        }

        try {
            const urls = this.inputModeManager.getCurrentUrls();
            
            if (urls.length === 0) {
                this.showNotification('请输入商品链接', 'warning');
                return;
            }

            if (urls.length === 1) {
                await this.extractSingleProduct(urls[0]);
            } else {
                await this.extractBatchProducts(urls);
            }

        } catch (error) {
            console.warn('⚠️ 数据提取处理失败:', error);  // ✅ 改为warn避免Edge Copilot弹窗
            this.showNotification('提取失败: ' + error.message, 'error');
        }
    }

    /**
     * 提取单个商品数据
     */
    async extractSingleProduct(url) {
        this.isExtracting = true;
        this.updateStatus('extracting', '正在提取商品数据...');

        try {
            // 发送消息给content script进行数据提取
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

            // 🔹 修复：检查当前页面URL是否与目标URL匹配（忽略查询参数）
            const currentUrlMatch = this.isXiaohongshuUrl(tab.url) && this.isSameProductUrl(tab.url, url);

            if (!this.isXiaohongshuUrl(tab.url) || !currentUrlMatch) {
                // 如果当前页面不是小红书，或者URL不匹配，需要打开新页面或导航到新URL
                console.log(`🔄 需要导航到新URL: ${url}`);

                // 加强标签页创建错误处理
                let newTab;
                try {
                    newTab = await chrome.tabs.create({ url: url, active: true });
                    if (!newTab || !newTab.id) {
                        throw new Error('标签页创建失败 - 无效的标签页对象');
                    }
                } catch (error) {
                    console.warn('⚠️ 标签页创建失败:', error);  // ✅ 改为warn避免Edge Copilot弹窗
                    throw new Error('标签页创建失败，可能达到Chrome数量限制');
                }

                // 等待页面加载完成
                await this.waitForTabLoad(newTab.id);

                // 在新页面提取数据 - 使用安全消息发送
                const response = window.safeTabMessage ?
                    await window.safeTabMessage(newTab.id, { action: 'extractData' }, { timeout: 15000, retries: 2 }) :
                    await chrome.tabs.sendMessage(newTab.id, { action: 'extractData' });

                if (response.success) {
                    await this.handleExtractionSuccess(response.data, url);
                } else {
                    throw new Error(response.error || '数据提取失败');
                }

                // 关闭新页面（可选）
                // await chrome.tabs.remove(newTab.id);

            } else {
                // 当前页面就是小红书且URL匹配，直接提取
                console.log(`✅ 当前页面URL匹配，直接提取: ${url}`);
                try {
                    // 先尝试发送消息
                    const response = window.safeTabMessage ?
                        await window.safeTabMessage(tab.id, { action: 'extractData' }, { timeout: 15000, retries: 2 }) :
                        await chrome.tabs.sendMessage(tab.id, { action: 'extractData' });

                    if (response.success) {
                        await this.handleExtractionSuccess(response.data, url);
                    } else {
                        throw new Error(response.error || '数据提取失败');
                    }
                } catch (connectionError) {
                    // 如果连接失败，尝试手动注入 content script
                    console.warn('⚠️ Content script 连接失败，尝试手动注入...', connectionError);

                    try {
                        await chrome.scripting.executeScript({
                            target: { tabId: tab.id },
                            files: ['content.js']
                        });

                        console.log('✅ Content script 手动注入成功，等待2秒后重试...');
                        await this.delay(2000);

                        // 重新尝试提取
                        const retryResponse = await chrome.tabs.sendMessage(tab.id, { action: 'extractData' });

                        if (retryResponse.success) {
                            await this.handleExtractionSuccess(retryResponse.data, url);
                        } else {
                            throw new Error(retryResponse.error || '数据提取失败');
                        }
                    } catch (injectError) {
                        console.warn('⚠️ Content script 注入失败:', injectError);  // ✅ 改为warn避免Edge Copilot弹窗
                        throw new Error('请刷新页面后重试，或在其他页面打开侧边栏');
                    }
                }
            }

        } catch (error) {
            console.warn('⚠️ 单商品提取失败:', error);  // ✅ 改为warn避免Edge Copilot弹窗
            this.updateStatus('error', '提取失败: ' + error.message);
            this.showNotification('提取失败: ' + error.message, 'error');
        } finally {
            this.isExtracting = false;
        }
    }

    /**
     * 处理提取成功的数据
     * @param {Object} data - 提取的商品数据
     * @param {string} url - 商品URL
     * @param {Object} options - 可选配置
     * @param {boolean} options.skipNotification - 是否跳过状态同步通知（批量提取时使用）
     */
    async handleExtractionSuccess(data, url, options = {}) {
        try {
            console.log('✅ 数据提取成功:', data);

            // 🔹 数据字段映射（适配Content Script新字段）
            const productData = {
                product_id: data.productId,                      // 🆕 商品ID
                product_name: data.productName,                  // 🆕 商品名称
                product_url: data.url || url,
                product_price: data.productPrice,                // 🆕 商品价格
                product_sales: data.productSales,
                store_sales: data.storeSales,
                store_name: data.storeName,                      // 🆕 店铺名称
                extracted_at: data.timestamp || new Date().toISOString(),

                // 🆕 附加数据
                additional_data: {
                    good_reviews: data.goodReviews || '',
                    cart_count: data.cartCount || '',
                    recent_sales: data.recentSales || '',
                    store_followers: data.storeFollowers || ''   // 🆕 粉丝数
                }
            };

            // 显示提取结果（保持不变）
            this.displayExtractionResults(productData);

            // ✅ 修改: 使用选中的分类ID保存
            const targetCategoryId = this.manualCategoryId || 1;  // 默认未分类

            const savedProduct = await this.localDataManager.saveProduct(
                productData,
                targetCategoryId  // ✅ 使用选中的分类
            );

            console.log(`✅ 商品已保存到分类 ${targetCategoryId}:`, savedProduct);

            // ✅ 批量提取时不显示单个商品保存通知
            if (!options.skipNotification) {
                this.showNotification('商品已保存到选中分类', 'success');
            }

            // ✅ 批量提取时跳过历史记录和统计更新，最后统一更新
            if (!options.skipNotification) {
                await this.loadHistory();
                await this.updateStatistics();
            }

            // ✅ 批量提取时跳过状态同步通知，最后统一发送
            if (this.componentBridge && !options.skipNotification) {
                this.componentBridge.notifyProductDataUpdated([targetCategoryId], 'single_extract');
                console.log('📡 已发送商品提取状态同步通知');
            }

            if (!options.skipNotification) {
                this.updateStatus('success', '数据提取并保存成功');
            }

        } catch (error) {
            console.warn('⚠️ 数据处理失败:', error);  // ✅ 改为warn避免Edge Copilot弹窗
            this.updateStatus('error', '数据保存失败: ' + error.message);
            this.showNotification('数据保存失败: ' + error.message, 'error');
            throw error;
        }
    }

    /**
     * 显示提取结果
     */
    displayExtractionResults(data) {
        this.currentData = data;
        
        // Results section 已删除，仅记录数据
        console.log('📊 提取结果:', {
            productSales: data.productSales || '-',
            storeSales: data.storeSales || '-', 
            extractTime: new Date().toLocaleString()
        });
    }

    /**
     * 批量提取商品数据 - 使用标签页池优化版
     */
    async extractBatchProducts(urls) {
        console.log('🔄 开始批量提取数据，共', urls.length, '个链接');

        // 验证分类选择
        const targetCategoryId = this.manualCategoryId || 1;
        if (!targetCategoryId) {
            this.showNotification('请先选择保存分类', 'warning');
            return;
        }

        this.isBatchMonitoring = true;
        this.batchResults = [];

        // 显示进度条
        this.showManualProgress(urls.length);

        try {
            // ✅ 确保标签页池已初始化
            await this.ensureTabPoolManager();
            console.log('✅ 标签页池已初始化，准备处理');

            const CONCURRENT = 5;  // 固定5并发

            // 分批处理
            for (let i = 0; i < urls.length; i += CONCURRENT) {
                if (!this.isBatchMonitoring) break;

                const batch = urls.slice(i, i + CONCURRENT);
                console.log(`处理批次 ${Math.floor(i/CONCURRENT)+1}: ${batch.length} 个链接`);

                // ✅ 并发处理这一批
                const batchPromises = batch.map(async (url, index) => {
                    let tabId = null;
                    let hasError = false;  // ✅ 修复: 在外部作用域定义错误标志
                    try {
                        // 从标签页池获取
                        tabId = await this.tabPoolManager.acquireTab();
                        console.log(`🏊 获取标签页 ${tabId} 处理: ${url}`);

                        // 导航到商品页
                        await new Promise((resolve, reject) => {
                            chrome.tabs.update(tabId, { url: url }, (updatedTab) => {
                                if (chrome.runtime.lastError) {
                                    reject(new Error('导航失败: ' + chrome.runtime.lastError.message));
                                } else {
                                    resolve();
                                }
                            });
                        });

                        // 等待页面加载
                        await this.waitForTabLoad(tabId);

                        // 提取数据
                        const response = await chrome.tabs.sendMessage(tabId, {
                            action: 'extractData'
                        });

                        if (response.success) {
                            // ✅ 批量提取时跳过通知，最后统一发送
                            await this.handleExtractionSuccess(response.data, url, { skipNotification: true });
                            return { url, success: true, index: i + index };
                        } else {
                            throw new Error(response.error || '数据提取失败');
                        }

                    } catch (error) {
                        hasError = true;  // ✅ 修复: 标记发生了错误
                        console.warn(`⚠️ 第${i + index + 1}个商品提取失败:`, error);  // ✅ 改为warn避免Edge Copilot弹窗
                        return { url, success: false, error: error.message, index: i + index };

                    } finally {
                        // ✅ 释放标签页回池（不关闭）
                        if (tabId && this.tabPoolManager) {
                            this.tabPoolManager.releaseTab(tabId, {
                                success: !hasError,  // ✅ 修复: 使用外部作用域的错误标志
                                url: url
                            });
                            console.log(`🔄 标签页 ${tabId} 已释放回池`);
                        }
                    }
                });

                // 等待这一批完成
                const batchResults = await Promise.all(batchPromises);
                this.batchResults.push(...batchResults);

                // 更新进度
                this.updateManualProgress(this.batchResults.length, urls.length);
            }

            // 完成统计
            const successCount = this.batchResults.filter(r => r.success).length;
            const failedCount = this.batchResults.length - successCount;

            this.hideManualProgress();
            this.showNotification(
                `批量提取完成: ${successCount} 成功, ${failedCount} 失败`,
                'success'
            );

            // ✅ 清理标签页池（关闭所有标签页）
            if (this.tabPoolManager) {
                await this.tabPoolManager.emergencyStop();
                console.log('✅ 标签页池已清理');
            }

            // ✅ 批量提取完成后，统一更新历史记录和统计信息
            if (successCount > 0) {
                await this.loadHistory();
                await this.updateStatistics();
            }

            // ✅ 批量提取完成后，统一发送一次状态同步通知
            if (this.componentBridge && successCount > 0) {
                this.componentBridge.notifyProductDataUpdated([targetCategoryId], 'batch_extract');
                console.log('📡 已发送批量提取状态同步通知');
            }

        } catch (error) {
            console.warn('⚠️ 批量提取失败:', error);  // ✅ 改为warn避免Edge Copilot弹窗
            this.hideManualProgress();
            this.showNotification('批量提取失败: ' + error.message, 'error');
        } finally {
            this.isBatchMonitoring = false;
        }
    }

    /**
     * ✅ 新增: 显示进度条
     */
    showManualProgress(total) {
        const progressBar = document.getElementById('manualProgressBar');
        if (progressBar) {
            progressBar.style.display = 'block';
        }
        this.updateManualProgress(0, total);
    }

    /**
     * ✅ 新增: 更新进度
     */
    updateManualProgress(completed, total) {
        const progressFill = document.getElementById('manualProgressFill');
        const progressText = document.getElementById('manualProgressText');

        const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;

        if (progressFill) {
            progressFill.style.width = percentage + '%';
        }

        if (progressText) {
            progressText.textContent = `${completed}/${total} (${percentage}%)`;
        }
    }

    /**
     * ✅ 新增: 隐藏进度条
     */
    hideManualProgress() {
        const progressBar = document.getElementById('manualProgressBar');
        if (progressBar) {
            progressBar.style.display = 'none';
        }
    }

    /**
     * 绑定Excel导入相关事件
     */
    bindExcelUploadEvents() {
        const uploadCategorySelect = document.getElementById('uploadCategorySelect');
        const excelUpload = document.getElementById('excelUpload');
        const startUploadBtn = document.getElementById('startUploadBtn');
        
        // 监听分类选择变化
        uploadCategorySelect?.addEventListener('change', () => {
            this.updateUploadButtonState();
        });
        
        // 监听文件选择变化
        excelUpload?.addEventListener('change', () => {
            this.updateUploadButtonState();
        });
        
        // 开始导入按钮事件
        startUploadBtn?.addEventListener('click', () => {
            this.handleExcelUpload();
        });


        console.log('✅ Excel导入事件绑定完成');
    }


    /**
     * 更新上传按钮状态
     */
    updateUploadButtonState() {
        const uploadCategorySelect = document.getElementById('uploadCategorySelect');
        const excelUpload = document.getElementById('excelUpload');
        const startUploadBtn = document.getElementById('startUploadBtn');
        const selectedFileName = document.getElementById('selectedFileName');
        const fileNameText = document.getElementById('fileNameText');
        
        if (uploadCategorySelect && excelUpload && startUploadBtn) {
            const hasCategorySelected = uploadCategorySelect.value && uploadCategorySelect.value !== '';
            const hasFileSelected = excelUpload.files && excelUpload.files.length > 0;
            
            startUploadBtn.disabled = !(hasCategorySelected && hasFileSelected);
            
            // 显示或隐藏文件名
            if (hasFileSelected && selectedFileName && fileNameText) {
                const fileName = excelUpload.files[0].name;
                fileNameText.textContent = `已选择: ${fileName}`;
                selectedFileName.style.display = 'block';
            } else if (selectedFileName) {
                selectedFileName.style.display = 'none';
            }
            
            console.log('上传按钮状态更新:', {
                分类已选: hasCategorySelected,
                文件已选: hasFileSelected,
                按钮可用: !startUploadBtn.disabled,
                文件名: hasFileSelected ? excelUpload.files[0].name : '未选择'
            });
        }
    }

    /**
     * 处理Excel文件上传
     */
    async handleExcelUpload() {
        // 从UI元素获取文件和分类信息
        const excelUpload = document.getElementById('excelUpload');
        const uploadCategorySelect = document.getElementById('uploadCategorySelect');
        const uploadResults = document.getElementById('uploadResults');
        const uploadProgress = document.getElementById('uploadProgress');
        
        const file = excelUpload?.files?.[0];
        const selectedCategoryId = parseInt(uploadCategorySelect?.value);
        
        if (!file) {
            this.showNotification('请选择Excel文件', 'warning');
            return;
        }
        
        if (!selectedCategoryId) {
            this.showNotification('请选择导入分类', 'warning');
            return;
        }

        this.isUploading = true;
        this.updateStatus('uploading', '正在处理Excel文件...');
        
        // 显示进度条
        if (uploadProgress) {
            uploadProgress.style.display = 'block';
        }

        try {
            console.log('📊 开始Excel导入:', {
                文件名: file.name,
                选择分类: selectedCategoryId,
                分类名称: uploadCategorySelect.options[uploadCategorySelect.selectedIndex].text
            });
            
            // 解析Excel文件
            const parseResult = await this.excelProcessor.parseFile(file);
            console.log('✅ Excel解析完成:', parseResult);

            if (parseResult.validProducts === 0) {
                throw new Error('Excel文件中没有有效的商品数据');
            }

            // 批量保存到数据库（使用选择的分类ID，启用去重功能）
            const batchResult = await this.localDataManager.batchSaveProductsWithDedup(
                parseResult.products, 
                selectedCategoryId
            );

            console.log('✅ Excel数据保存完成:', batchResult);

            // 显示导入结果（包含过滤统计）
            this.showUploadResults(batchResult, uploadCategorySelect.options[uploadCategorySelect.selectedIndex].text, batchResult.filterStats);

            // 更新界面
            await this.loadHistory();
            await this.updateStatistics();

            // 🆕 新增：通知数据管理器状态同步
            if (this.componentBridge) {
                this.componentBridge.notifyExcelUploadCompleted(selectedCategoryId, batchResult);
                console.log('📡 已发送Excel上传完成状态同步通知');
            }

            const successMsg = `Excel导入完成: 总计${batchResult.success}条` +
                (batchResult.created ? `, 新建${batchResult.created}条` : '') +
                (batchResult.updated ? `, 更新${batchResult.updated}条` : '') +
                (batchResult.failed > 0 ? `, 失败${batchResult.failed}条` : '');
            this.updateStatus('success', successMsg);
            this.showNotification(successMsg, 'success');

        } catch (error) {
            console.error('❌ Excel处理失败:', error);
            this.updateStatus('error', 'Excel处理失败: ' + error.message);
            this.showNotification('Excel处理失败: ' + error.message, 'error');
            
            // 显示错误结果
            this.showUploadResults({ success: 0, failed: 1, error: error.message });
        } finally {
            this.isUploading = false;
            
            // 清空文件输入并重置按钮状态
            if (excelUpload) {
                excelUpload.value = '';
            }
            this.updateUploadButtonState();
            
            // 隐藏进度条
            if (uploadProgress) {
                uploadProgress.style.display = 'none';
            }
        }
    }

    /**
     * 显示Excel导入结果 - ✅ 已移除过滤统计显示
     */
    showUploadResults(result, categoryName = '', filterStats = null) {
        const uploadResults = document.getElementById('uploadResults');
        if (!uploadResults) return;

        const isError = result.error || (result.success === 0 && result.failed > 0);
        const statusClass = isError ? 'error' : 'success';
        const statusIcon = isError ? '❌' : '✅';

        // ✅ 已移除过滤统计信息显示（不再过滤零销量商品）
        let filterStatsHtml = '';

        uploadResults.innerHTML = `
            <div class="upload-result ${statusClass}" style="margin-top: 15px; padding: 15px; border-radius: 6px; border: 1px solid ${isError ? '#dc2626' : '#10b981'}; background: ${isError ? '#fef2f2' : '#f0fdf4'};">
                <div style="display: flex; align-items: center; gap: 8px; font-weight: 600; color: ${isError ? '#dc2626' : '#10b981'}; margin-bottom: 8px;">
                    <span>${statusIcon}</span>
                    <span>${isError ? '导入失败' : '导入成功'}</span>
                </div>
                <div style="color: #374151; font-size: 14px;">
                    ${result.error ?
                        `错误信息：${result.error}` :
                        `目标分类：${categoryName}<br>` +
                        `总计处理：${result.success} 条<br>` +
                        (result.created ? `新建商品：${result.created} 条<br>` : '') +
                        (result.updated ? `更新商品：${result.updated} 条（已存在商品ID）<br>` : '') +
                        (result.noId ? `无ID商品：${result.noId} 条<br>` : '') +
                        `失败：${result.failed} 条`
                    }
                </div>
                ${filterStatsHtml}
            </div>
        `;

        // 自动隐藏成功消息
        if (!isError) {
            setTimeout(() => {
                if (uploadResults.innerHTML.includes('导入成功')) {
                    uploadResults.innerHTML = '';
                }
            }, 3000);
        }
    }

    /**
     * 打开数据管理器
     */
    openDataManager() {
        // 打开独立的数据管理页面
        chrome.tabs.create({
            url: chrome.runtime.getURL('data-manager.html')
        });
    }

    /**
     * 打开分类管理器
     */
    async openCategoryManager() {
        try {
            // 这里可以实现一个简单的分类管理弹窗
            // 或者跳转到数据管理器的分类管理页面
            const categories = await this.categoryManager.getAllCategories();
            console.log('当前分类列表:', categories);
            
            // 简化版：显示一个prompt来创建新分类
            const newCategoryName = prompt('输入新分类名称：');
            if (newCategoryName && newCategoryName.trim()) {
                try {
                    const newCategory = await this.categoryManager.createCategory(newCategoryName.trim());
                    console.log('✅ 新分类创建成功:', newCategory);

                    // 重新加载分类列表
                    await this.loadCategories();

                    // 🆕 新增：通知数据管理器状态同步
                    if (this.componentBridge) {
                        this.componentBridge.notifyCategoryCreated(newCategory.id || newCategory, newCategoryName.trim());
                        console.log('📡 已发送分类创建状态同步通知');
                    }

                    this.showNotification(`分类"${newCategoryName}"创建成功`, 'success');
                    
                } catch (error) {
                    console.error('❌ 分类创建失败:', error);
                    this.showNotification('分类创建失败: ' + error.message, 'error');
                }
            }
            
        } catch (error) {
            console.error('❌ 打开分类管理失败:', error);
            this.showNotification('分类管理打开失败: ' + error.message, 'error');
        }
    }

    // ==================== 工具方法 ====================

    /**
     * 检查是否为小红书URL
     */
    isXiaohongshuUrl(url) {
        if (!url) return false;
        return /^https?:\/\/(www\.)?xiaohongshu\.com/i.test(url);
    }

    /**
     * 比较两个URL是否指向同一个商品（忽略查询参数）
     */
    isSameProductUrl(url1, url2) {
        if (!url1 || !url2) return false;

        try {
            // 提取商品ID的函数
            const extractProductId = (url) => {
                // 匹配 goods-detail/{productId} 格式
                const match = url.match(/goods-detail\/([a-f0-9]+)/i);
                return match ? match[1] : null;
            };

            const id1 = extractProductId(url1);
            const id2 = extractProductId(url2);

            // 如果两个URL都包含商品ID，比较ID是否相同
            if (id1 && id2) {
                return id1 === id2;
            }

            // 如果无法提取商品ID，比较pathname（忽略查询参数）
            const path1 = new URL(url1).pathname;
            const path2 = new URL(url2).pathname;
            return path1 === path2;
        } catch (error) {
            console.error('❌ URL比较失败:', error);
            return false;
        }
    }

    /**
     * 等待标签页加载完成
     */
    async waitForTabLoad(tabId) {
        return new Promise((resolve) => {
            const listener = (tabIdChanged, changeInfo) => {
                if (tabIdChanged === tabId && changeInfo.status === 'complete') {
                    chrome.tabs.onUpdated.removeListener(listener);
                    setTimeout(resolve, 1000); // 额外等待1秒确保页面完全加载
                }
            };
            chrome.tabs.onUpdated.addListener(listener);
        });
    }

    /**
     * 延迟函数
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * 更新状态显示
     */
    updateStatus(type, message) {
        // Status section 已删除，仅记录日志
        console.log(`📊 状态: ${type} - ${message}`);
    }

    /**
     * 显示通知
     */
    showNotification(message, type = 'info') {
        console.log(`🔔 通知: ${type} - ${message}`);
        
        // 可以在这里实现更复杂的通知UI
        // 目前简化为控制台日志
        
        // 如果有通知权限，可以使用Chrome通知API
        if (chrome.notifications) {
            chrome.notifications.create({
                type: 'basic',
                iconUrl: 'icons/icon48.png',
                title: '流量蜂小红书数据监控助手',
                message: message
            });
        }
    }

    /**
     * 切换显示模式
     */
    toggleModeDisplay() {
        const manualContent = document.getElementById('manualContent');
        const batchContent = document.getElementById('batchContent');
        
        console.log(`🔄 模式切换开始: ${this.isBatchMode ? '批量监控' : '手动输入'}`);
        
        if (this.isBatchMode) {
            // 隐藏手动模式
            if (manualContent) {
                manualContent.classList.add('hidden');
                manualContent.style.display = 'none';
            }
            
            // 显示批量模式 - 同时处理CSS类和内联样式
            if (batchContent) {
                batchContent.classList.remove('hidden');
                batchContent.style.display = 'block'; // ✅ 修复关键问题：移除内联隐藏样式
                
                console.log('✅ 批量内容已显示:', {
                    hasHiddenClass: batchContent.classList.contains('hidden'),
                    displayStyle: batchContent.style.display,
                    computedDisplay: window.getComputedStyle(batchContent).display
                });
            }

            // 🔧 确保组件完全初始化后再加载（添加延迟确保DOM更新完成）
            console.log('⏰ 准备在100ms后调用ensureBatchModeReady...');
            setTimeout(() => {
                console.log('⏰ 开始调用ensureBatchModeReady...');
                this.ensureBatchModeReady();
            }, 100);
            
        } else {
            // 显示手动模式
            if (manualContent) {
                manualContent.classList.remove('hidden');
                manualContent.style.display = 'block';
            }
            
            // 隐藏批量模式
            if (batchContent) {
                batchContent.classList.add('hidden');
                batchContent.style.display = 'none';
            }
        }
        
        console.log(`✅ 模式切换完成: ${this.isBatchMode ? '批量监控' : '手动输入'}`);
    }

    /**
     * 确保批量模式就绪 - 新增方法
     */
    async ensureBatchModeReady() {
        try {
            console.log('🔄 准备批量模式...');
            
            // 1. 等待DOM元素渲染完成
            await this.waitForElement('categorySelectorGrid', 3000);
            
            // 2. 验证关键组件已初始化
            if (!this.categoryManager || !this.localDataManager) {
                throw new Error('关键组件未初始化');
            }
            
            // 3. ✅ 修复：检查是否有实际的分类复选框项，而不是占位符
            const grid = document.getElementById('categorySelectorGrid');
            if (!grid) {
                throw new Error('categorySelectorGrid 元素未找到');
            }

            const categoryItems = grid.querySelectorAll('.category-checkbox-item');
            console.log(`🔍 检查分类复选框状态: 找到 ${categoryItems.length} 个分类项`);

            if (categoryItems.length > 0) {
                // 已有分类复选框，只需重新绑定事件
                console.log('🔧 为现有分类复选框绑定事件...', categoryItems.length, '个分类');
                this.bindExistingCategoryCheckboxes(grid);
            } else {
                // 没有分类复选框（可能只有占位符），需要加载
                console.log('📥 首次加载分类复选框...');
                const success = await this.loadCategoryCheckboxes();
                if (!success) {
                    throw new Error('分类复选框加载失败');
                }
            }
            
            // 5. 强制更新监控预览
            await this.updateMonitorPreview();
            
            console.log('✅ 批量模式就绪');
        } catch (error) {
            console.error('❌ 批量模式初始化失败:', error);
            this.showNotification('批量模式加载失败，请刷新重试', 'error');
            
            // 显示错误状态
            const grid = document.getElementById('categorySelectorGrid');
            if (grid) {
                grid.innerHTML = `
                    <div class="error-state">
                        <div class="error-text">❌ ${error.message}</div>
                        <button class="btn btn-secondary btn-sm" onclick="xiaohongShuMonitor.ensureBatchModeReady()">重试</button>
                    </div>
                `;
            }
        }
    }

    /**
     * 绑定现有分类复选框事件 - 新增修复方法
     */
    bindExistingCategoryCheckboxes(grid) {
        console.log('🔧 绑定现有分类复选框事件...');
        
        // 移除已有的事件监听器（避免重复绑定）
        grid.querySelectorAll('.category-checkbox-item').forEach(item => {
            // 克隆元素来移除所有事件监听器
            const newItem = item.cloneNode(true);
            item.parentNode.replaceChild(newItem, item);
        });
        
        // 重新获取元素并绑定事件
        const items = grid.querySelectorAll('.category-checkbox-item');
        const checkboxes = grid.querySelectorAll('.category-checkbox');
        
        console.log(`找到 ${items.length} 个分类项，${checkboxes.length} 个复选框`);
        
        // 绑定分类项点击事件
        items.forEach(item => {
            item.addEventListener('click', (e) => {
                if (e.target.type !== 'checkbox') {
                    const checkbox = item.querySelector('.category-checkbox');
                    if (checkbox) {
                        checkbox.checked = !checkbox.checked;
                        checkbox.dispatchEvent(new Event('change'));
                    }
                }
            });
        });
        
        // 绑定复选框变化事件
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const item = checkbox.closest('.category-checkbox-item');
                if (item) {
                    item.classList.toggle('selected', checkbox.checked);
                }
                
                console.log(`分类选择变化: ${checkbox.value}, 选中: ${checkbox.checked}`);
                
                // 更新监控预览
                this.updateMonitorPreview();
            });
        });
        
        console.log('✅ 现有分类复选框事件绑定完成');
    }

    /**
     * 等待DOM元素 - 新增工具方法
     */
    waitForElement(elementId, timeout = 3000) {
        return new Promise((resolve, reject) => {
            const element = document.getElementById(elementId);
            if (element) {
                resolve(element);
                return;
            }
            
            const observer = new MutationObserver(() => {
                const element = document.getElementById(elementId);
                if (element) {
                    observer.disconnect();
                    resolve(element);
                }
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
            
            setTimeout(() => {
                observer.disconnect();
                reject(new Error(`元素 ${elementId} 加载超时`));
            }, timeout);
        });
    }







    
    /**
     * 启动新的批量监控服务
     */
    async startAdvancedBatchMonitoring(config) {
        try {
            // 使用按需初始化确保BatchMonitorService可用
            const batchService = await this.ensureBatchMonitorService();

            console.log('🚀 启动高级批量监控:', config);

            // 使用新的监控服务启动监控
            await batchService.startBatchMonitoring(config);

        } catch (error) {
            console.error('❌ 启动批量监控失败:', error);
            this.showNotification('启动批量监控失败: ' + error.message, 'error');
        }
    }
    
    /**
     * 暂停批量监控
     */
    pauseAdvancedBatchMonitoring() {
        if (this.batchMonitorService) {
            this.batchMonitorService.togglePause();
        } else {
            console.warn('⚠️ 批量监控服务未初始化，无法暂停');
        }
    }
    
    /**
     * 停止批量监控
     */
    stopAdvancedBatchMonitoring() {
        if (this.batchMonitorService) {
            this.batchMonitorService.stop();
        } else {
            console.warn('⚠️ 批量监控服务未初始化，无法停止');
        }
    }
    
    /**
     * 运行异常检测
     */
    async runAnomalyDetection() {
        try {
            // 使用按需初始化确保BatchMonitorService可用
            const batchService = await this.ensureBatchMonitorService();

            console.log('🔍 运行异常检测...');

            // 更新UI状态：运行中
            this.updateAnomalyDetectionStatus('running', '正在运行...');
            this.showNotification('开始运行异常检测...', 'info');

            const result = await batchService.runAnomalyDetection();
            
            if (result.success) {
                // 更新UI状态：成功
                this.updateAnomalyDetectionStatus('success', '检测完成', Date.now());
                this.showNotification(
                    `异常检测完成: 发现 ${result.anomaliesFound} 个异常`, 
                    'success'
                );
                
                // 更新异常统计
                this.updateAnomalyStats({
                    critical: result.criticalAnomalies,
                    warning: result.warningAnomalies,
                    info: result.infoAnomalies
                });
                
            } else {
                // 更新UI状态：失败
                this.updateAnomalyDetectionStatus('error', '检测失败');
                this.showNotification('异常检测失败: ' + result.error, 'error');
            }
            
        } catch (error) {
            console.error('❌ 运行异常检测失败:', error);
            this.updateAnomalyDetectionStatus('error', '检测失败');
            this.showNotification('异常检测失败: ' + error.message, 'error');
        }
    }
    
    /**
     * 初始化ComponentBridge通信
     */
    initializeComponentBridge() {
        if (window.getComponentBridge) {
            this.componentBridge = window.getComponentBridge();

            // 注册消息监听器 - 处理来自data-manager的请求
            this.componentBridge.onMessage('OPEN_BATCH_MONITOR_DIALOG', (data) => {
                this.handleOpenBatchMonitorRequest(data);
            });

            this.componentBridge.onMessage('RUN_ANOMALY_DETECTION', (data) => {
                this.handleAnomalyDetectionRequest(data);
            });

            // 🔔 监听分类更新消息 - 实现跨页面分类同步
            this.componentBridge.onMessage('CATEGORIES_UPDATED', (data) => {
                this.handleCategoriesUpdated(data);
            });

            console.log('✅ Sidepanel ComponentBridge 通信已建立');
        }
    }
    
    /**
     * 处理打开批量监控对话框请求
     */
    handleOpenBatchMonitorRequest(data) {
        console.log('📥 收到批量监控对话框打开请求:', data);
        
        // 这里可以添加打开批量监控UI的逻辑
        // 例如显示配置对话框或切换到批量模式
        this.showNotification('批量监控功能正在开发中...', 'info');
        
        // 示例：如果有分类配置，可以启动批量监控
        // const sampleConfig = {
        //     selectedCategories: [1, 2],
        //     interval: 60,
        //     concurrent: 3,
        //     autoRetry: true
        // };
        // this.startAdvancedBatchMonitoring(sampleConfig);
    }
    
    /**
     * 处理异常检测请求
     */
    async handleAnomalyDetectionRequest(data) {
        console.log('📥 收到异常检测请求:', data);

        try {
            // 调用异常检测方法
            await this.runAnomalyDetection();
        } catch (error) {
            console.error('❌ 处理异常检测请求失败:', error);
        }
    }

    /**
     * 🔔 处理分类更新消息 - 实现跨页面分类同步
     */
    async handleCategoriesUpdated(data) {
        console.log('📥 收到分类更新通知:', data);

        try {
            const { action, categoryId, categoryName } = data;

            // 重新加载分类列表,更新所有分类选择器
            await this.loadCategories();

            // 同时刷新批量监控的分类选择器
            if (this.categorySelectorManager) {
                await this.categorySelectorManager.refresh();
            }

            // 显示提示消息
            const actionText = action === 'create' ? '创建' : action === 'update' ? '更新' : '删除';
            console.log(`✅ 分类列表已同步更新 (${actionText}: ${categoryName || categoryId})`);

        } catch (error) {
            console.error('❌ 处理分类更新消息失败:', error);
        }
    }

    /**
     * 绑定高级批量监控事件
     */
    bindAdvancedBatchMonitoringEvents() {
        // 分类选择事件
        document.getElementById('selectAllCategories')?.addEventListener('click', () => {
            this.selectAllCategories();
        });
        
        document.getElementById('selectNoneCategories')?.addEventListener('click', () => {
            this.selectNoneCategories();
        });
        
        // 监控配置变化事件
        const configInputs = ['monitorInterval', 'concurrentLimit', 'autoRetry', 'enableAnomalyDetection'];
        configInputs.forEach(id => {
            document.getElementById(id)?.addEventListener('change', () => {
                this.updateMonitorPreview();
            });
        });
        
        // 启动高级批量监控 - 支持暂停/继续
        document.getElementById('startAdvancedBatchBtn')?.addEventListener('click', () => {
            this.handleBatchMonitoringAction();
        });
        
        // 停止批量监控
        document.getElementById('stopBatchBtn')?.addEventListener('click', () => {
            this.handleStopMonitoring();
        });
        
        console.log('✅ 高级批量监控事件绑定完成');
    }
    
    /**
     * 绑定异常检测控制面板事件
     */
    bindAnomalyDetectionEvents() {
        // EasyAnomalyManager 会自动绑定自己的事件，这里只需要处理旧的按钮兼容性
        // 运行异常检测按钮 - 如果还存在旧按钮，将其重定向到新的检测功能
        const oldRunBtn = document.getElementById('runAnomalyDetectionBtn');
        if (oldRunBtn) {
            oldRunBtn.addEventListener('click', () => {
                const newRunBtn = document.getElementById('easyRunDetection');
                if (newRunBtn) {
                    newRunBtn.click();
                } else {
                    console.log('请使用新的异常检测界面');
                }
            });
        }

        console.log('✅ 异常检测事件绑定完成');
    }
    
    /**
     * 全选分类
     */
    selectAllCategories() {
        const checkboxes = document.querySelectorAll('#categorySelectorGrid input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = true;
            checkbox.closest('.category-checkbox-item').classList.add('selected');
        });
        this.updateMonitorPreview();
    }
    
    /**
     * 全不选分类
     */
    selectNoneCategories() {
        const checkboxes = document.querySelectorAll('#categorySelectorGrid input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = false;
            checkbox.closest('.category-checkbox-item').classList.remove('selected');
        });
        this.updateMonitorPreview();
    }
    
    /**
     * 更新监控预览 - 增强版
     */
    async updateMonitorPreview() {
        try {
            console.log('🔄 更新监控预览...');
            
            const selectedCategories = Array.from(
                document.querySelectorAll('#categorySelectorGrid input[type="checkbox"]:checked')
            ).map(cb => parseInt(cb.value));
            
            console.log('已选择的分类:', selectedCategories);
            
            let totalProducts = 0;
            
            // 增强商品数量获取逻辑 - 支持多种获取方式
            for (const categoryId of selectedCategories) {
                try {
                    // 方法1: 通过数据管理器获取
                    if (this.localDataManager) {
                        const count = await this.localDataManager.getProductCountByCategory(categoryId);
                        totalProducts += count;
                        console.log(`✅ 通过数据管理器获取分类 ${categoryId}: ${count} 件商品`);
                    } else {
                        throw new Error('数据管理器未初始化');
                    }
                } catch (error) {
                    console.warn(`⚠️ 数据管理器获取失败，尝试从HTML获取:`, error);
                    
                    // 方法2: 从HTML元素中解析商品数量（备用方案）
                    try {
                        const categoryItem = document.querySelector(`[data-category-id="${categoryId}"]`);
                        const countText = categoryItem?.querySelector('.category-count')?.textContent || '0 件商品';
                        const match = countText.match(/(\d+)\s*件商品/);
                        const htmlCount = match ? parseInt(match[1]) : 0;
                        totalProducts += htmlCount;
                        console.log(`✅ 通过HTML获取分类 ${categoryId}: ${htmlCount} 件商品`);
                    } catch (htmlError) {
                        console.warn(`❌ HTML解析也失败，分类 ${categoryId} 计为0件商品:`, htmlError);
                        // 继续处理下一个分类，不中断流程
                    }
                }
            }
            
            // 更新预览数据
            const selectedCategoryCountEl = document.getElementById('selectedCategoryCount');
            const selectedProductCountEl = document.getElementById('selectedProductCount');
            const estimatedTimeEl = document.getElementById('estimatedTime');
            
            if (selectedCategoryCountEl) {
                selectedCategoryCountEl.textContent = selectedCategories.length;
            }
            
            if (selectedProductCountEl) {
                selectedProductCountEl.textContent = totalProducts;
            }
            
            // 计算预计时间
            const intervalEl = document.getElementById('monitorInterval');
            const concurrentEl = document.getElementById('concurrentLimit');
            
            const interval = parseInt(intervalEl?.value) || 60;
            const concurrent = 15; // Level 1保守优化：硬编码15并发
            const estimatedMinutes = totalProducts > 0 ? Math.ceil((totalProducts / concurrent * interval) / 60) : 0;
            
            if (estimatedTimeEl) {
                estimatedTimeEl.textContent = 
                    estimatedMinutes > 0 ? `约 ${estimatedMinutes} 分钟` : '< 1 分钟';
            }
            
            // ✅ 增强按钮状态控制逻辑
            const startBtn = document.getElementById('startAdvancedBatchBtn');
            if (startBtn) {
                // 更宽松的启用条件：只要选择了分类就启用（即使商品数为0也允许）
                const shouldEnable = selectedCategories.length > 0;
                const wasDisabled = startBtn.disabled;
                
                startBtn.disabled = !shouldEnable;
                
                // 添加视觉反馈
                if (shouldEnable && wasDisabled) {
                    // 按钮从禁用变为启用时的动画效果
                    startBtn.style.transition = 'all 0.3s ease';
                    startBtn.style.transform = 'scale(1.05)';
                    setTimeout(() => {
                        startBtn.style.transform = 'scale(1)';
                    }, 200);
                }
                
                console.log(`🔘 按钮状态更新: ${shouldEnable ? '启用' : '禁用'}, 选中分类: ${selectedCategories.length}, 商品总数: ${totalProducts}`);
                
                // 更新按钮文本提示
                if (shouldEnable) {
                    startBtn.title = `准备监控 ${selectedCategories.length} 个分类，共 ${totalProducts} 件商品`;
                } else {
                    startBtn.title = '请至少选择一个分类';
                }
            } else {
                console.warn('❌ 找不到启动按钮元素 #startAdvancedBatchBtn');
            }
            
        } catch (error) {
            console.error('❌ 更新监控预览失败:', error);
            
            // 错误处理：确保按钮状态不会被卡住
            const startBtn = document.getElementById('startAdvancedBatchBtn');
            if (startBtn) {
                startBtn.disabled = true; // 出错时禁用按钮
                startBtn.title = '预览更新失败，请重试';
            }
        }
    }
    
    /**
     * 启动高级批量监控
     */
    async startAdvancedBatchMonitoring() {
        try {
            const selectedCategories = Array.from(
                document.querySelectorAll('#categorySelectorGrid input[type="checkbox"]:checked')
            ).map(cb => parseInt(cb.value));

            if (selectedCategories.length === 0) {
                this.showNotification('请至少选择一个分类进行监控', 'warning');
                return;
            }

            // 显示进度条
            this.showBatchProgress();

            // 最高性能固定配置：5并发 + 0延迟 + 自动重试 + 异常检测
            const config = {
                selectedCategories: selectedCategories,
                interval: 0, // 批次间无等待，最高性能
                concurrent: 15, // Level 1保守优化：15并发
                autoRetry: document.getElementById('autoRetry')?.checked ?? true,
                enableAnomalyDetection: document.getElementById('enableAnomalyDetection')?.checked ?? true
            };

            console.log('🚀 启动高级批量监控:', config);

            // 设置按钮为启动中状态
            this.updateButtonState('starting');

            // 监控状态标志
            let isRunningStateSet = false;

            // 使用按需初始化确保BatchMonitorService可用
            const batchService = await this.ensureBatchMonitorService();

            // 使用批量监控服务，传递进度回调
            await batchService.startBatchMonitoring({
                ...config,
                onProgress: (completed, total, message) => {
                    // 第一次收到进度更新时，设置按钮为运行状态
                    if (!isRunningStateSet) {
                        this.updateButtonState('running');
                        isRunningStateSet = true;
                    }
                    this.updateBatchProgress(completed, total, message);
                },
                onComplete: () => {
                    this.hideBatchProgress();
                    this.resetStartButton();
                    this.showNotification('批量监控完成！', 'success');
                },
                onError: (error) => {
                    this.hideBatchProgress();
                    this.resetStartButton();
                    this.showNotification('批量监控出错: ' + error.message, 'error');
                }
            });
            
        } catch (error) {
            console.error('❌ 启动高级批量监控失败:', error);
            this.showNotification('启动高级批量监控失败: ' + error.message, 'error');
            this.hideBatchProgress();
            this.resetStartButton();
        }
    }
    
    /**
     * 显示批量监控进度条
     */
    showBatchProgress() {
        const progressSection = document.getElementById('batchProgressSection');
        if (progressSection) {
            progressSection.style.display = 'block';
            this.updateBatchProgress(0, 0, '准备开始监控...');
        }
    }
    
    /**
     * 隐藏批量监控进度条
     */
    hideBatchProgress() {
        const progressSection = document.getElementById('batchProgressSection');
        if (progressSection) {
            progressSection.style.display = 'none';
        }
    }
    
    /**
     * 更新批量监控进度
     */
    updateBatchProgress(completed, total, message = '') {
        const progressFill = document.getElementById('batchProgressFill');
        const progressStats = document.getElementById('batchProgressStats');
        const progressInfo = document.getElementById('batchProgressInfo');
        
        const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;
        
        if (progressFill) {
            progressFill.style.width = percentage + '%';
        }
        
        if (progressStats) {
            progressStats.textContent = `${completed}/${total}`;
        }
        
        if (progressInfo && message) {
            progressInfo.textContent = message;
        }
    }
    
    /**
     * 处理批量监控动作按钮点击
     */
    async handleBatchMonitoringAction() {
        const startBtn = document.getElementById('startAdvancedBatchBtn');
        if (!startBtn) return;

        // 如果BatchMonitorService未初始化，直接启动新监控
        if (!this.batchMonitorService) {
            this.startAdvancedBatchMonitoring();
            return;
        }

        // 获取当前监控状态
        const status = this.batchMonitorService.getMonitoringStatus();
        
        switch (status.status) {
            case 'idle':
                // 启动监控
                this.startAdvancedBatchMonitoring();
                break;
                
            case 'running':
                // 暂停监控
                const pauseResult = this.batchMonitorService.pauseMonitoring();
                if (pauseResult.success) {
                    this.updateButtonState('paused');
                    this.showNotification('监控已暂停', 'info');
                } else {
                    this.showNotification(pauseResult.message, 'error');
                }
                break;
                
            case 'paused':
                // 继续监控
                const resumeResult = this.batchMonitorService.resumeMonitoring();
                if (resumeResult.success) {
                    this.updateButtonState('running');
                    this.showNotification('监控已继续', 'success');
                } else {
                    this.showNotification(resumeResult.message, 'error');
                }
                break;
                
            default:
                console.warn('未知的监控状态:', status.status);
                break;
        }
    }
    
    /**
     * 处理停止监控
     */
    async handleStopMonitoring() {
        if (this.batchMonitorService) {
            const result = this.batchMonitorService.stopMonitoring();
            if (result.success) {
                this.hideBatchProgress();
                this.updateButtonState('idle');
                this.showNotification('监控已停止', 'info');
            } else {
                this.showNotification(result.message, 'error');
            }
        } else {
            console.warn('⚠️ 批量监控服务未初始化，无法停止');
            this.hideBatchProgress();
            this.updateButtonState('idle');
        }
    }

    /**
     * 更新按钮状态显示
     */
    updateButtonState(state) {
        const startBtn = document.getElementById('startAdvancedBatchBtn');
        const stopBtn = document.getElementById('stopBatchBtn');
        if (!startBtn) return;

        // 如果BatchMonitorService未初始化，使用默认状态
        const status = this.batchMonitorService ?
            this.batchMonitorService.getMonitoringStatus() :
            { status: 'idle', isRunning: false };
        
        switch (state) {
            case 'running':
                startBtn.disabled = false;
                startBtn.className = 'btn btn-warning';
                startBtn.innerHTML = '<span class="btn-icon">⏸️</span>暂停监控';
                startBtn.title = status.message || '点击暂停监控';
                
                if (stopBtn) {
                    stopBtn.style.display = 'block';
                    stopBtn.disabled = false;
                }
                break;
                
            case 'paused':
                startBtn.disabled = false;
                startBtn.className = 'btn btn-success';
                startBtn.innerHTML = '<span class="btn-icon">▶️</span>继续监控';
                startBtn.title = status.message || '点击继续监控';
                
                if (stopBtn) {
                    stopBtn.style.display = 'block';
                    stopBtn.disabled = false;
                }
                break;
                
            case 'starting':
                startBtn.disabled = true;
                startBtn.className = 'btn btn-secondary';
                startBtn.innerHTML = '<span class="btn-icon">⏳</span>启动中...';
                startBtn.title = '正在启动监控，请稍候';
                
                if (stopBtn) {
                    stopBtn.style.display = 'none';
                }
                break;
                
            case 'idle':
            default:
                startBtn.disabled = false;
                startBtn.className = 'btn btn-primary';
                startBtn.innerHTML = '<span class="btn-icon">🚀</span>启动批量监控';
                startBtn.title = '启动批量监控';
                
                if (stopBtn) {
                    stopBtn.style.display = 'none';
                }
                break;
        }
    }
    
    /**
     * 重置启动按钮
     */
    resetStartButton() {
        this.updateButtonState('idle');
    }
    
    /**
     * 切换异常检测设置面板
     */
    toggleAnomalySettings() {
        const panel = document.getElementById('anomalySettingsPanel');
        const isVisible = panel.style.display !== 'none';
        
        if (isVisible) {
            panel.style.display = 'none';
        } else {
            panel.style.display = 'block';
            this.loadAnomalySettings();
        }
    }
    
    /**
     * 加载异常检测设置
     */
    async loadAnomalySettings() {
        // 简化版：加载默认阈值到简化界面
        try {
            const salesInput = document.getElementById('easySalesThreshold');
            const revenueInput = document.getElementById('easyRevenueThreshold');

            if (salesInput && !salesInput.value) salesInput.value = '50';
            if (revenueInput && !revenueInput.value) revenueInput.value = '500';

            console.log('✅ 简化版异常检测设置已加载');
        } catch (error) {
            console.error('❌ 加载异常检测设置失败:', error);
        }
    }
    
    /**
     * 保存异常检测设置
     */
    async saveAnomalySettings() {
        // 简化版：设置由EasyAnomalyManager自动处理，这里只提供兼容性支持
        console.log('🔧 设置已由简化系统自动处理');
        this.showNotification('设置已自动保存', 'success');
    }
    
    /**
     * 重置异常检测设置
     */
    async resetAnomalySettings() {
        // 简化版：重置阈值为默认值
        const salesInput = document.getElementById('easySalesThreshold');
        const revenueInput = document.getElementById('easyRevenueThreshold');

        if (salesInput) salesInput.value = '50';
        if (revenueInput) revenueInput.value = '500';

        console.log('🔧 异常检测阈值已重置为默认值');
        this.showNotification('已重置为默认阈值', 'success');
    }
    
    /**
     * 更新异常检测状态显示
     */
    updateAnomalyDetectionStatus(status, text, lastTime = null) {
        const statusDot = document.getElementById('anomalyStatusDot');
        const statusText = document.getElementById('anomalyStatusText');
        const lastDetection = document.getElementById('lastDetection');
        
        if (statusDot) {
            statusDot.className = `status-dot ${status}`;
        }
        
        if (statusText) {
            statusText.textContent = text;
        }
        
        if (lastDetection && lastTime) {
            lastDetection.innerHTML = `<span class="detection-time">上次运行: ${new Date(lastTime).toLocaleTimeString()}</span>`;
        }
    }
    
    /**
     * 更新异常统计显示
     */
    updateAnomalyStats(stats) {
        // 由于 sidepanel 中没有这些统计元素，改为简单的控制台输出
        console.log('📊 异常统计更新:', stats);

        // 如果有对应的元素再更新，否则静默忽略
        const criticalElement = document.getElementById('criticalAnomalies');
        const warningElement = document.getElementById('warningAnomalies');
        const infoElement = document.getElementById('infoAnomalies');

        if (criticalElement) criticalElement.textContent = stats.critical || 0;
        if (warningElement) warningElement.textContent = stats.warning || 0;
        if (infoElement) infoElement.textContent = stats.info || 0;

        // ultrathink: 更新侧边栏的anomalyCount元素
        const anomalyCountElement = document.getElementById('anomalyCount');
        if (anomalyCountElement) {
            const totalAnomalies = (stats.critical || 0) + (stats.warning || 0) + (stats.info || 0);
            anomalyCountElement.textContent = totalAnomalies;
            console.log('✅ [updateAnomalyStats] 已更新anomalyCount显示:', totalAnomalies);
        } else {
            console.log('⚠️ [updateAnomalyStats] 未找到anomalyCount元素');
        }
    }

    /**
     * 初始化异常检测分类选择器
     */
    async initEasyAnomalyManager() {
        try {
            console.log('🎛️ 初始化简化异常检测管理器...');

            // 初始化EasyAnomalyManager
            const success = await this.easyAnomalyManager.init(this.localDataManager, this.categoryManager);

            if (success) {
                console.log('✅ 简化异常检测管理器初始化完成');
            } else {
                console.error('❌ 简化异常检测管理器初始化失败');
            }

        } catch (error) {
            console.error('❌ 初始化简化异常检测管理器失败:', error);
        }
    }

    /**
     * 更新异常检测分类选择摘要
     */
    updateAnomalyCategorySelectionSummary() {
        // 简化版：不再需要分类选择摘要
        console.log('🔧 分类选择功能已移除，使用自动全部分类检测');
    }

    /**
     * 获取选中的异常检测分类ID列表
     */
    getSelectedAnomalyCategories() {
        // 简化版：返回空数组，因为现在检测所有分类
        return [];
    }

    /**
     * 获取用户自定义阈值
     */
    getCustomThresholds() {
        try {
            const salesThresholdInput = document.getElementById('salesThreshold');
            const revenueThresholdInput = document.getElementById('revenueThreshold');

            const salesThreshold = salesThresholdInput ? parseInt(salesThresholdInput.value) || 50 : 50;
            const revenueThreshold = revenueThresholdInput ? parseInt(revenueThresholdInput.value) || 500 : 500;

            return {
                sales: salesThreshold,
                revenue: revenueThreshold
            };
        } catch (error) {
            console.error('❌ 获取自定义阈值失败:', error);
            return {
                sales: 50,
                revenue: 500
            };
        }
    }

    /**
     * 加载分类复选框
     */
    async loadCategoryCheckboxes() {
        try {
            console.log('🔄 加载分类复选框...');
            
            // 1. 多重验证：确保所有依赖就绪
            const validationResults = await this.validateBatchModePrerequisites();
            if (!validationResults.isValid) {
                throw new Error(`前置条件不满足: ${validationResults.errors.join(', ')}`);
            }
            
            const grid = document.getElementById('categorySelectorGrid');
            
            // 2. 更新加载状态UI
            this.updateCategoryLoadingState(grid, 'loading', '正在加载分类数据...');
            
            // 3. 获取分类数据（增加重试机制）
            const categories = await this.getCategoriesWithRetry();
            
            console.log('✅ 获取到分类数据:', categories.length, '个分类');
            
            if (!categories || categories.length === 0) {
                this.updateCategoryLoadingState(grid, 'empty', '暂无分类数据');
                return false;
            }
            
            // 4. 并发获取商品统计（优化性能）
            const categoryItems = await this.generateCategoryCheckboxes(categories);
            grid.innerHTML = categoryItems.join('');
            
            // 5. 绑定事件并验证
            this.bindCategoryCheckboxEvents(grid);
            this.updateCategoryLoadingState(grid, 'success', '分类加载完成');
            
            console.log(`✅ 成功加载 ${categories.length} 个分类`);
            return true;
            
        } catch (error) {
            console.error('❌ 加载分类复选框失败:', error);
            const grid = document.getElementById('categorySelectorGrid');
            this.updateCategoryLoadingState(grid, 'error', error.message);
            return false;
        }
    }

    /**
     * 前置条件验证 - 新增方法
     */
    async validateBatchModePrerequisites() {
        const errors = [];
        
        if (!this.categoryManager) {
            errors.push('CategoryManager未初始化');
        }
        
        if (!this.localDataManager) {
            errors.push('LocalDataManager未初始化');
        }
        
        const grid = document.getElementById('categorySelectorGrid');
        if (!grid) {
            errors.push('categorySelectorGrid元素不存在');
        }
        
        return {
            isValid: errors.length === 0,
            errors: errors
        };
    }

    /**
     * 分类数据获取（重试机制）- 新增方法
     */
    async getCategoriesWithRetry(maxRetries = 3) {
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                return await this.categoryManager.getAllCategories();
            } catch (error) {
                console.warn(`获取分类数据失败 (尝试 ${attempt}/${maxRetries}):`, error);
                if (attempt === maxRetries) {
                    throw error;
                }
                await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
            }
        }
    }

    /**
     * 生成分类复选框 - 新增方法
     */
    async generateCategoryCheckboxes(categories) {
        return await Promise.all(categories.map(async (category) => {
            try {
                const productCount = await this.localDataManager.getProductCountByCategory(category.id);
                
                return `
                    <div class="category-checkbox-item" data-category-id="${category.id}">
                        <div class="category-marker" style="background: ${category.color || '#6366f1'}"></div>
                        <input type="checkbox" class="category-checkbox" value="${category.id}">
                        <div class="category-info">
                            <div class="category-name">${category.name}</div>
                            <div class="category-meta">
                                <span class="category-count">${productCount} 件商品</span>
                                ${category.description ? `<span class="category-desc">${category.description}</span>` : ''}
                            </div>
                        </div>
                    </div>
                `;
            } catch (error) {
                console.warn(`获取分类 ${category.id} 商品数量失败:`, error);
                return `
                    <div class="category-checkbox-item" data-category-id="${category.id}">
                        <div class="category-marker" style="background: ${category.color || '#6366f1'}"></div>
                        <input type="checkbox" class="category-checkbox" value="${category.id}">
                        <div class="category-info">
                            <div class="category-name">${category.name}</div>
                            <div class="category-meta">
                                <span class="category-count">- 件商品</span>
                                ${category.description ? `<span class="category-desc">${category.description}</span>` : ''}
                            </div>
                        </div>
                    </div>
                `;
            }
        }));
    }

    /**
     * 绑定分类复选框事件 - 新增方法
     */
    bindCategoryCheckboxEvents(grid) {
        // 绑定分类选择事件
        grid.querySelectorAll('.category-checkbox-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (e.target.type !== 'checkbox') {
                    const checkbox = item.querySelector('.category-checkbox');
                    checkbox.checked = !checkbox.checked;
                    checkbox.dispatchEvent(new Event('change'));
                }
            });
        });
        
        grid.querySelectorAll('.category-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                const item = checkbox.closest('.category-checkbox-item');
                item.classList.toggle('selected', checkbox.checked);
                this.updateMonitorPreview();
            });
        });
    }

    /**
     * 状态更新UI - 新增方法
     */
    updateCategoryLoadingState(grid, state, message) {
        const stateConfigs = {
            loading: {
                html: `
                    <div class="loading-state">
                        <div class="spinner"></div>
                        <div class="loading-text">${message}</div>
                    </div>
                `,
                class: 'loading'
            },
            empty: {
                html: `
                    <div class="empty-state">
                        <div class="empty-icon">📁</div>
                        <div class="empty-text">${message}</div>
                        <button class="btn btn-primary btn-sm" onclick="document.getElementById('manageCategoriesBtn').click()">创建分类</button>
                    </div>
                `,
                class: 'empty'
            },
            error: {
                html: `
                    <div class="error-state">
                        <div class="error-icon">❌</div>
                        <div class="error-text">${message}</div>
                        <div class="error-actions">
                            <button class="btn btn-secondary btn-sm" onclick="xiaohongShuMonitor.loadCategoryCheckboxes()">重试</button>
                            <button class="btn btn-outline btn-sm" onclick="xiaohongShuMonitor.ensureBatchModeReady()">重新初始化</button>
                        </div>
                    </div>
                `,
                class: 'error'
            },
            success: {
                html: '', // 正常内容，不需要特殊HTML
                class: 'loaded'
            }
        };
        
        if (grid && stateConfigs[state]) {
            if (state !== 'success') {
                grid.innerHTML = stateConfigs[state].html;
            }
            grid.className = `category-selector-grid ${stateConfigs[state].class}`;
            
            console.log(`🔄 分类选择器状态: ${state} - ${message}`);
        }
    }
    
    /**
     * 加载异常统计
     */
    async loadAnomalyStats() {
        try {
            console.log('🔄 加载简化异常统计...');

            // 简化版：直接从数据库查询is_anomaly为true的商品数量
            if (!this.localDataManager) {
                console.log('数据管理器未初始化，跳过统计加载');
                return;
            }

            const products = await this.localDataManager.getAllProducts();
            const anomalyCount = products.filter(p => p.is_anomaly).length;

            const stats = {
                totalAnomalies: anomalyCount,
                totalProducts: products.length,
                anomalyRate: products.length > 0 ? (anomalyCount / products.length * 100).toFixed(2) : 0
            };

            // 改为直接传递简化的统计信息
            this.updateAnomalyStats({
                critical: 0,  // sidepanel 不区分严重程度，统一设为0
                warning: anomalyCount,  // 所有异常都作为warning级别
                info: 0
            });
            console.log('✅ 简化异常统计加载完成:', stats);

        } catch (error) {
            console.error('❌ 加载异常统计失败:', error);
        }
    }

    /**
     * 初始化并发架构 - 延迟初始化，避免预创建标签页
     */
    async initializeConcurrentArchitecture() {
        try {
            console.log('🚀 初始化并发架构（延迟初始化模式）...');

            // 初始化停止协调器
            this.stopCoordinator = new StopCoordinator();

            // 延迟初始化标签页池管理器 - 仅在实际需要时才创建
            this.tabPoolManager = null; // 设为null，延迟创建
            this.tabPoolManagerConfig = {
                maxPoolSize: 5,
                lazyLoadEnabled: true,
                initialPoolSize: 0
            };
            
            // 延迟初始化批量监控服务 - 仅在实际需要时才创建
            this.batchMonitorService = null;
            this.batchMonitorServiceInitialized = false;
            
            console.log('✅ 并发架构基础组件初始化完成 - TabPoolManager和BatchMonitorService将在需要时延迟创建');
            
        } catch (error) {
            console.error('❌ 并发架构初始化失败:', error);
            // 不抛出错误，允许应用继续运行（降级到非池模式）
        }
    }

    /**
     * 按需初始化TabPoolManager - 仅在实际爬取时才创建
     */
    async ensureTabPoolManager() {
        if (this.tabPoolManager === null) {
            console.log('🔄 按需初始化TabPoolManager...');
            try {
                this.tabPoolManager = new TabPoolManager(this.tabPoolManagerConfig.maxPoolSize);
                this.tabPoolManager.lazyLoadEnabled = this.tabPoolManagerConfig.lazyLoadEnabled;
                this.tabPoolManager.initialPoolSize = this.tabPoolManagerConfig.initialPoolSize;
                await this.tabPoolManager.initialize();

                // 注册到停止协调器
                this.stopCoordinator.register('TabPoolManager', this.tabPoolManager);

                console.log('✅ TabPoolManager按需初始化完成');
                return this.tabPoolManager;
            } catch (error) {
                console.error('❌ TabPoolManager按需初始化失败:', error);
                this.tabPoolManager = null;
                throw error;
            }
        }
        return this.tabPoolManager;
    }

    /**
     * 按需初始化BatchMonitorService - 仅在实际爬取时才创建
     */
    async ensureBatchMonitorService() {
        if (this.batchMonitorService === null && !this.batchMonitorServiceInitialized) {
            console.log('🔄 按需初始化BatchMonitorService...');
            try {
                this.batchMonitorServiceInitialized = true;

                // 确保TabPoolManager已初始化
                const tabPoolManager = await this.ensureTabPoolManager();

                this.batchMonitorService = new BatchMonitorService(this.sharedDataService, this);
                await this.batchMonitorService.init(tabPoolManager);

                // 注册到停止协调器
                this.stopCoordinator.register('BatchMonitorService', this.batchMonitorService);

                console.log('✅ BatchMonitorService按需初始化完成');
                return this.batchMonitorService;
            } catch (error) {
                console.error('❌ BatchMonitorService按需初始化失败:', error);
                this.batchMonitorService = null;
                this.batchMonitorServiceInitialized = false;
                throw error;
            }
        }
        return this.batchMonitorService;
    }
}

/**
 * 批量监控服务 - 核心监控功能
 * 从 data-manager 迁移的完整监控引擎
 */
class BatchMonitorService {
    constructor(sharedDataService, sidePanelInstance = null) {
        this.sharedDataService = sharedDataService;
        this.localDataManager = null;
        this.categoryManager = null;
        this.easyAnomalyManager = null;

        // 🔧 修复：添加主面板实例引用
        this.sidePanel = sidePanelInstance;

        // 监控状态
        this.monitorState = null;
        this.componentBridge = null;

        console.log('📡 BatchMonitorService 初始化');
    }
    
    async init(tabPoolManager = null) {
        // 获取共享服务
        this.localDataManager = this.sharedDataService.getLocalDataManager();
        this.categoryManager = this.sharedDataService.getCategoryManager();
        this.easyAnomalyManager = new EasyAnomalyManager();

        // 获取通信桥梁
        this.componentBridge = window.getComponentBridge ? window.getComponentBridge() : null;

        // 初始化简化的异常检测管理器
        if (this.easyAnomalyManager) {
            await this.easyAnomalyManager.init(this.localDataManager, this.categoryManager);
        }
        
        // 设置标签页池管理器 (直接传入或从全局获取)
        this.tabPoolManager = tabPoolManager || (window.xiaohongshuApp ? window.xiaohongshuApp.tabPoolManager : null);

        // 🚀 Phase 3 优化: 启动内存优化
        this.initializeMemoryOptimization();

        console.log('✅ BatchMonitorService 初始化完成', {
            hasTabPoolManager: !!this.tabPoolManager,
            tabPoolSource: tabPoolManager ? 'parameter' : 'global',
            memoryOptimization: 'enabled'
        });
    }

    /**
     * 🆕 检测系统内存并自动设置固定并发数
     * 规则：
     * - ≤8GB  → 5个并发（保守模式）
     * - ≤16GB → 8个并发（均衡模式）
     * - ≤32GB → 11个并发（性能模式）
     * - >32GB → 15个并发（极限模式）
     */
    async detectAndSetFixedConcurrency() {
        let systemMemoryGB = null;
        let isManualConfig = false;

        try {
            // 🆕 优先读取用户手动配置
            const savedMemoryConfig = localStorage.getItem('systemMemoryConfig');
            if (savedMemoryConfig && savedMemoryConfig !== 'auto') {
                systemMemoryGB = parseInt(savedMemoryConfig);
                isManualConfig = true;
                console.log(`✅ 使用手动配置的运存: ${systemMemoryGB}GB`);
            } else {
                // 方法1：navigator.deviceMemory（最准确）
                if ('deviceMemory' in navigator) {
                    systemMemoryGB = navigator.deviceMemory;
                    console.log(`✅ 检测到系统内存: ${systemMemoryGB}GB`);
                }
                // 方法2：通过堆内存估算
                else if ('memory' in performance && performance.memory) {
                    const heapLimit = performance.memory.jsHeapSizeLimit;
                    systemMemoryGB = Math.round((heapLimit / (1024 * 1024 * 1024)) / 0.25);
                    console.log(`⚠️ 估算系统内存: ${systemMemoryGB}GB`);
                }
            }
        } catch (error) {
            console.warn('⚠️ 无法检测系统内存，使用默认配置:', error);
        }

        // 根据内存确定并发数
        let concurrent, mode;

        if (!systemMemoryGB) {
            // 无法检测，默认保守模式
            concurrent = 5;
            mode = '保守模式(默认)';
        } else if (systemMemoryGB <= 8) {
            concurrent = 5;
            mode = '保守模式';
        } else if (systemMemoryGB <= 16) {
            concurrent = 8;
            mode = '均衡模式';
        } else if (systemMemoryGB <= 32) {
            concurrent = 11;
            mode = '性能模式';
        } else {
            concurrent = 15;
            mode = '极限模式';
        }

        const configSource = isManualConfig ? '手动配置' : '自动检测';
        console.log(`📊 批量监控模式: ${mode} - ${concurrent}个并发 (${configSource}: ${systemMemoryGB || '未知'}GB)`);

        // 可选：显示通知
        if (this.sidePanel && this.sidePanel.showNotification) {
            this.sidePanel.showNotification(
                `批量监控以${mode}运行 (${concurrent}个并发)`,
                'info'
            );
        }

        return concurrent;
    }

    /**
     * 开始批量监控 - 主入口
     */
    async startBatchMonitoring(config) {
        try {
            console.log('🚀 开始批量监控...', config);

            // 🆕 检测系统内存并设置固定并发数
            const fixedConcurrent = await this.detectAndSetFixedConcurrency();
            console.log(`🎯 本次批量监控固定并发数: ${fixedConcurrent}`);

            // 初始化监控状态
            this.monitorState = {
                isRunning: true,
                isPaused: false,
                totalProducts: 0,
                processedProducts: 0,
                successCount: 0,
                errorCount: 0,
                skippedCount: 0,
                violationCount: 0,
                startTime: new Date(),
                categories: config.selectedCategories,
                config: config,
                // 保存回调函数
                onProgress: config.onProgress,
                onComplete: config.onComplete,
                onError: config.onError,
                // 🆕 保存固定并发数
                fixedConcurrent: fixedConcurrent
            };
            
            // 收集所有要监控的商品
            const allProducts = await this.collectMonitorProducts(config.selectedCategories);
            this.monitorState.totalProducts = allProducts.length;
            
            // 初始进度更新
            if (this.monitorState.onProgress) {
                this.monitorState.onProgress(0, this.monitorState.totalProducts, `准备监控 ${this.monitorState.totalProducts} 个商品...`);
            }
            
            // 通知 data-manager 开始监控
            this.componentBridge.notifyMonitoringStatus('started', {
                totalProducts: allProducts.length,
                categories: config.selectedCategories
            });
            
            // 分批处理商品
            await this.processProductsBatch(allProducts, config);
            
            // 监控完成
            this.completeMonitoring();
            
        } catch (error) {
            console.error('❌ 批量监控失败:', error);
            
            // 调用错误回调
            if (this.monitorState && this.monitorState.onError) {
                this.monitorState.onError(error);
            }
            
            this.componentBridge.notifyMonitoringStatus('stopped', { 
                error: error.message 
            });
            throw error;
        }
    }
    
    /**
     * 收集要监控的商品
     */
    async collectMonitorProducts(categoryIds) {
        const allProducts = [];
        
        for (const categoryId of categoryIds) {
            try {
                // 修复：传入大的limit值获取所有商品，而不是默认的20件
                const result = await this.localDataManager.getProducts(categoryId, {}, { page: 1, limit: 50000 });
                allProducts.push(...result.products);
                
                console.log(`收集分类 ${categoryId} 的 ${result.products.length} 件商品`);
            } catch (error) {
                console.error(`收集分类 ${categoryId} 商品失败:`, error);
            }
        }
        
        console.log(`🎯 批量监控商品收集完成: 总计 ${allProducts.length} 件商品`);
        return allProducts;
    }
    
    /**
     * 分批处理商品
     */
    async processProductsBatch(products, config) {
        const concurrent = config.concurrent || 15; // Level 1保守优化：默认15并发
        // 修复：正确处理interval为0的情况，0应该表示无延迟而不是默认值
        const intervalSeconds = config.interval !== undefined ? config.interval : 60;
        const interval = intervalSeconds * 1000; // 转换为毫秒
        
        // 分批处理
        for (let i = 0; i < products.length; i += concurrent) {
            if (!this.monitorState.isRunning) break;
            
            // 处理暂停状态
            while (this.monitorState.isPaused && this.monitorState.isRunning) {
                await this.sleep(1000);
            }
            
            const batch = products.slice(i, i + concurrent);
            console.log(`处理批次 ${Math.floor(i/concurrent)+1}: ${batch.length} 件商品`);

            // 🚀 Phase 2 优化: 异步流水线处理替换Promise.allSettled阻塞
            await this.processAsyncPipeline(batch, config);
            
            // 🔥 ultrathink: 智能批次间等待 - 根据系统负载动态调整
            if (i + concurrent < products.length) {
                const dynamicInterval = this.calculateOptimalInterval();
                if (dynamicInterval > 0) {
                    const intervalSeconds = Math.round(dynamicInterval / 1000);
                    console.log(`智能等待 ${intervalSeconds} 秒 (基于系统负载优化)...`);
                    await this.sleep(dynamicInterval);
                }
            }
        }
    }
    
    /**
     * 处理单个商品监控
     */
    async processProductMonitor(product, config) {
        if (!this.monitorState.isRunning) return;

        // 🔥 ultrathink: 关键修复 - 每个商品处理前检查暂停状态
        if (this.monitorState?.isPaused) {
            console.log(`⏸️ 商品处理已暂停: ${product.product_name || product.product_id}`);
            return {
                paused: true,
                message: '任务已暂停',
                product_id: product.product_id
            };
        }

        try {
            console.log(`开始监控商品: ${product.product_name || product.product_id}`);
            
            // 调用爬虫服务提取最新数据
            const updatedData = await this.callCrawlerService(product.product_url || product.url);

            // 🚀 ultrathink: 违规商品快速跳过处理
            if (updatedData && updatedData.data && updatedData.data.violation) {
                this.monitorState.skippedCount = (this.monitorState.skippedCount || 0) + 1;
                this.monitorState.violationCount = (this.monitorState.violationCount || 0) + 1;

                console.log(`⚠️ 跳过违规商品: ${product.product_name || product.product_id}`);
                console.log(`   ├─ 检测方法: ${updatedData.data.violationDetails?.method || 'unknown'}`);
                console.log(`   ├─ 检测耗时: ${updatedData.data.violationDetails?.duration?.toFixed(2) || 'N/A'}ms`);
                console.log(`   └─ 违规原因: ${updatedData.data.violationDetails?.reason || updatedData.data.message}`);

                // 通知进度（违规商品计为已处理）
                this.updateProgress();

                return {
                    success: false,
                    skipped: true,
                    reason: 'violation',
                    details: updatedData.data.violationDetails
                };
            }

            if (updatedData && updatedData.success) {
                // 转换数据格式以符合LocalDataManager的预期
                const formattedData = {
                    product_id: product.product_id,
                    product_name: product.product_name || '未知商品',
                    product_url: product.product_url || product.url,
                    category_id: product.category_id,
                    product_sales: updatedData.data.productSales,
                    store_sales: updatedData.data.storeSales,
                    extracted_at: updatedData.data.timestamp || new Date().toISOString(),
                    raw_data: updatedData.data
                };
                
                // 📊 爬虫数据保存日志
                console.log(`📥 [数据保存] ${formattedData.product_name}`);
                console.log(`   ├─ 商品销量: ${formattedData.product_sales}`);
                console.log(`   ├─ 店铺销量: ${formattedData.store_sales}`);
                console.log(`   └─ 爬取时间: ${new Date().toLocaleString()}`);
                
                // 使用时间序列upsert保存数据 (支持动态日期字段)
                let saveResult;
                try {
                    saveResult = await this.localDataManager.upsertProductWithTimeSeries(formattedData, product.category_id, new Date());
                    
                    this.monitorState.successCount++;
                    
                    // 生成详细的操作描述
                    let operationDesc = '';
                    if (saveResult.timeSeriesOperation === 'updated_day') {
                        operationDesc = `当天数据更新 (${saveResult.dateStr}, 销量: ${saveResult.productSales || 'N/A'})`;
                    } else if (saveResult.timeSeriesOperation === 'created_day') {
                        operationDesc = `新建日期字段 (${saveResult.dateStr}, 销量: ${saveResult.productSales || 'N/A'})`;
                    } else {
                        operationDesc = `监控成功 (销量: ${saveResult.productSales || 'N/A'})`;
                    }
                    
                    console.log(`✅ ${product.product_name || product.product_id} - ${operationDesc}`);
                    
                    // 显示时间序列统计信息
                    if (saveResult.timeSeriesCount && saveResult.timeSeriesCount.uniqueDays > 1) {
                        console.log(`📊 ${product.product_name || product.product_id} - 已追踪 ${saveResult.timeSeriesCount.uniqueDays} 天销量数据`);
                    }
                    
                } catch (saveError) {
                    console.error(`❌ 数据保存失败 ${product.product_name || product.product_id}:`, saveError);
                    throw new Error(`数据保存失败: ${saveError.message}`);
                }
                
                // 检测异常变化
                await this.checkProductAnomaly(product.product_id, formattedData);
                
                // 通知数据更新
                if (this.componentBridge) {
                    this.componentBridge.notifyDataUpdate('product', formattedData);
                }
                
            } else {
                this.monitorState.errorCount++;
                console.error(`❌ ${product.product_name || product.product_id} - 提取失败`, {
                    url: product.product_url || product.url,
                    response: updatedData,
                    hasSuccess: updatedData?.success,
                    hasData: !!updatedData?.data
                });
                
                // 🚀 Phase 2 优化: 智能错误恢复机制
                if (config.autoRetry) {
                    return await this.smartErrorRecovery(product, config, updatedData, 'extraction_failed');
                }
            }
            
        } catch (error) {
            this.monitorState.errorCount++;
            console.error(`❌ ${product.product_name || product.product_id} - ${error.message}`);

            // 🚀 Phase 2 优化: 智能错误恢复机制
            if (config.autoRetry) {
                return await this.smartErrorRecovery(product, config, null, 'system_error', error);
            }
        } finally {
            // 防止重试时重复计数
            if (!product._isRetry) {
                this.monitorState.processedProducts++;
            }
        }
    }
    
    /**
     * 调用爬虫服务 - 使用标签页池版本
     */
    async callCrawlerService(productUrl) {
        let tabId = null;
        let checkInterval = null;
        let timeoutHandle = null;
        const performanceStart = Date.now();

        try {
            if (this.tabPoolManager) {
                tabId = await this.tabPoolManager.acquireTab();
                console.log(`🏊 从标签页池获取标签页 ${tabId} 用于监控: ${productUrl}`);
            } else {
                console.warn('⚠️ 标签页池不可用，降级到创建新标签页');
                const newTab = await chrome.tabs.create({ url: 'about:blank', active: false });
                tabId = newTab.id;
            }

            await new Promise((resolve, reject) => {
                chrome.tabs.update(tabId, { url: productUrl }, (updatedTab) => {
                    if (chrome.runtime.lastError) {
                        reject(new Error('导航失败: ' + chrome.runtime.lastError.message));
                    } else {
                        console.log(`🧭 标签页 ${tabId} 开始导航到: ${productUrl}`);
                        resolve(updatedTab);
                    }
                });
            });

            const result = await new Promise((resolve, reject) => {
                let isResolved = false;
                let tabUpdateListener = null;
                let pauseCheckInterval = null;
                const normalizedTargetUrl = productUrl.split('?')[0].split('#')[0];

                const cleanup = () => {
                    if (checkInterval) {
                        clearInterval(checkInterval);
                        checkInterval = null;
                    }
                    if (timeoutHandle) {
                        clearTimeout(timeoutHandle);
                        timeoutHandle = null;
                    }
                    if (tabUpdateListener) {
                        chrome.tabs.onUpdated.removeListener(tabUpdateListener);
                        tabUpdateListener = null;
                    }
                    if (pauseCheckInterval) {
                        clearInterval(pauseCheckInterval);
                        pauseCheckInterval = null;
                    }
                };

                tabUpdateListener = (tabIdChanged, changeInfo, tab) => {
                    if (isResolved || tabIdChanged !== tabId) return;

                    if (changeInfo.status === 'complete' && tab.url) {
                        console.log(`🔄 标签页 ${tabId} 状态更新: ${tab.status}, URL: ${tab.url}`);

                        if (tab.url.includes(normalizedTargetUrl)) {
                            cleanup();
                            console.log(`🔍 标签页 ${tabId} 导航并加载完成，当前URL: ${tab.url}`);
                            console.log(`🔍 目标URL: ${productUrl}`);

                            (async () => {
                                if (isResolved) return;
                                try {
                                    const response = window.safeTabMessage ?
                                        await window.safeTabMessage(tabId, { action: 'extractData' }, { timeout: 12000, retries: 1 }) :
                                        await new Promise((msgResolve, msgReject) => {
                                            chrome.tabs.sendMessage(tabId, { action: 'extractData' }, (msgResponse) => {
                                                if (chrome.runtime.lastError) {
                                                    msgReject(new Error(chrome.runtime.lastError.message));
                                                } else {
                                                    msgResolve(msgResponse);
                                                }
                                            });
                                        });

                                    if (!isResolved) {
                                        isResolved = true;
                                        console.log(`✅ 标签页 ${tabId} 数据提取成功`);
                                        resolve(response);
                                    }
                                } catch (error) {
                                    if (!isResolved) {
                                        isResolved = true;
                                        console.error(`❌ 标签页 ${tabId} 数据提取失败:`, error);
                                        reject(new Error(error.message || '数据提取失败'));
                                    }
                                }
                            })();
                        } else {
                            console.log(`⚠️ 标签页 ${tabId} 加载完成但URL不匹配:
                                当前URL: ${tab.url}
                                预期URL: ${productUrl}`);
                        }
                    }
                };

                chrome.tabs.onUpdated.addListener(tabUpdateListener);

                pauseCheckInterval = setInterval(() => {
                    if (isResolved) return;
                    if (this.monitorState?.isPaused) {
                        isResolved = true;
                        cleanup();
                        resolve({
                            paused: true,
                            message: '页面加载期间任务被暂停'
                        });
                    }
                }, 2000);

                const dynamicTimeout = this.calculateDynamicTimeout('pageLoad');
                console.log(`🕒 设置动态超时: ${Math.round(dynamicTimeout / 1000)}秒`);
                timeoutHandle = setTimeout(() => {
                    if (!isResolved) {
                        isResolved = true;
                        cleanup();
                        reject(new Error(`标签页 ${tabId} 处理超时 (${Math.round(dynamicTimeout / 1000)}秒)`));
                    }
                }, dynamicTimeout);
            });

            const processingTime = Date.now() - performanceStart;
            const performanceData = {
                success: !!result.success,
                processingTime,
                url: productUrl
            };

            if (this.tabPoolManager) {
                this.tabPoolManager.releaseTab(tabId, performanceData);
                console.log(`🔄 标签页 ${tabId} 已释放回池 (耗时: ${processingTime}ms)`);
            } else {
                try {
                    await chrome.tabs.remove(tabId);
                } catch (error) {
                    console.warn(`关闭标签页 ${tabId} 失败:`, error.message);
                }
            }

            return result;

        } catch (error) {
            const processingTime = Date.now() - performanceStart;
            const performanceData = {
                success: false,
                processingTime,
                error: error.message,
                url: productUrl
            };

            if (tabId) {
                if (this.tabPoolManager) {
                    this.tabPoolManager.releaseTab(tabId, performanceData);
                    console.log(`🔄 标签页 ${tabId} 因错误释放回池: ${error.message}`);
                } else {
                    try {
                        await chrome.tabs.remove(tabId);
                    } catch (removeError) {
                        console.warn(`关闭标签页 ${tabId} 失败:`, removeError.message);
                    }
                }
            }

            if (checkInterval) {
                clearInterval(checkInterval);
            }
            if (timeoutHandle) {
                clearTimeout(timeoutHandle);
            }

            throw error;
        }
    }

    /**
     * 打开使用说明
     */
    openUserGuide() {
        this.ensureGuideElements();
        if (!this.guideOverlay) return;
        console.log('🔎 打开使用说明');
        this.renderUserGuideContent();
        this.guideOverlay.classList.remove('hidden');
    }

    /**
     * 关闭使用说明
     */
    closeUserGuide() {
        if (!this.guideOverlay) return;
        this.guideOverlay.classList.add('hidden');
    }

    /**
     * 渲染使用说明内容（占位文案）
     */
    renderUserGuideContent() {
        if (!this.guideContentEl || this.guideContentInitialized) return;

        const sections = [
            {
                icon: '📥',
                title: '数据导入',
                items: [
                    '手动输入商品链接并点击“开始提取”即可保存到当前分类。',
                    '批量模式支持粘贴多行链接或上传 Excel，记得先选择分类。',
                    '导入成功后可在“数据管理”查看最新记录。'
                ]
            },
            {
                icon: '📡',
                title: '数据监控',
                items: [
                    '在“批量监控”区域勾选需要监控的分类并设置间隔/并发。',
                    '点击开始后系统会自动轮询提取并更新时间序列。',
                    '监控进度、暂停与停止按钮均在同一区域。'
                ]
            },
            {
                icon: '🚨',
                title: '异常检测',
                items: [
                    '设置好销量、营收、价格等阈值后启用检测。',
                    '检测完成会列出异常商品，可导出或跳转管理器查看。',
                    '阈值和检测策略可随时调整。'
                ]
            },
            {
                icon: '📊',
                title: '数据管理器',
                items: [
                    '点击“打开数据管理器”进入完整后台视图。',
                    '可查看所有分类、导出数据、批量操作、查看时间序列。',
                    '更多详细说明可稍后由你补充。'
                ]
            }
        ];

        const content = sections.map(section => `
            <div class="guide-section">
                <h3>${section.icon} ${section.title}</h3>
                <ul>
                    ${section.items.map(item => `<li>${item}</li>`).join('')}
                </ul>
            </div>
        `).join('');

        this.guideContentEl.innerHTML = content;
        this.guideContentInitialized = true;
    }

    /**
     * 确保指南元素已初始化
     */
    ensureGuideElements() {
        if (!this.guideOverlay || !this.guideContentEl) {
            this.guideOverlay = document.getElementById('userGuideOverlay');
            this.guideContentEl = document.getElementById('guideContent');
        }

        if (!this.guideOverlay || !this.guideContentEl || this.guideEventsBound) {
            return;
        }

        const closeGuideBtn = document.getElementById('closeGuideBtn');
        closeGuideBtn?.addEventListener('click', () => this.closeUserGuide());

        this.guideOverlay.addEventListener('click', (event) => {
            if (event.target === this.guideOverlay) {
                this.closeUserGuide();
            }
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                this.closeUserGuide();
            }
        });

        this.guideEventsBound = true;
    }

    /**
     * 清空数据占位逻辑
     */
    handleClearAllData() {
        if (!confirm('⚠️ 确定要清空所有本地数据吗？此操作不可恢复！')) {
            return;
        }

        if (!confirm('再次确认：这将删除所有分类、商品数据和历史记录！')) {
            return;
        }

        this.showNotification('数据清空功能将在后续版本中开放，可前往数据管理器操作。', 'warning');
    }

    /**
     * 导出数据占位逻辑
     */
    handleExportAllData() {
        this.showNotification('请在数据管理器中使用导出功能，当前侧边栏不支持导出。', 'info');
    }

    /**
     * 直接异常检测备用绑定
     */
    setupDirectAnomalyDetectionFallback() {
        setTimeout(() => {
            const runBtn = document.getElementById('easyRunDetection');
            if (!runBtn) {
                console.warn('⚠️ 未找到异常检测按钮');
                return;
            }

            const handler = async () => {
                console.log('🚀 触发直接异常检测');
                try {
                    if (this.easyAnomalyManager && typeof this.easyAnomalyManager.runDetection === 'function') {
                        await this.easyAnomalyManager.runDetection();
                        return;
                    }

                    if (window.xiaohongShuMonitor?.easyAnomalyManager?.runDetection) {
                        await window.xiaohongShuMonitor.easyAnomalyManager.runDetection();
                        return;
                    }

                    if (window.EasyAnomalyManager && window.LocalDataManager && window.CategoryManager) {
                        const tempManager = new window.EasyAnomalyManager();
                        const localDataManager = new window.LocalDataManager();
                        const categoryManager = new window.CategoryManager();

                        await localDataManager.init();
                        await categoryManager.init();
                        await tempManager.init(localDataManager, categoryManager);
                        await tempManager.runDetection();
                        return;
                    }

                    throw new Error('缺少异常检测组件');
                } catch (error) {
                    console.error('❌ 直接异常检测失败', error);
                    alert('异常检测失败：' + error.message);
                }
            };

            runBtn.removeEventListener('click', runBtn.directAnomalyHandler);
            runBtn.directAnomalyHandler = handler;
            runBtn.addEventListener('click', handler);
            console.log('✅ 直接异常检测备用事件绑定完成');
        }, 2000);
    }

    /**
     * 检测商品异常 - 使用重构后的异常检测器
     */
    async checkProductAnomaly(productId, newData) {
        try {
            // 简化版：基本的阈值检测
            if (this.easyAnomalyManager && this.easyAnomalyManager.detector) {
                const categoryMap = new Map(); // 简化版暂时使用空分类映射
                const anomaly = this.easyAnomalyManager.detector.detectSingleProduct(newData, categoryMap);

                if (anomaly) {
                    console.log(`⚠️ 检测到异常商品: ${anomaly.product_name}`);

                    // 更新数据库中的异常状态
                    await this.localDataManager.updateProductAnomalyStatus(productId, true);

                    return anomaly;
                } else {
                    // 如果没有异常，也要更新状态
                    await this.localDataManager.updateProductAnomalyStatus(productId, false);
                }
            }
            return null;
        } catch (error) {
            console.warn('简化异常检测失败:', error);
            return null;
        }
    }
    
    /**
     * 更新进度
     */
    updateProgress() {
        const progress = {
            totalProducts: this.monitorState.totalProducts,
            processedProducts: this.monitorState.processedProducts,
            successCount: this.monitorState.successCount,
            errorCount: this.monitorState.errorCount,
            skippedCount: this.monitorState.skippedCount,
            violationCount: this.monitorState.violationCount || 0,
            percentage: Math.floor((this.monitorState.processedProducts / this.monitorState.totalProducts) * 100)
        };

        // 调用UI进度回调
        if (this.monitorState.onProgress) {
            const violationText = this.monitorState.violationCount ? `, 违规:${this.monitorState.violationCount}` : '';
            const message = `正在监控商品 ${this.monitorState.processedProducts}/${this.monitorState.totalProducts} (成功:${this.monitorState.successCount}, 失败:${this.monitorState.errorCount}${violationText})`;
            this.monitorState.onProgress(this.monitorState.processedProducts, this.monitorState.totalProducts, message);
        }

        this.componentBridge.notifyMonitoringStatus('progress', progress);
    }
    
    /**
     * 完成监控
     */
    completeMonitoring() {
        if (this.monitorState) {
            this.monitorState.isRunning = false;
            this.monitorState.isPaused = false;
        }
        
        const duration = new Date() - this.monitorState.startTime;
        const minutes = Math.floor(duration / 60000);
        const seconds = Math.floor((duration % 60000) / 1000);
        
        const result = {
            totalProducts: this.monitorState.totalProducts,
            successCount: this.monitorState.successCount,
            errorCount: this.monitorState.errorCount,
            violationCount: this.monitorState.violationCount || 0,
            duration: { minutes, seconds }
        };

        console.log(`🎉 批量监控完成！耗时 ${minutes}分${seconds}秒`);
        const violationText = this.monitorState.violationCount ? `, 违规商品: ${this.monitorState.violationCount}` : '';
        console.log(`成功: ${this.monitorState.successCount}, 失败: ${this.monitorState.errorCount}${violationText}`);

        // 调用完成回调
        if (this.monitorState.onComplete) {
            this.monitorState.onComplete();
        }

        // 原有的监控状态通知
        this.componentBridge.notifyMonitoringStatus('completed', result);

        // 🆕 新增：通知数据管理器状态同步
        if (this.componentBridge) {
            this.componentBridge.notifyBatchMonitoringCompleted(result);
            console.log('📡 已发送批量监控完成状态同步通知');
        }
    }
    
    /**
     * 暂停/恢复监控
     */
    togglePause() {
        if (this.monitorState && this.monitorState.isRunning) {
            this.monitorState.isPaused = !this.monitorState.isPaused;
            
            const status = this.monitorState.isPaused ? 'paused' : 'progress';
            this.componentBridge.notifyMonitoringStatus(status, {
                isPaused: this.monitorState.isPaused
            });
            
            console.log(this.monitorState.isPaused ? '⏸️ 监控已暂停' : '▶️ 监控继续');
        }
    }
    
    /**
     * 停止监控
     */
    stop() {
        if (this.monitorState) {
            this.monitorState.isRunning = false;
            this.monitorState.isPaused = false;
        }
        
        this.componentBridge.notifyMonitoringStatus('stopped', {
            reason: 'user_stopped'
        });
        
        console.log('⏹️ 监控已停止');
    }
    
    /**
     * 运行异常检测
     */
    async runAnomalyDetection() {
        try {
            console.log('🔍 开始运行简化异常检测...');

            // 使用EasyAnomalyManager进行检测
            if (!this.easyAnomalyManager) {
                throw new Error('异常检测管理器未初始化');
            }

            const result = await this.easyAnomalyManager.detector.detectAllAnomalies();

            if (result.success) {
                console.log(`✅ 异常检测完成: 发现 ${result.anomaliesFound} 个异常`);

                // 原有的异常检测完成通知
                this.componentBridge.sendMessage('data-manager', 'ANOMALY_DETECTION_COMPLETED', {
                    success: true,
                    anomaliesFound: result.anomaliesFound,
                    checkedCount: result.checkedCount,
                    thresholds: result.thresholds,
                    timestamp: Date.now(),
                    batchResults: result.batchResults
                });

                // 🆕 新增：通知数据管理器状态同步
                this.componentBridge.notifyAnomalyDetectionUpdated(result.batchResults || []);
                console.log('📡 已发送异常检测完成状态同步通知');

                // 🔧 修复：通过主面板实例显示通知
                this.sidePanel.showNotification(
                    `异常检测完成: 检查了 ${result.checkedCount} 个商品，发现 ${result.anomaliesFound} 个异常`,
                    'success'
                );

            } else {
                console.error('❌ 异常检测失败:', result.error);

                // 发送失败通知
                this.componentBridge.sendMessage('data-manager', 'ANOMALY_DETECTION_FAILED', {
                    error: result.error,
                    timestamp: Date.now()
                });

                this.sidePanel.showNotification(`异常检测失败: ${result.error}`, 'error');
            }

            return result;

        } catch (error) {
            console.error('❌ 运行异常检测失败:', error);
            if (this.sidePanel) {
                this.sidePanel.showNotification(`异常检测失败: ${error.message}`, 'error');
            }
            throw error;
        }
    }
    
    /**
     * 获取监控状态
     */
    getMonitorState() {
        return this.monitorState;
    }
    
    /**
     * 暂停监控
     */
    pauseMonitoring() {
        if (this.monitorState && this.monitorState.isRunning) {
            this.monitorState.isPaused = true;
            console.log('⏸️ 批量监控已暂停');
            
            // 通知 data-manager 暂停状态
            if (this.componentBridge) {
                this.componentBridge.notifyMonitoringStatus('paused', {
                    processedProducts: this.monitorState.processedProducts,
                    totalProducts: this.monitorState.totalProducts
                });
            }
            
            return {
                success: true,
                message: '监控已暂停',
                status: 'paused'
            };
        }
        
        return {
            success: false,
            message: '没有正在运行的监控任务',
            status: 'idle'
        };
    }
    
    /**
     * 继续监控
     */
    resumeMonitoring() {
        if (this.monitorState && this.monitorState.isRunning && this.monitorState.isPaused) {
            this.monitorState.isPaused = false;
            console.log('▶️ 批量监控继续运行');
            
            // 通知 data-manager 继续状态
            if (this.componentBridge) {
                this.componentBridge.notifyMonitoringStatus('resumed', {
                    processedProducts: this.monitorState.processedProducts,
                    totalProducts: this.monitorState.totalProducts
                });
            }
            
            return {
                success: true,
                message: '监控已继续',
                status: 'running'
            };
        }
        
        return {
            success: false,
            message: '没有暂停的监控任务',
            status: this.monitorState ? (this.monitorState.isRunning ? 'running' : 'idle') : 'idle'
        };
    }
    
    /**
     * 停止监控
     */
    stopMonitoring() {
        if (this.monitorState && this.monitorState.isRunning) {
            this.monitorState.isRunning = false;
            this.monitorState.isPaused = false;
            console.log('⏹️ 批量监控已停止');
            
            // 通知 data-manager 停止状态
            if (this.componentBridge) {
                this.componentBridge.notifyMonitoringStatus('stopped', {
                    processedProducts: this.monitorState.processedProducts,
                    totalProducts: this.monitorState.totalProducts,
                    reason: 'user_stopped'
                });
            }
            
            return {
                success: true,
                message: '监控已停止',
                status: 'stopped'
            };
        }
        
        return {
            success: false,
            message: '没有正在运行的监控任务',
            status: 'idle'
        };
    }
    
    /**
     * 获取监控状态
     */
    getMonitoringStatus() {
        if (!this.monitorState) {
            return {
                status: 'idle',
                message: '监控服务就绪'
            };
        }
        
        if (!this.monitorState.isRunning) {
            return {
                status: 'idle',
                message: '监控服务就绪'
            };
        }
        
        if (this.monitorState.isPaused) {
            return {
                status: 'paused',
                message: `监控已暂停 (${this.monitorState.processedProducts}/${this.monitorState.totalProducts})`,
                progress: {
                    processed: this.monitorState.processedProducts,
                    total: this.monitorState.totalProducts,
                    percentage: Math.floor((this.monitorState.processedProducts / this.monitorState.totalProducts) * 100)
                }
            };
        }
        
        return {
            status: 'running',
            message: `正在监控 (${this.monitorState.processedProducts}/${this.monitorState.totalProducts})`,
            progress: {
                processed: this.monitorState.processedProducts,
                total: this.monitorState.totalProducts,
                percentage: Math.floor((this.monitorState.processedProducts / this.monitorState.totalProducts) * 100)
            }
        };
    }

    /**
     * 工具方法：等待指定毫秒
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * 计算智能间隔时间
     */
    calculateOptimalInterval() {
        const baseInterval = 500; // Level 1保守优化：基础间隔500ms
        const maxInterval = 10000;  // 最大间隔10秒
        const minInterval = 1000;   // 最小间隔1秒

        // 基于错误率调整
        const errorRate = this.monitorState.errorCount / (this.monitorState.totalProcessed || 1);
        const errorMultiplier = Math.min(1 + errorRate * 2, 3); // 错误率越高间隔越长，最多3倍

        // 基于当前负载调整
        const loadMultiplier = this.monitorState.isHighLoad ? 1.5 : 1;

        // 基于当前小时调整（避开高峰期）
        const currentHour = new Date().getHours();
        const peakHourMultiplier = (currentHour >= 19 && currentHour <= 23) ? 1.3 : 1;

        // 计算最终间隔
        const calculatedInterval = baseInterval * errorMultiplier * loadMultiplier * peakHourMultiplier;

        return Math.max(minInterval, Math.min(maxInterval, calculatedInterval));
    }

    /**
     * 计算动态超时时间
     */
    calculateDynamicTimeout(operation = 'default') {
        const timeouts = {
            default: { base: 8000, min: 5000, max: 15000 },
            pageLoad: { base: 8000, min: 6000, max: 15000 },
            dataExtraction: { base: 8000, min: 5000, max: 15000 },
            tabAcquisition: { base: 10000, min: 5000, max: 20000 }
        };

        const config = timeouts[operation] || timeouts.default;
        let timeout = config.base;

        // 基于错误率调整
        const errorRate = this.monitorState.errorCount / (this.monitorState.totalProcessed || 1);
        const errorMultiplier = Math.min(1 + errorRate, 2); // 错误率高时增加超时时间

        // 基于系统负载调整
        const loadMultiplier = this.monitorState.isHighLoad ? 1.5 : 1;

        // 基于当前小时调整（高峰期增加超时）
        const currentHour = new Date().getHours();
        const peakMultiplier = (currentHour >= 19 && currentHour <= 23) ? 1.3 : 1;

        // 计算最终超时时间
        timeout = timeout * errorMultiplier * loadMultiplier * peakMultiplier;

        return Math.max(config.min, Math.min(config.max, Math.round(timeout)));
    }

    /**
     * 异步流水线处理 - 替换Promise.allSettled阻塞
     */
    async processAsyncPipeline(batch, config) {
        // ✅ 使用固定并发数（不再动态调整）
        const concurrentLimit = this.monitorState.fixedConcurrent || 8; // 默认8个
        console.log(`🎯 本批次使用固定并发: ${concurrentLimit}`);
        const activePromises = new Set();
        let completed = 0;
        let index = 0;
        let consecutiveErrors = 0;

        const processNext = async () => {
            if (index >= batch.length) return;

            const product = batch[index++];
            const promise = this.processProductMonitor(product, config)
                .then(result => {
                    completed++;
                    consecutiveErrors = 0; // 重置连续错误计数
                    // 实时更新进度
                    this.updateProgress();
                    console.log(`✅ 商品 ${product.product_name || product.product_id} 处理完成 (${completed}/${batch.length})`);
                    return result;
                })
                .catch(error => {
                    completed++;
                    consecutiveErrors++; // 增加连续错误计数
                    console.error(`❌ 商品 ${product.product_name || product.product_id} 处理失败:`, error);

                    // ✅ 保持固定并发，不因错误降速
                    // 移除了动态降低并发的逻辑，失败商品会自动重试

                    // 即使失败也更新进度
                    this.updateProgress();
                    return { error: error.message };
                })
                .finally(() => {
                    activePromises.delete(promise);
                    // 启动下一个处理
                    if (index < batch.length) {
                        processNext();
                    }
                });

            activePromises.add(promise);
            return promise;
        };

        // 启动初始并发
        const initialPromises = [];
        for (let i = 0; i < concurrentLimit && i < batch.length; i++) {
            initialPromises.push(processNext());
        }

        // 等待所有任务完成 - 修复死循环问题
        let maxWaitTime = 300000; // 5分钟超时保护
        const startTime = Date.now();

        while (activePromises.size > 0 || completed < batch.length) {
            // 超时保护
            if (Date.now() - startTime > maxWaitTime) {
                console.warn('⚠️ 批处理超时，强制结束');
                break;
            }

            if (activePromises.size > 0) {
                try {
                    // 加入超时机制防止Promise永不解决
                    const timeoutPromise = new Promise((_, reject) =>
                        setTimeout(() => reject(new Error('单个Promise超时')), 30000)
                    );
                    await Promise.race([Promise.race(activePromises), timeoutPromise]);
                } catch (error) {
                    console.warn('⚠️ Promise处理异常:', error.message);
                    // 清理异常Promise
                    activePromises.clear();
                    break;
                }
            }

            // 防止死循环，但不阻塞
            await this.sleep(50);
        }

        console.log(`🎯 批次处理完成: ${completed}/${batch.length} 件商品`);
    }

    /**
     * 智能错误恢复机制 - Phase 2 优化
     */
    async smartErrorRecovery(product, config, response, errorType, originalError) {
        // 获取产品专属错误计数器
        const productId = product.product_id || product.id;
        if (!this.monitorState.productErrorCount) {
            this.monitorState.productErrorCount = new Map();
        }

        const productErrorCount = this.monitorState.productErrorCount.get(productId) || 0;
        const maxRetries = this.calculateMaxRetries(errorType, productErrorCount);

        if (productErrorCount >= maxRetries) {
            console.warn(`❌ ${product.product_name || productId} 达到最大重试次数 (${maxRetries})，跳过处理`);
            return null;
        }

        // 更新产品错误计数
        this.monitorState.productErrorCount.set(productId, productErrorCount + 1);

        // 根据错误类型选择恢复策略
        const recoveryStrategy = this.selectRecoveryStrategy(errorType, productErrorCount, originalError);
        console.log(`🔧 ${product.product_name || productId} 执行恢复策略: ${recoveryStrategy.name} (第${productErrorCount + 1}次重试)`);

        // 执行恢复动作
        await this.executeRecoveryActions(recoveryStrategy, product);

        // 等待恢复间隔
        const retryDelay = this.calculateRetryDelay(errorType, productErrorCount, recoveryStrategy);
        if (retryDelay > 0) {
            console.log(`⏳ 等待 ${Math.round(retryDelay/1000)}秒 后重试...`);
            await this.sleep(retryDelay);
        }

        // 递归重试 - 标记为重试防止重复计数
        const retryProduct = { ...product, _isRetry: true };
        return await this.processProductMonitor(retryProduct, config);
    }

    /**
     * 计算最大重试次数
     */
    calculateMaxRetries(errorType, currentRetries) {
        const baseRetries = {
            'extraction_failed': 2,  // 提取失败：2次重试
            'system_error': 3,       // 系统错误：3次重试
            'network_error': 4,      // 网络错误：4次重试
            'timeout_error': 2       // 超时错误：2次重试
        };

        // 基于系统负载动态调整
        const loadMultiplier = this.monitorState.isHighLoad ? 0.5 : 1;
        return Math.max(1, Math.floor((baseRetries[errorType] || 2) * loadMultiplier));
    }

    /**
     * 选择恢复策略
     */
    selectRecoveryStrategy(errorType, retryCount, originalError) {
        const strategies = {
            extraction_failed: [
                { name: '轻量重试', actions: ['clear_cache'] },
                { name: '强制刷新', actions: ['refresh_tab', 'clear_cache'] }
            ],
            system_error: [
                { name: '标准重试', actions: ['delay'] },
                { name: '池重置', actions: ['reset_tab_pool', 'delay'] },
                { name: '降级模式', actions: ['single_thread', 'delay'] }
            ],
            network_error: [
                { name: '快速重试', actions: ['short_delay'] },
                { name: '网络恢复', actions: ['check_network', 'delay'] },
                { name: '长时等待', actions: ['long_delay'] }
            ],
            timeout_error: [
                { name: '扩展超时', actions: ['extend_timeout'] },
                { name: '分段处理', actions: ['split_request', 'delay'] }
            ]
        };

        const errorStrategies = strategies[errorType] || strategies.system_error;
        const strategyIndex = Math.min(retryCount, errorStrategies.length - 1);
        return errorStrategies[strategyIndex];
    }

    /**
     * 执行恢复动作
     */
    async executeRecoveryActions(strategy, product) {
        for (const action of strategy.actions) {
            try {
                switch (action) {
                    case 'clear_cache':
                        // 清理可能的缓存
                        break;
                    case 'refresh_tab':
                        // 刷新标签页
                        console.log('🔄 执行标签页刷新恢复动作');
                        break;
                    case 'reset_tab_pool':
                        // 重置标签页池（如果可用）
                        if (this.tabPoolManager) {
                            console.log('🔄 执行标签页池重置恢复动作');
                            await this.tabPoolManager.performHealthCheck();
                        }
                        break;
                    case 'single_thread':
                        // 降级到单线程模式
                        console.log('🔄 降级到单线程处理模式');
                        this.monitorState.isHighLoad = true;
                        break;
                    case 'check_network':
                        // 网络连接检查
                        console.log('🔄 执行网络连接检查');
                        break;
                    case 'extend_timeout':
                        // 扩展超时时间
                        console.log('🔄 扩展超时时间');
                        break;
                    default:
                        break;
                }
            } catch (actionError) {
                console.warn(`⚠️ 恢复动作 ${action} 执行失败:`, actionError);
            }
        }
    }

    /**
     * 计算重试延迟
     */
    calculateRetryDelay(errorType, retryCount, strategy) {
        const baseDelays = {
            short_delay: 1000,   // 1秒
            delay: 3000,         // 3秒
            long_delay: 8000     // 8秒
        };

        // 检查策略中是否包含延迟动作
        const hasDelay = strategy.actions.some(action => action.includes('delay'));
        if (!hasDelay) return 0;

        const delayAction = strategy.actions.find(action => action.includes('delay')) || 'delay';
        let baseDelay = baseDelays[delayAction] || baseDelays.delay;

        // 指数退避，但有上限
        const backoffMultiplier = Math.min(Math.pow(1.5, retryCount), 4);
        return Math.min(baseDelay * backoffMultiplier, 15000); // 最多15秒
    }

    /**
     * 内存优化管理器 - Phase 3 优化
     */
    initializeMemoryOptimization() {
        // 启动内存监控
        this.memoryMonitorInterval = setInterval(() => {
            this.performMemoryOptimization();
        }, 30000); // 每30秒检查一次

        console.log('🧠 内存优化管理器已启动');
    }

    /**
     * 执行内存优化
     */
    async performMemoryOptimization() {
        try {
            // 检查内存使用情况
            const memoryInfo = await this.getMemoryInfo();

            // 清理过期数据
            this.cleanupExpiredData();

            // 优化数据结构
            this.optimizeDataStructures();

            // 如果内存使用过高，执行深度清理
            if (memoryInfo.usagePercent > 80) {
                await this.performDeepMemoryCleanup();
            }

            console.log(`🧠 内存优化完成 - 使用率: ${memoryInfo.usagePercent.toFixed(1)}%`);

        } catch (error) {
            console.warn('⚠️ 内存优化执行失败:', error);
        }
    }

    /**
     * 获取内存信息
     */
    async getMemoryInfo() {
        try {
            if ('memory' in performance) {
                const memInfo = performance.memory;
                return {
                    used: memInfo.usedJSHeapSize,
                    total: memInfo.totalJSHeapSize,
                    limit: memInfo.jsHeapSizeLimit,
                    usagePercent: (memInfo.usedJSHeapSize / memInfo.jsHeapSizeLimit) * 100
                };
            }
        } catch (error) {
            console.warn('⚠️ 无法获取内存信息:', error);
        }

        // 降级返回模拟数据
        return { used: 0, total: 0, limit: 0, usagePercent: 50 };
    }

    /**
     * 清理过期数据
     */
    cleanupExpiredData() {
        const now = Date.now();
        const maxAge = 300000; // 5分钟

        // 清理过期的性能统计
        if (this.monitorState.productErrorCount) {
            for (const [productId, count] of this.monitorState.productErrorCount.entries()) {
                // 如果错误计数长时间未更新，清理它
                if (count === 0) {
                    this.monitorState.productErrorCount.delete(productId);
                }
            }
        }

        // 清理标签页池的过期历史数据
        if (this.tabPoolManager && this.tabPoolManager.poolUsageHistory) {
            const cutoffTime = now - maxAge;
            this.tabPoolManager.poolUsageHistory = this.tabPoolManager.poolUsageHistory.filter(
                record => record.timestamp > cutoffTime
            );
        }

        // 清理标签页性能统计中的过期数据
        if (this.tabPoolManager && this.tabPoolManager.tabPerformanceStats) {
            for (const [tabId, stats] of this.tabPoolManager.tabPerformanceStats.entries()) {
                if (now - stats.lastUsed > maxAge) {
                    this.tabPoolManager.tabPerformanceStats.delete(tabId);
                }
            }
        }

        console.log('🗑️ 过期数据清理完成');
    }

    /**
     * 优化数据结构
     */
    optimizeDataStructures() {
        // 限制历史数据大小
        if (this.tabPoolManager && this.tabPoolManager.poolUsageHistory) {
            const maxHistorySize = 100;
            if (this.tabPoolManager.poolUsageHistory.length > maxHistorySize) {
                this.tabPoolManager.poolUsageHistory = this.tabPoolManager.poolUsageHistory.slice(-maxHistorySize);
            }
        }

        // 优化错误计数器
        if (this.monitorState.productErrorCount) {
            const maxErrorEntries = 1000;
            if (this.monitorState.productErrorCount.size > maxErrorEntries) {
                // 删除最旧的条目
                const entries = Array.from(this.monitorState.productErrorCount.entries());
                entries.slice(0, entries.length - maxErrorEntries).forEach(([key]) => {
                    this.monitorState.productErrorCount.delete(key);
                });
            }
        }

        console.log('📊 数据结构优化完成');
    }

    /**
     * 深度内存清理
     */
    async performDeepMemoryCleanup() {
        console.log('🧹 执行深度内存清理...');

        // 强制垃圾回收（如果支持）
        if ('gc' in window && typeof window.gc === 'function') {
            try {
                window.gc();
                console.log('♻️ 强制垃圾回收完成');
            } catch (error) {
                console.warn('⚠️ 强制垃圾回收失败:', error);
            }
        }

        // 重置非关键状态
        this.resetNonCriticalState();

        // 压缩标签页池
        if (this.tabPoolManager) {
            await this.tabPoolManager.performPoolShrinking();
        }

        // 通知系统进入内存节约模式
        this.monitorState.isMemoryConstrained = true;
        setTimeout(() => {
            this.monitorState.isMemoryConstrained = false;
        }, 60000); // 1分钟后退出内存节约模式

        console.log('🧹 深度内存清理完成');
    }

    /**
     * 重置非关键状态
     */
    resetNonCriticalState() {
        // 清空缓存数据
        if (this.monitorState.cache) {
            this.monitorState.cache.clear();
        }

        // 重置性能统计但保留关键指标
        const criticalStats = {
            totalProcessed: this.monitorState.totalProcessed,
            errorCount: this.monitorState.errorCount,
            isRunning: this.monitorState.isRunning,
            isPaused: this.monitorState.isPaused
        };

        Object.keys(this.monitorState).forEach(key => {
            if (!criticalStats.hasOwnProperty(key) && key !== 'productErrorCount') {
                delete this.monitorState[key];
            }
        });

        // 恢复关键状态
        Object.assign(this.monitorState, criticalStats);

        console.log('🔄 非关键状态重置完成');
    }

    /**
     * 计算最优并发度 - Phase 3 优化
     */
    calculateOptimalConcurrency(batchSize) {
        const baseConcurrency = Math.min(batchSize, 15); // Level 1保守优化：基础并发度，最多15个

        // 系统状态因子
        let systemFactor = 1;

        // 基于内存状态调整
        if (this.monitorState.isMemoryConstrained) {
            systemFactor *= 0.5; // 内存受限时减少并发
        }

        // 基于系统负载调整
        if (this.monitorState.isHighLoad) {
            systemFactor *= 0.6; // 高负载时减少并发
        }

        // 基于错误率调整
        const errorRate = this.monitorState.errorCount / (this.monitorState.totalProcessed || 1);
        if (errorRate > 0.1) { // 错误率超过10%
            systemFactor *= 0.7;
        }

        // 基于标签页池状态调整
        if (this.tabPoolManager) {
            const poolStatus = this.tabPoolManager.getPoolStatus();
            const utilization = poolStatus.busy / poolStatus.total;

            if (utilization > 0.8) { // 池利用率过高
                systemFactor *= 0.8;
            } else if (utilization < 0.3) { // 池利用率很低，可以增加并发
                systemFactor *= 1.2;
            }

            // 考虑队列长度
            if (poolStatus.queue > 3) {
                systemFactor *= 0.5; // 队列过长时显著降低并发
            }
        }

        // 时间因子（高峰期降低并发）
        const currentHour = new Date().getHours();
        if (currentHour >= 19 && currentHour <= 23) {
            systemFactor *= 0.8;
        }

        // 计算最终并发度
        const optimalConcurrency = Math.max(1, Math.min(
            Math.floor(baseConcurrency * systemFactor),
            15 // Level 1保守优化：硬性上限提升到15
        ));

        console.log(`🎯 计算最优并发度: ${optimalConcurrency} (基础: ${baseConcurrency}, 系统因子: ${systemFactor.toFixed(2)})`);

        return optimalConcurrency;
    }

    /**
     * 动态调整并发策略
     */
    adjustConcurrencyStrategy() {
        // 基于性能指标动态调整并发策略
        const recentPerformance = this.analyzeRecentPerformance();

        if (recentPerformance.successRate < 0.7) {
            // 成功率低，启用保守模式
            this.monitorState.concurrencyMode = 'conservative';
            this.monitorState.isHighLoad = true;
            console.log('📉 启用保守并发模式');
        } else if (recentPerformance.successRate > 0.9 && recentPerformance.avgResponseTime < 5000) {
            // 高成功率且响应快，可以启用积极模式
            this.monitorState.concurrencyMode = 'aggressive';
            this.monitorState.isHighLoad = false;
            console.log('📈 启用积极并发模式');
        } else {
            // 平衡模式
            this.monitorState.concurrencyMode = 'balanced';
            console.log('⚖️ 启用平衡并发模式');
        }
    }

    /**
     * 分析最近性能表现
     */
    analyzeRecentPerformance() {
        // 简化的性能分析
        const totalProcessed = this.monitorState.totalProcessed || 1;
        const errorCount = this.monitorState.errorCount || 0;
        const successRate = (totalProcessed - errorCount) / totalProcessed;

        return {
            successRate: successRate,
            avgResponseTime: 3000, // 简化为固定值，实际可以基于历史数据计算
            errorRate: errorCount / totalProcessed
        };
    }

    /**
     * 紧急停止方法 - 供StopCoordinator调用
     */
    async emergencyStop() {
        console.log('🚨 BatchMonitorService 执行紧急停止...');
        
        if (this.monitorState) {
            this.monitorState.isRunning = false;
            this.monitorState.isPaused = false;
        }

        // 🚀 Phase 3 优化: 停止内存优化监控
        if (this.memoryMonitorInterval) {
            clearInterval(this.memoryMonitorInterval);
            this.memoryMonitorInterval = null;
        }

        console.log('✅ BatchMonitorService 紧急停止完成');
    }
}

/**
 * 标签页池管理器 - 复用标签页提升性能
 * 优化版：实现懒加载模式，避免初始创建空白标签页
 */
class TabPoolManager {
    constructor(poolSize = 20) {
        this.poolSize = poolSize;
        this.availableTabs = new Set();
        this.busyTabs = new Map(); // tabId -> 使用信息
        this.isInitialized = false;
        this.createdTabs = new Set(); // 跟踪所有创建的标签页
        
        // 防崩溃保护机制
        this.maxSystemTabs = 40; // 系统最大标签页限制（支持多窗口运行）
        this.warningThreshold = 30; // 警告阈值
        this.healthCheckInterval = null;
        this.currentHealthCheckInterval = 15000; // 当前健康检查间隔
        this.lastHealthCheck = Date.now();
        this.lastCleanupTime = 0; // 上次清理时间
        this.cleanupCooldown = 30000; // 清理冷却时间30秒
        this.leakDetectionThreshold = 30000; // 30秒未释放视为泄漏
        
        // 智能池管理属性
        this.poolUsageHistory = []; // 池使用历史
        this.adaptivePoolSize = this.poolSize; // 自适应池大小
        this.maxAdaptiveSize = Math.min(this.poolSize * 2, 10); // 最大自适应大小
        this.minAdaptiveSize = 0; // 最小自适应大小，设为0以避免预创建标签页
        this.acquisitionQueue = []; // 获取队列
        this.tabPerformanceStats = new Map(); // 标签页性能统计
        this.lastResizeTime = 0; // 上次调整池大小时间
        this.resizeCooldown = 60000; // 池大小调整冷却时间60秒
        
        // 懒加载模式配置
        this.lazyLoadEnabled = true; // 启用懒加载模式
        this.initialPoolSize = 0; // 初始池大小为0，避免预创建标签页
        
        // 启动健康检查
        this.startHealthMonitoring();

        // 🚀 Phase 3 优化: 启动智能预分配监控
        this.startSmartPreallocation();

        console.log('🏊 标签页池管理器已初始化（懒加载模式）');
    }

    /**
     * 初始化标签页池 - 懒加载模式
     */
    async initialize() {
        console.log(`🏊 初始化标签页池 - 懒加载模式启用，初始池大小: ${this.initialPoolSize}`);
        
        // 懒加载模式下，不预先创建标签页，仅标记为已初始化
        this.isInitialized = true;
        
        // 如果配置了初始池大小，则创建指定数量的标签页
        if (this.initialPoolSize > 0) {
            const tabPromises = [];
            for (let i = 0; i < this.initialPoolSize; i++) {
                tabPromises.push(this.createTab(`初始化预创建 ${i + 1}/${this.initialPoolSize}`));
            }

            try {
                const tabs = await Promise.all(tabPromises);
                for (const tab of tabs) {
                    this.availableTabs.add(tab.id);
                    this.createdTabs.add(tab.id);
                }
                console.log(`✅ 标签页池初始化完成 - 预创建标签页: ${this.availableTabs.size}`);
            } catch (error) {
                console.error('⚠️ 标签页预创建失败:', error);
                // 不抛出错误，允许继续使用懒加载模式
            }
        } else {
            console.log('✅ 标签页池初始化完成 - 懒加载模式，无预创建标签页');
        }
    }

    /**
     * 创建新标签页 - 添加创建原因追踪
     */
    async createTab(reason = '未知原因') {
        console.log(`📋 创建新标签页 - 原因: ${reason}`);
        return await chrome.tabs.create({
            url: 'about:blank',
            active: false
        });
    }

    /**
     * 获取可用标签页 - 支持懒加载模式
     */
    async acquireTab() {
        if (!this.isInitialized) {
            await this.initialize();
        }

        // 系统级标签页数量检查
        await this.checkSystemResourcesBeforeAcquire();

        // 懒加载模式：如果没有可用标签页，按需创建
        if (this.lazyLoadEnabled && this.availableTabs.size === 0) {
            try {
                console.log('🔄 懒加载模式：按需创建新标签页用于爬取');
                const tab = await this.createTab('懒加载按需创建 - 用于数据爬取');
                this.availableTabs.add(tab.id);
                this.createdTabs.add(tab.id);
            } catch (error) {
                console.error('❌ 懒加载创建标签页失败:', error);
                // 继续尝试其他获取方式
            }
        }

        // 智能标签页分配策略
        const tabId = await this.intelligentTabAcquisition();
        
        if (tabId) {
            // 记录分配信息
            this.recordTabAcquisition(tabId);
            console.log(`📝 分配标签页 ${tabId} - 剩余可用: ${this.availableTabs.size}`);
            return tabId;
        }

        // 🚀 Phase 2 优化: 智能池扩容和预创建策略
        return await this.smartTabAcquisition();
    }

    /**
     * 系统资源检查
     */
    async checkSystemResourcesBeforeAcquire() {
        try {
            const allTabs = await chrome.tabs.query({});
            if (allTabs.length > this.maxSystemTabs) {
                console.warn(`⚠️ 系统标签页过多: ${allTabs.length}/${this.maxSystemTabs}`);
                await this.emergencyCleanup();
            }
        } catch (error) {
            console.warn('⚠️ 系统资源检查失败:', error);
        }
    }

    /**
     * 智能标签页获取策略
     */
    async intelligentTabAcquisition() {
        // 1. 检查是否有可用标签页
        if (this.availableTabs.size > 0) {
            // 负载均衡：选择性能最佳的标签页
            const bestTabId = this.selectBestAvailableTab();
            this.availableTabs.delete(bestTabId);
            this.busyTabs.set(bestTabId, {
                acquiredAt: Date.now(),
                inUse: true
            });
            return bestTabId;
        }

        // 2. 检查是否可以创建新标签页（自适应扩容）
        if (this.canExpandPool()) {
            try {
                const tab = await this.createTab('自适应扩容 - 爬取需求');
                this.createdTabs.add(tab.id);
                this.busyTabs.set(tab.id, {
                    acquiredAt: Date.now(),
                    inUse: true
                });
                console.log(`🚀 自适应扩容创建标签页 ${tab.id}`);
                return tab.id;
            } catch (error) {
                console.warn('⚠️ 自适应扩容失败:', error);
            }
        }

        return null; // 无法立即获取
    }

    /**
     * 选择性能最佳的可用标签页
     */
    selectBestAvailableTab() {
        if (this.availableTabs.size === 1) {
            return this.availableTabs.values().next().value;
        }

        let bestTabId = null;
        let bestScore = -1;

        for (const tabId of this.availableTabs) {
            const stats = this.tabPerformanceStats.get(tabId);
            const score = this.calculateTabScore(tabId, stats);
            
            if (score > bestScore) {
                bestScore = score;
                bestTabId = tabId;
            }
        }

        return bestTabId || this.availableTabs.values().next().value;
    }

    /**
     * 计算标签页评分（越高越好）
     */
    calculateTabScore(tabId, stats) {
        if (!stats) return 50; // 新标签页默认中等评分

        let score = 50; // 基础分
        
        // 基于历史性能评分
        if (stats.successCount > 0) {
            const successRate = stats.successCount / (stats.successCount + stats.errorCount);
            score += successRate * 30; // 成功率加分 (0-30分)
        }
        
        // 基于平均处理时间评分
        if (stats.avgProcessingTime > 0) {
            const timeScore = Math.max(0, 20 - (stats.avgProcessingTime / 1000) * 2); // 处理时间越短分数越高
            score += timeScore;
        }
        
        // 基于最近使用时间评分
        const timeSinceLastUse = Date.now() - (stats.lastUsed || 0);
        if (timeSinceLastUse < 30000) { // 30秒内使用过
            score += 10; // 热标签页加分
        }

        return Math.max(0, Math.min(100, score));
    }

    /**
     * 检查是否可以扩容池
     */
    canExpandPool() {
        const currentSize = this.availableTabs.size + this.busyTabs.size;
        return (
            currentSize < this.adaptivePoolSize &&
            this.createdTabs.size < this.maxSystemTabs &&
            currentSize < this.maxAdaptiveSize
        );
    }

    /**
     * 智能标签页获取策略 - Phase 2 优化
     */
    async smartTabAcquisition() {
        // 检查是否可以扩容
        const canExpand = this.createdTabs.size < this.maxAdaptiveSize &&
                         this.acquisitionQueue.length > 0 &&
                         Date.now() - this.lastResizeTime > 5000; // 5秒冷却

        if (canExpand) {
            console.log(`🚀 智能扩容：当前 ${this.createdTabs.size}/${this.maxAdaptiveSize}，队列长度 ${this.acquisitionQueue.length}`);

            try {
                // 创建新标签页
                const newTab = await chrome.tabs.create({
                    url: 'about:blank',
                    active: false
                });

                this.createdTabs.add(newTab.id);
                this.availableTabs.add(newTab.id);
                this.lastResizeTime = Date.now();

                console.log(`✅ 智能扩容成功：新建标签页 ${newTab.id}`);

                // 立即分配新创建的标签页
                this.availableTabs.delete(newTab.id);
                this.busyTabs.set(newTab.id, {
                    acquiredAt: Date.now(),
                    inUse: true
                });

                this.recordTabAcquisition(newTab.id);
                return newTab.id;

            } catch (error) {
                console.warn('⚠️ 智能扩容失败，回退到队列等待:', error);
            }
        }

        // 如果不能扩容或扩容失败，使用优化的队列等待
        return await this.optimizedQueueWaiting();
    }

    /**
     * 优化的队列等待机制
     */
    async optimizedQueueWaiting() {
        // 如果队列太长，给出警告和预估等待时间
        if (this.acquisitionQueue.length > 5) {
            const avgWaitTime = this.calculateAverageWaitTime();
            console.warn(`⚠️ 队列较长 (${this.acquisitionQueue.length})，预估等待 ${Math.round(avgWaitTime/1000)}秒`);
        }

        return this.queuedTabAcquisition();
    }

    /**
     * 计算平均等待时间
     */
    calculateAverageWaitTime() {
        if (this.poolUsageHistory.length < 2) return 10000; // 默认10秒

        const recentHistory = this.poolUsageHistory.slice(-10);
        const avgReleaseInterval = recentHistory.length > 1 ?
            (recentHistory[recentHistory.length-1].timestamp - recentHistory[0].timestamp) / recentHistory.length :
            10000;

        return Math.min(avgReleaseInterval * this.acquisitionQueue.length, 30000); // 最多30秒
    }

    /**
     * 智能预分配监控 - Phase 3 优化
     */
    startSmartPreallocation() {
        this.preallocationInterval = setInterval(() => {
            this.executeSmartPreallocation();
        }, 10000); // 每10秒检查一次

        console.log('🧠 智能预分配监控已启动');
    }

    /**
     * 执行智能预分配逻辑
     */
    async executeSmartPreallocation() {
        try {
            // 分析使用模式
            const usagePattern = this.analyzeUsagePattern();

            // 预测未来需求
            const predictedDemand = this.predictFutureDemand(usagePattern);

            // 检查是否需要预分配
            if (this.shouldPreallocate(predictedDemand, usagePattern)) {
                await this.performPreallocation(predictedDemand);
            }

            // 检查是否需要收缩池大小
            if (this.shouldShrinkPool(usagePattern)) {
                await this.performPoolShrinking();
            }

        } catch (error) {
            console.warn('⚠️ 智能预分配执行失败:', error);
        }
    }

    /**
     * 分析使用模式
     */
    analyzeUsagePattern() {
        const recentHistory = this.poolUsageHistory.slice(-20); // 最近20个数据点
        if (recentHistory.length < 5) {
            return { trend: 'unknown', avgUtilization: 0.5, peakUsage: 0 };
        }

        // 计算利用率趋势
        const utilizations = recentHistory.map(h =>
            h.busyCount / (h.busyCount + h.availableCount) || 0
        );

        const avgUtilization = utilizations.reduce((a, b) => a + b, 0) / utilizations.length;
        const peakUsage = Math.max(...recentHistory.map(h => h.busyCount));

        // 分析趋势
        const recent = utilizations.slice(-5);
        const earlier = utilizations.slice(-10, -5);
        const recentAvg = recent.reduce((a, b) => a + b, 0) / recent.length;
        const earlierAvg = earlier.reduce((a, b) => a + b, 0) / earlier.length;

        let trend = 'stable';
        if (recentAvg > earlierAvg + 0.1) trend = 'increasing';
        else if (recentAvg < earlierAvg - 0.1) trend = 'decreasing';

        return { trend, avgUtilization, peakUsage };
    }

    /**
     * 预测未来需求
     */
    predictFutureDemand(usagePattern) {
        let baseDemand = Math.ceil(usagePattern.peakUsage * 1.2); // 基于峰值的120%

        // 根据趋势调整
        if (usagePattern.trend === 'increasing') {
            baseDemand = Math.ceil(baseDemand * 1.3);
        } else if (usagePattern.trend === 'decreasing') {
            baseDemand = Math.ceil(baseDemand * 0.8);
        }

        // 考虑时间因素（高峰期预测）
        const currentHour = new Date().getHours();
        const isPeakHour = (currentHour >= 19 && currentHour <= 23);
        if (isPeakHour) {
            baseDemand = Math.ceil(baseDemand * 1.4);
        }

        return Math.max(this.poolSize, Math.min(baseDemand, this.maxAdaptiveSize));
    }

    /**
     * 检查是否需要预分配
     */
    shouldPreallocate(predictedDemand, usagePattern) {
        const currentTotal = this.createdTabs.size;
        const availableCount = this.availableTabs.size;
        const queueLength = this.acquisitionQueue.length;

        // 条件1: 队列有等待且可用标签页不足
        const hasQueuePressure = queueLength > 0 && availableCount < 2;

        // 条件2: 预测需求超过当前池大小
        const demandExceedsCapacity = predictedDemand > currentTotal;

        // 条件3: 利用率过高
        const highUtilization = usagePattern.avgUtilization > 0.8;

        // 条件4: 冷却时间已过
        const cooldownExpired = Date.now() - this.lastResizeTime > 15000; // 15秒冷却

        return (hasQueuePressure || demandExceedsCapacity || highUtilization) &&
               cooldownExpired &&
               currentTotal < this.maxAdaptiveSize;
    }

    /**
     * 执行预分配
     */
    async performPreallocation(predictedDemand) {
        const currentTotal = this.createdTabs.size;
        const needToCreate = Math.min(predictedDemand - currentTotal, 2); // 每次最多创建2个

        if (needToCreate <= 0) return;

        console.log(`🧠 智能预分配: 当前${currentTotal}个，预测需求${predictedDemand}个，将创建${needToCreate}个标签页`);

        for (let i = 0; i < needToCreate; i++) {
            try {
                const newTab = await chrome.tabs.create({
                    url: 'about:blank',
                    active: false
                });

                this.createdTabs.add(newTab.id);
                this.availableTabs.add(newTab.id);

                console.log(`✨ 预分配标签页 ${newTab.id} 创建成功`);

            } catch (error) {
                console.warn('⚠️ 预分配标签页创建失败:', error);
                break; // 如果失败，停止创建更多
            }
        }

        this.lastResizeTime = Date.now();
    }

    /**
     * 检查是否需要收缩池
     */
    shouldShrinkPool(usagePattern) {
        const currentTotal = this.createdTabs.size;
        const availableCount = this.availableTabs.size;

        // 条件1: 利用率很低
        const lowUtilization = usagePattern.avgUtilization < 0.3;

        // 条件2: 可用标签页过多
        const tooManyAvailable = availableCount > this.poolSize && availableCount > 3;

        // 条件3: 趋势下降
        const decliningTrend = usagePattern.trend === 'decreasing';

        // 条件4: 超过最小池大小
        const aboveMinSize = currentTotal > this.poolSize;

        // 条件5: 冷却时间已过
        const cooldownExpired = Date.now() - this.lastResizeTime > 30000; // 30秒冷却

        return lowUtilization && tooManyAvailable && decliningTrend && aboveMinSize && cooldownExpired;
    }

    /**
     * 执行池收缩
     */
    async performPoolShrinking() {
        const availableCount = this.availableTabs.size;
        const toRemove = Math.min(Math.floor(availableCount / 2), 2); // 每次最多移除2个

        if (toRemove <= 0) return;

        console.log(`🔻 智能收缩: 将移除${toRemove}个空闲标签页`);

        const tabsToRemove = Array.from(this.availableTabs).slice(0, toRemove);

        for (const tabId of tabsToRemove) {
            try {
                await chrome.tabs.remove(tabId);
                this.availableTabs.delete(tabId);
                this.createdTabs.delete(tabId);
                console.log(`🗑️ 收缩移除标签页 ${tabId}`);
            } catch (error) {
                console.warn(`⚠️ 移除标签页 ${tabId} 失败:`, error);
            }
        }

        this.lastResizeTime = Date.now();
    }

    /**
     * 队列等待机制
     */
    async queuedTabAcquisition() {
        return new Promise((resolve, reject) => {
            const request = {
                resolve,
                reject,
                timestamp: Date.now(),
                timeout: setTimeout(() => {
                    // 从队列中移除超时请求
                    const index = this.acquisitionQueue.indexOf(request);
                    if (index > -1) {
                        this.acquisitionQueue.splice(index, 1);
                    }
                    reject(new Error('获取标签页超时'));
                }, 30000) // 30秒超时
            };

            this.acquisitionQueue.push(request);
            console.log(`📋 加入获取队列，队列长度: ${this.acquisitionQueue.length}`);
        });
    }

    /**
     * 释放标签页回池
     */
    releaseTab(tabId, performanceData = null) {
        if (this.busyTabs.has(tabId)) {
            const acquireInfo = this.busyTabs.get(tabId);
            this.busyTabs.delete(tabId);
            
            // 更新性能统计
            this.updateTabPerformanceStats(tabId, acquireInfo, performanceData);
            
            // 处理等待队列
            if (this.acquisitionQueue.length > 0) {
                const request = this.acquisitionQueue.shift();
                clearTimeout(request.timeout);
                
                // 直接分配给等待中的请求
                this.busyTabs.set(tabId, {
                    acquiredAt: Date.now(),
                    inUse: true
                });
                
                this.recordTabAcquisition(tabId);
                console.log(`📋 从队列分配标签页 ${tabId} - 队列剩余: ${this.acquisitionQueue.length}`);
                request.resolve(tabId);
            } else {
                // 没有等待队列，标签页回到可用池
                this.availableTabs.add(tabId);
                console.log(`🔄 释放标签页 ${tabId} - 可用: ${this.availableTabs.size}`);
            }
            
            // 动态调整池大小
            this.adjustPoolSizeIfNeeded();
        }
    }

    /**
     * 更新标签页性能统计
     */
    updateTabPerformanceStats(tabId, acquireInfo, performanceData) {
        const stats = this.tabPerformanceStats.get(tabId) || {
            successCount: 0,
            errorCount: 0,
            totalProcessingTime: 0,
            avgProcessingTime: 0,
            lastUsed: 0,
            created: Date.now()
        };

        const processingTime = Date.now() - acquireInfo.acquiredAt;
        stats.totalProcessingTime += processingTime;
        stats.lastUsed = Date.now();

        if (performanceData) {
            if (performanceData.success) {
                stats.successCount++;
            } else {
                stats.errorCount++;
            }
        } else {
            // 没有明确的性能数据，假设成功
            stats.successCount++;
        }

        // 计算平均处理时间
        const totalOperations = stats.successCount + stats.errorCount;
        if (totalOperations > 0) {
            stats.avgProcessingTime = stats.totalProcessingTime / totalOperations;
        }

        this.tabPerformanceStats.set(tabId, stats);
    }

    /**
     * 记录标签页分配信息
     */
    recordTabAcquisition(tabId) {
        // 记录池使用历史
        this.poolUsageHistory.push({
            timestamp: Date.now(),
            availableCount: this.availableTabs.size,
            busyCount: this.busyTabs.size,
            queueLength: this.acquisitionQueue.length
        });
        
        // 保持历史记录在合理范围内
        if (this.poolUsageHistory.length > 100) {
            this.poolUsageHistory = this.poolUsageHistory.slice(-50);
        }
    }

    /**
     * 动态调整池大小
     */
    adjustPoolSizeIfNeeded() {
        const now = Date.now();
        
        // 冷却期检查
        if (now - this.lastResizeTime < this.resizeCooldown) {
            return;
        }

        // 分析最近的使用模式
        const recentUsage = this.analyzeRecentUsage();
        let newSize = this.adaptivePoolSize;

        // 根据使用模式调整池大小
        if (recentUsage.avgQueueLength > 2) {
            // 队列过长，需要扩容
            newSize = Math.min(this.adaptivePoolSize + 1, this.maxAdaptiveSize);
            console.log(`📈 队列压力大，扩容池大小: ${this.adaptivePoolSize} -> ${newSize}`);
        } else if (recentUsage.avgUtilization < 0.3 && this.adaptivePoolSize > this.minAdaptiveSize) {
            // 利用率过低，可以缩容
            newSize = Math.max(this.adaptivePoolSize - 1, this.minAdaptiveSize);
            console.log(`📉 利用率低，缩容池大小: ${this.adaptivePoolSize} -> ${newSize}`);
        }

        if (newSize !== this.adaptivePoolSize) {
            this.adaptivePoolSize = newSize;
            this.lastResizeTime = now;
        }
    }

    /**
     * 分析最近使用模式
     */
    analyzeRecentUsage() {
        const recentHistory = this.poolUsageHistory.slice(-20); // 最近20条记录
        
        if (recentHistory.length === 0) {
            return { avgUtilization: 0.5, avgQueueLength: 0 };
        }

        let totalUtilization = 0;
        let totalQueueLength = 0;

        for (const record of recentHistory) {
            const totalTabs = record.availableCount + record.busyCount;
            const utilization = totalTabs > 0 ? record.busyCount / totalTabs : 0;
            totalUtilization += utilization;
            totalQueueLength += record.queueLength;
        }

        return {
            avgUtilization: totalUtilization / recentHistory.length,
            avgQueueLength: totalQueueLength / recentHistory.length
        };
    }

    /**
     * 启动健康监控
     */
    startHealthMonitoring() {
        this.healthCheckInterval = setInterval(() => {
            this.performHealthCheck();
        }, this.currentHealthCheckInterval);
        
        console.log('🏥 标签页池健康监控已启动');
    }

    /**
     * 执行健康检查
     */
    async performHealthCheck() {
        try {
            // 检查标签页状态
            await this.checkTabHealth();
            
            // 检测泄漏
            this.detectTabLeaks();
            
            // 清理无效标签页
            await this.cleanupInvalidTabs();
            
        } catch (error) {
            console.error('❌ 标签页池健康检查失败:', error);
        }
    }

    /**
     * 检查标签页健康状态
     */
    async checkTabHealth() {
        const allTabIds = new Set([...this.availableTabs, ...this.busyTabs.keys()]);
        const invalidTabs = [];

        for (const tabId of allTabIds) {
            try {
                await chrome.tabs.get(tabId);
            } catch (error) {
                invalidTabs.push(tabId);
            }
        }

        // 清理无效标签页
        for (const tabId of invalidTabs) {
            this.cleanupTab(tabId);
        }

        if (invalidTabs.length > 0) {
            console.log(`🧹 清理了 ${invalidTabs.length} 个无效标签页`);
        }
    }

    /**
     * 检测标签页泄漏
     */
    detectTabLeaks() {
        const now = Date.now();
        const leakedTabs = [];

        for (const [tabId, info] of this.busyTabs) {
            if (now - info.acquiredAt > this.leakDetectionThreshold) {
                leakedTabs.push(tabId);
                console.warn(`⚠️ 检测到标签页泄漏: ${tabId} (占用 ${Math.round((now - info.acquiredAt) / 1000)}s)`);
            }
        }

        // 强制回收泄漏的标签页
        for (const tabId of leakedTabs) {
            this.releaseTab(tabId, { success: false, leaked: true });
        }
    }

    /**
     * 清理无效标签页
     */
    async cleanupInvalidTabs() {
        const validTabIds = new Set();
        
        try {
            const allTabs = await chrome.tabs.query({});
            allTabs.forEach(tab => validTabIds.add(tab.id));
        } catch (error) {
            console.warn('⚠️ 无法获取系统标签页列表:', error);
            return;
        }

        // 清理不存在的标签页
        const toCleanup = [];
        for (const tabId of this.createdTabs) {
            if (!validTabIds.has(tabId)) {
                toCleanup.push(tabId);
            }
        }

        for (const tabId of toCleanup) {
            this.cleanupTab(tabId);
        }
    }

    /**
     * 清理单个标签页记录
     */
    cleanupTab(tabId) {
        this.availableTabs.delete(tabId);
        this.busyTabs.delete(tabId);
        this.createdTabs.delete(tabId);
        this.tabPerformanceStats.delete(tabId);
    }

    /**
     * 紧急清理
     */
    async emergencyCleanup() {
        const now = Date.now();
        if (now - this.lastCleanupTime < this.cleanupCooldown) {
            return;
        }

        console.log('🚨 执行紧急清理...');
        this.lastCleanupTime = now;

        // 关闭性能最差的标签页
        const sortedTabs = Array.from(this.availableTabs).sort((a, b) => {
            const aStats = this.tabPerformanceStats.get(a);
            const bStats = this.tabPerformanceStats.get(b);
            return this.calculateTabScore(a, aStats) - this.calculateTabScore(b, bStats);
        });

        const toClose = Math.min(3, sortedTabs.length);
        for (let i = 0; i < toClose; i++) {
            const tabId = sortedTabs[i];
            try {
                await chrome.tabs.remove(tabId);
                this.cleanupTab(tabId);
            } catch (error) {
                console.warn(`⚠️ 关闭标签页 ${tabId} 失败:`, error);
            }
        }

        console.log(`🧹 紧急清理完成，关闭了 ${toClose} 个标签页`);
    }

    /**
     * 紧急停止
     */
    async emergencyStop() {
        console.log('🚨 TabPoolManager 执行紧急停止...');
        
        // 停止健康检查
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
            this.healthCheckInterval = null;
        }

        // 🚀 Phase 3 优化: 停止智能预分配监控
        if (this.preallocationInterval) {
            clearInterval(this.preallocationInterval);
            this.preallocationInterval = null;
        }

        // 清理所有队列
        const queueCount = this.acquisitionQueue.length;
        this.acquisitionQueue.forEach(request => {
            clearTimeout(request.timeout);
            request.reject(new Error('系统紧急停止'));
        });
        this.acquisitionQueue = [];

        // 关闭所有创建的标签页
        const closePromises = [];
        for (const tabId of this.createdTabs) {
            closePromises.push(
                chrome.tabs.remove(tabId).catch(error => {
                    console.warn(`关闭标签页 ${tabId} 失败:`, error.message);
                })
            );
        }

        await Promise.allSettled(closePromises);

        // 清理状态
        this.availableTabs.clear();
        this.busyTabs.clear();
        this.createdTabs.clear();
        this.isInitialized = false;

        console.log(`✅ TabPoolManager 紧急停止完成，关闭了 ${closePromises.length} 个标签页`);
    }

    /**
     * 获取池状态
     */
    getPoolStatus() {
        return {
            available: this.availableTabs.size,
            busy: this.busyTabs.size,
            total: this.createdTabs.size,
            queue: this.acquisitionQueue.length,
            adaptiveSize: this.adaptivePoolSize
        };
    }
}

/**
 * 停止协调器 - 管理多组件统一停止
 * 从git历史恢复的正确实现
 */
class StopCoordinator {
    constructor() {
        this.isGlobalStopping = false;
        this.registeredComponents = new Map();
        this.stopPromises = [];
        
        console.log('🎯 停止协调器已初始化');
    }
    
    /**
     * 注册需要协调停止的组件
     */
    register(name, component) {
        this.registeredComponents.set(name, component);
        console.log(`📝 注册组件: ${name}`);
    }
    
    /**
     * 统一紧急停止所有组件
     */
    async emergencyStopAll(reason = '手动触发') {
        if (this.isGlobalStopping) {
            console.log('⚠️ 全局停止已在进行中...');
            return;
        }
        
        console.log(`🚨 启动全局紧急停止: ${reason}`);
        this.isGlobalStopping = true;
        
        const stopPromises = [];
        
        // 并行停止所有组件
        for (const [name, component] of this.registeredComponents) {
            if (component && typeof component.emergencyStop === 'function') {
                console.log(`🛑 停止组件: ${name}`);
                stopPromises.push(
                    this.safeStop(name, component).catch(error => {
                        console.error(`❌ 组件 ${name} 停止失败:`, error);
                        return { name, error };
                    })
                );
            }
        }
        
        // 等待所有组件停止完成
        const results = await Promise.allSettled(stopPromises);
        
        // 统计结果
        const failed = results.filter(r => r.status === 'rejected' || r.value?.error);
        if (failed.length > 0) {
            console.warn(`⚠️ ${failed.length} 个组件停止时出现问题`);
        }
        
        console.log('✅ 全局紧急停止完成');
        this.isGlobalStopping = false;
    }
    
    /**
     * 安全停止单个组件
     */
    async safeStop(name, component) {
        const timeout = new Promise((_, reject) => 
            setTimeout(() => reject(new Error(`${name} 停止超时`)), 5000)
        );
        
        try {
            await Promise.race([component.emergencyStop(), timeout]);
            console.log(`✅ 组件 ${name} 停止成功`);
        } catch (error) {
            console.error(`❌ 组件 ${name} 停止失败:`, error.message);
            
            // 强制停止标志
            if (component.isProcessing !== undefined) {
                component.isProcessing = false;
            }
            throw error;
        }
    }
    
    /**
     * 检查是否正在全局停止
     */
    isGlobalStop() {
        return this.isGlobalStopping;
    }
    
    /**
     * 重置状态（用于重新开始）
     */
    reset() {
        this.isGlobalStopping = false;
        console.log('🔄 停止协调器状态已重置');
    }
}

// 初始化应用
window.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 DOM加载完成，初始化应用...');

    // 检查必要环境 - ultrathink: 允许在非Chrome扩展环境下运行
    if (typeof chrome === 'undefined' || !chrome.storage) {
        console.error('❌ Chrome扩展环境不可用');
        // ultrathink: 不要直接return，继续初始化以支持本地测试
        console.log('🔧 继续在本地环境下初始化...');
    }

    try {
        // 创建应用实例
        window.xiaohongshuApp = new XiaohongshuSidePanel();

        // 创建全局监控实例以便HTML中的onclick事件可以访问
        window.xiaohongShuMonitor = window.xiaohongshuApp;

        console.log('✅ 应用实例创建成功');
        console.log('🌐 全局引用已暴露:', {
            xiaohongshuApp: !!window.xiaohongshuApp,
            xiaohongShuMonitor: !!window.xiaohongShuMonitor
        });

        // 🆕 初始化运存配置
        initSystemMemoryConfig();

    } catch (error) {
        console.error('❌ 应用初始化失败:', error);

        // ultrathink: 提供简化的备用初始化
        console.log('🔧 尝试简化初始化...');
        window.xiaohongShuMonitor = {
            showNotification: (message, type) => console.log(`📢 [${type.toUpperCase()}] ${message}`)
        };
    }
});

/**
 * 全选异常检测分类
 */
window.selectAllAnomalyCategories = function() {
    try {
        if (window.xiaohongShuMonitor?.categorySelectorManager) {
            const allCategories = window.xiaohongShuMonitor.categorySelectorManager.getAllCategoryIds();
            window.xiaohongShuMonitor.categorySelectorManager.setSelection(allCategories);
            window.xiaohongShuMonitor.updateAnomalyCategorySelectionSummary();
        }
    } catch (error) {
        console.error('❌ 全选异常检测分类失败:', error);
    }
};

/**
 * 清空异常检测分类选择
 */
window.clearAnomalyCategories = function() {
    try {
        if (window.xiaohongShuMonitor?.categorySelectorManager) {
            window.xiaohongShuMonitor.categorySelectorManager.setSelection([]);
            window.xiaohongShuMonitor.updateAnomalyCategorySelectionSummary();
        }
    } catch (error) {
        console.error('❌ 清空异常检测分类选择失败:', error);
    }
};

/**
 * 获取选中的异常检测分类ID列表
 */
window.getSelectedAnomalyCategories = function() {
    try {
        if (window.xiaohongShuMonitor?.categorySelectorManager) {
            return window.xiaohongShuMonitor.categorySelectorManager.getSelectedIds();
        }
        return [];
    } catch (error) {
        console.error('❌ 获取选中的异常检测分类失败:', error);
        return [];
    }
};

/**
 * 🆕 初始化系统运存配置
 * - 加载保存的配置
 * - 绑定事件监听器
 * - 更新UI显示
 */
function initSystemMemoryConfig() {
    console.log('🔧 初始化系统运存配置...');

    const selectElement = document.getElementById('systemMemoryConfig');

    if (!selectElement) {
        console.warn('⚠️ 运存配置元素未找到');
        return;
    }

    // 加载保存的配置
    const savedConfig = localStorage.getItem('systemMemoryConfig') || 'auto';
    selectElement.value = savedConfig;

    // 绑定事件监听器
    selectElement.addEventListener('change', function(e) {
        const selectedValue = e.target.value;

        // 保存到localStorage
        localStorage.setItem('systemMemoryConfig', selectedValue);
        console.log(`💾 运存配置已保存: ${selectedValue}`);

        // 显示保存成功提示
        if (window.xiaohongShuMonitor && window.xiaohongShuMonitor.showNotification) {
            const modeText = getMemoryModeText(selectedValue);
            window.xiaohongShuMonitor.showNotification(
                `运存配置已更新: ${modeText}`,
                'success'
            );
        }
    });

    console.log('✅ 运存配置初始化完成');
}

/**
 * 根据配置值获取显示文本
 */
function getMemoryModeText(configValue) {
    const modeMap = {
        'auto': '自动检测模式',
        '8': '8GB - 保守模式 (5个并发)',
        '16': '16GB - 均衡模式 (8个并发)',
        '32': '32GB - 性能模式 (11个并发)',
        '64': '32GB以上 - 极限模式 (15个并发)'
    };
    return modeMap[configValue] || '未知模式';
}

// 导出供其他模块使用
if (typeof window !== 'undefined') {
    window.XiaohongshuSidePanel = XiaohongshuSidePanel;
    window.InputModeManager = InputModeManager;
    window.BatchInputAdapter = BatchInputAdapter;
    window.ExcelProcessor = ExcelProcessor;
}
