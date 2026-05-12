/**
 * Excel上传流程跟踪器 - 对比手动测试和真实上传的差异
 * ultrathink 专项调试工具
 */

class UploadFlowTracer {
    constructor() {
        this.traceData = {
            manualTest: null,
            realUpload: null,
            differences: []
        };
        this.isTracing = false;
    }

    /**
     * 启动上传流程跟踪
     */
    startTracing() {
        this.isTracing = true;
        this.traceData = {
            manualTest: null,
            realUpload: null,
            differences: []
        };

        console.log('🔍 [上传流程跟踪器] 启动');
        console.log('═'.repeat(80));
        console.log('💡 现在请执行以下操作：');
        console.log('1. 点击"开始导入"按钮上传Excel');
        console.log('2. 查看跟踪结果');

        this.interceptUploadFlow();
    }

    /**
     * 拦截上传流程
     */
    interceptUploadFlow() {
        // 拦截 ExcelProcessor.parseFile
        if (typeof ExcelProcessor !== 'undefined') {
            const processor = new ExcelProcessor();
            const originalParseFile = processor.parseFile.bind(processor);
            const originalProcessSheetData = processor.processSheetData.bind(processor);

            processor.parseFile = async (file) => {
                console.log('🎯 [跟踪] parseFile被调用:', {
                    fileName: file.name,
                    fileSize: file.size,
                    fileType: file.type
                });

                const result = await originalParseFile(file);

                console.log('🎯 [跟踪] parseFile结果:', {
                    success: result.success,
                    validProducts: result.validProducts,
                    totalRows: result.totalRows,
                    firstProductAdditionalData: result.products && result.products[0] ? {
                        good_reviews: result.products[0].good_reviews,
                        goodReviews: result.products[0].goodReviews,
                        cart_count: result.products[0].cart_count,
                        cartCount: result.products[0].cartCount,
                        recent_sales: result.products[0].recent_sales,
                        recentSales: result.products[0].recentSales,
                        store_followers: result.products[0].store_followers,
                        storeFollowers: result.products[0].storeFollowers
                    } : null
                });

                this.traceData.realUpload = {
                    step: 'parseFile',
                    result: result,
                    additionalDataFields: this.extractAdditionalDataFields(result.products)
                };

                return result;
            };

            processor.processSheetData = (jsonData) => {
                console.log('🎯 [跟踪] processSheetData被调用:', {
                    headers: jsonData[0],
                    dataRows: jsonData.length - 1,
                    sampleData: jsonData[1]
                });

                const result = originalProcessSheetData(jsonData);

                console.log('🎯 [跟踪] processSheetData结果:', {
                    success: result.success,
                    validProducts: result.validProducts,
                    firstProductFields: result.products && result.products[0] ? Object.keys(result.products[0]) : null
                });

                return result;
            };

            // 替换全局ExcelProcessor
            window.ExcelProcessor = function() {
                return processor;
            };
        }

        // 拦截 handleExcelUpload
        this.interceptHandleExcelUpload();
    }

    /**
     * 拦截handleExcelUpload函数
     */
    interceptHandleExcelUpload() {
        // 查找并拦截上传处理函数
        if (typeof handleExcelUpload !== 'undefined') {
            const originalHandleExcelUpload = handleExcelUpload;

            window.handleExcelUpload = async (file, batchId) => {
                console.log('🎯 [跟踪] handleExcelUpload被调用:', {
                    fileName: file.name,
                    batchId: batchId
                });

                const result = await originalHandleExcelUpload(file, batchId);

                console.log('🎯 [跟踪] handleExcelUpload结果:', result);

                return result;
            };
        }
    }

    /**
     * 提取additional_data字段
     */
    extractAdditionalDataFields(products) {
        if (!products || products.length === 0) return null;

        const firstProduct = products[0];
        return {
            good_reviews: firstProduct.good_reviews,
            goodReviews: firstProduct.goodReviews,
            cart_count: firstProduct.cart_count,
            cartCount: firstProduct.cartCount,
            recent_sales: firstProduct.recent_sales,
            recentSales: firstProduct.recentSales,
            store_followers: firstProduct.store_followers,
            storeFollowers: firstProduct.storeFollowers
        };
    }

    /**
     * 运行手动对比测试
     */
    runManualComparisonTest() {
        console.log('🧪 [跟踪器] 运行手动对比测试');
        console.log('─'.repeat(60));

        // 模拟用户的真实Excel数据
        const realExcelData = [
            ['商品ID', '商品名称', '商品价格', '商品销量', '好评人数', '加购件数', '近3个月销量', '店铺名称', '店铺粉丝数', '店铺销量', '商品链接', '采集时间'],
            ['test123', '测试商品', '¥5.88', '1597', '98%好评', '400+人加购', '3个月内600+人购买', '测试店铺', '5万粉丝', '4461', 'https://test.com', '2025-08-13']
        ];

        if (typeof ExcelProcessor !== 'undefined') {
            const processor = new ExcelProcessor();

            try {
                const result = processor.processSheetData(realExcelData);

                this.traceData.manualTest = {
                    step: 'processSheetData',
                    result: result,
                    additionalDataFields: this.extractAdditionalDataFields(result.products)
                };

                console.log('✅ 手动测试结果:', {
                    success: result.success,
                    validProducts: result.validProducts,
                    additionalDataFields: this.traceData.manualTest.additionalDataFields
                });

                return true;
            } catch (error) {
                console.error('❌ 手动测试失败:', error);
                return false;
            }
        } else {
            console.log('❌ ExcelProcessor不可用');
            return false;
        }
    }

    /**
     * 生成对比报告
     */
    generateComparisonReport() {
        console.log('\n📊 [上传流程对比报告]');
        console.log('═'.repeat(80));

        if (!this.traceData.manualTest) {
            console.log('⚠️ 缺少手动测试数据，先运行手动测试');
            return;
        }

        if (!this.traceData.realUpload) {
            console.log('⚠️ 缺少真实上传数据，请上传Excel文件');
            return;
        }

        // 对比additional_data字段
        console.log('🔍 additional_data字段对比:');
        console.log('─'.repeat(50));

        const manualFields = this.traceData.manualTest.additionalDataFields;
        const realFields = this.traceData.realUpload.additionalDataFields;

        const fields = ['good_reviews', 'goodReviews', 'cart_count', 'cartCount', 'recent_sales', 'recentSales', 'store_followers', 'storeFollowers'];

        fields.forEach(field => {
            const manualValue = manualFields ? manualFields[field] : 'N/A';
            const realValue = realFields ? realFields[field] : 'N/A';
            const matches = manualValue === realValue;

            console.log(`  ${field}:`);
            console.log(`    手动测试: ${manualValue}`);
            console.log(`    真实上传: ${realValue}`);
            console.log(`    ${matches ? '✅ 一致' : '❌ 不一致'}`);
            console.log('');

            if (!matches) {
                this.traceData.differences.push({
                    field: field,
                    manual: manualValue,
                    real: realValue
                });
            }
        });

        // 输出差异分析
        if (this.traceData.differences.length > 0) {
            console.log('🚨 发现的差异:');
            this.traceData.differences.forEach((diff, index) => {
                console.log(`  ${index + 1}. ${diff.field}: 手动="${diff.manual}" vs 真实="${diff.real}"`);
            });

            console.log('\n💡 可能的原因:');
            console.log('1. Excel文件解析流程不同');
            console.log('2. 字段映射逻辑差异');
            console.log('3. 数据处理管道差异');
            console.log('4. 版本不一致或缓存问题');
        } else {
            console.log('✅ 所有字段都一致，需要检查数据保存阶段');
        }
    }

    /**
     * 停止跟踪
     */
    stopTracing() {
        this.isTracing = false;
        this.generateComparisonReport();
    }
}

// 全局实例
let uploadFlowTracer = null;

// 便捷函数
function startUploadTracing() {
    if (uploadFlowTracer) {
        uploadFlowTracer.stopTracing();
    }

    uploadFlowTracer = new UploadFlowTracer();
    uploadFlowTracer.startTracing();

    // 运行手动对比测试
    uploadFlowTracer.runManualComparisonTest();

    return '🔍 上传流程跟踪已启动！现在请上传Excel文件...';
}

function stopUploadTracing() {
    if (uploadFlowTracer) {
        uploadFlowTracer.stopTracing();
        return '📊 上传流程跟踪已停止，对比报告已生成';
    } else {
        return '⚠️ 上传流程跟踪未启动';
    }
}

function runManualTest() {
    if (uploadFlowTracer) {
        return uploadFlowTracer.runManualComparisonTest();
    } else {
        uploadFlowTracer = new UploadFlowTracer();
        return uploadFlowTracer.runManualComparisonTest();
    }
}

// 暴露给全局使用
if (typeof window !== 'undefined') {
    window.UploadFlowTracer = UploadFlowTracer;
    window.startUploadTracing = startUploadTracing;
    window.stopUploadTracing = stopUploadTracing;
    window.runManualTest = runManualTest;
}

console.log('🔍 Excel上传流程跟踪器已加载');
console.log('💡 使用方法:');
console.log('   startUploadTracing() - 启动跟踪并运行手动测试');
console.log('   [点击"开始导入"上传Excel文件]');
console.log('   stopUploadTracing() - 停止跟踪并生成报告');
console.log('   runManualTest() - 仅运行手动测试');