/**
 * 简化Excel上传器 - 直接使用中文字段名，避免复杂映射
 * ultrathink 简化方案
 */

class SimpleExcelUploader {
    constructor() {
        this.supportedFormats = ['.xlsx', '.xls'];
    }

    /**
     * 简化的Excel上传处理
     */
    async handleSimpleExcelUpload(file, categoryId = 1) {
        try {
            console.log('🚀 [简化上传] 开始处理Excel文件:', file.name);

            // 1. 解析Excel文件
            const excelData = await this.parseExcelFile(file);
            console.log('📊 [简化上传] Excel解析完成:', {
                totalRows: excelData.length - 1,
                headers: excelData[0]
            });

            // 2. 转换为产品数据
            const products = this.convertToProducts(excelData);
            console.log('✅ [简化上传] 产品转换完成:', products.length, '个产品');

            // 3. 保存到数据库
            const saveResult = await this.saveToDatabase(products, categoryId);
            console.log('💾 [简化上传] 保存完成:', saveResult);

            return saveResult;

        } catch (error) {
            console.error('❌ [简化上传] 上传失败:', error);
            throw error;
        }
    }

    /**
     * 解析Excel文件
     */
    async parseExcelFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();

            reader.onload = (e) => {
                try {
                    const data = new Uint8Array(e.target.result);
                    const workbook = XLSX.read(data, { type: 'array' });
                    const firstSheetName = workbook.SheetNames[0];
                    const worksheet = workbook.Sheets[firstSheetName];
                    const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });

                    resolve(jsonData);
                } catch (error) {
                    reject(new Error('Excel解析失败: ' + error.message));
                }
            };

            reader.onerror = () => reject(new Error('文件读取失败'));
            reader.readAsArrayBuffer(file);
        });
    }

    /**
     * 转换为产品数据 - 直接使用中文字段名
     */
    convertToProducts(excelData) {
        const [headers, ...dataRows] = excelData;
        const products = [];

        console.log('📋 [简化上传] Excel标题行:', headers);

        // 查找关键字段的索引
        const fieldIndexes = {
            商品ID: headers.indexOf('商品ID'),
            商品名称: headers.indexOf('商品名称'),
            商品价格: headers.indexOf('商品价格'),
            商品销量: headers.indexOf('商品销量'),
            好评人数: headers.indexOf('好评人数'),
            加购件数: headers.indexOf('加购件数'),
            近3个月销量: headers.indexOf('近3个月销量'),
            店铺名称: headers.indexOf('店铺名称'),
            店铺粉丝数: headers.indexOf('店铺粉丝数'),
            店铺销量: headers.indexOf('店铺销量'),
            商品链接: headers.indexOf('商品链接'),
            采集时间: headers.indexOf('采集时间')
        };

        console.log('🔍 [简化上传] 字段索引映射:', fieldIndexes);

        // 转换每一行数据
        dataRows.forEach((row, index) => {
            try {
                // 检查必需字段
                const productUrl = row[fieldIndexes.商品链接];
                if (!productUrl) {
                    console.warn(`⚠️ [简化上传] 第${index + 2}行缺少商品链接，跳过`);
                    return;
                }

                // 构建产品对象 - 直接使用中文字段
                const product = {
                    // 基础字段
                    product_id: row[fieldIndexes.商品ID] || `产品_${Date.now()}_${index}`,
                    product_name: row[fieldIndexes.商品名称] || `商品_${index + 1}`,
                    product_url: productUrl,
                    product_price: this.parsePrice(row[fieldIndexes.商品价格]),
                    product_sales: this.parseSales(row[fieldIndexes.商品销量]),
                    store_name: row[fieldIndexes.店铺名称] || '',
                    store_sales: this.parseSales(row[fieldIndexes.店铺销量]),
                    extracted_at: row[fieldIndexes.采集时间] || new Date().toISOString(),

                    // 🎯 核心修复：additional_data直接使用中文字段值
                    additional_data: {
                        good_reviews: row[fieldIndexes.好评人数] || '',
                        cart_count: row[fieldIndexes.加购件数] || '',
                        recent_sales: row[fieldIndexes.近3个月销量] || '',
                        store_followers: row[fieldIndexes.店铺粉丝数] || ''
                    },

                    // 兼容字段
                    productName: row[fieldIndexes.商品名称] || `商品_${index + 1}`,
                    productUrl: productUrl,
                    storeName: row[fieldIndexes.店铺名称] || '',

                    // 标记来源
                    isFromExcel: true,
                    excelRowIndex: index + 2
                };

                // 调试第一个产品
                if (index === 0) {
                    console.log('🎯 [简化上传] 第一个产品数据:', product);
                    console.log('🎯 [简化上传] additional_data详情:', product.additional_data);
                }

                products.push(product);

            } catch (error) {
                console.error(`❌ [简化上传] 第${index + 2}行处理失败:`, error);
            }
        });

        return products;
    }

    /**
     * 保存到数据库
     */
    async saveToDatabase(products, categoryId) {
        // 检查数据管理器是否可用
        if (window.dataManagerApp && window.dataManagerApp.sharedDataService && window.dataManagerApp.sharedDataService.localDataManager) {
            const localDataManager = window.dataManagerApp.sharedDataService.localDataManager;
            return await localDataManager.batchSaveProductsWithDedup(products, categoryId);
        } else {
            // 如果在sidepanel，需要通过消息传递到data-manager
            return new Promise((resolve, reject) => {
                chrome.runtime.sendMessage({
                    action: 'saveProducts',
                    products: products,
                    categoryId: categoryId
                }, (response) => {
                    if (response.success) {
                        resolve(response.result);
                    } else {
                        reject(new Error(response.error));
                    }
                });
            });
        }
    }

    /**
     * 解析价格
     */
    parsePrice(priceStr) {
        if (!priceStr) return 0;
        const cleaned = priceStr.toString().replace(/[￥$¥,]/g, '');
        const price = parseFloat(cleaned);
        return isNaN(price) ? 0 : price;
    }

    /**
     * 解析销量
     */
    parseSales(salesStr) {
        if (!salesStr) return 0;
        const cleaned = salesStr.toString().replace(/[,+万千]/g, '');
        const sales = parseInt(cleaned);
        return isNaN(sales) ? 0 : sales;
    }
}

// 创建简化上传器实例
const simpleUploader = new SimpleExcelUploader();

/**
 * 替换原有的handleExcelUpload函数
 */
async function handleSimpleExcelUpload(file, categoryId = 1) {
    try {
        // 更新UI状态
        if (typeof updateUploadStatus === 'function') {
            updateUploadStatus('uploading', '正在处理Excel文件...');
        }

        // 使用简化上传器
        const result = await simpleUploader.handleSimpleExcelUpload(file, categoryId);

        // 更新UI状态
        if (typeof updateUploadStatus === 'function') {
            updateUploadStatus('success', `上传完成: ${result.success}个成功, ${result.failed}个失败`);
        }

        return result;

    } catch (error) {
        console.error('❌ [简化上传] 处理失败:', error);

        if (typeof updateUploadStatus === 'function') {
            updateUploadStatus('error', '上传失败: ' + error.message);
        }

        throw error;
    }
}

// 暴露到全局
window.SimpleExcelUploader = SimpleExcelUploader;
window.handleSimpleExcelUpload = handleSimpleExcelUpload;
window.simpleUploader = simpleUploader;

console.log('✅ [简化上传] 简化Excel上传器已加载');
console.log('💡 使用方法: handleSimpleExcelUpload(file, categoryId)');
console.log('🎯 特点: 直接使用中文字段名，避免复杂映射逻辑');