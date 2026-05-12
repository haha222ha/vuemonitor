/**
 * 直接流程对比工具 - 精确定位手动测试vs真实上传差异
 * ultrathink 终极调试工具
 */

console.log('🎯 直接流程对比工具 - 开始精确定位差异');
console.log('═'.repeat(80));

// 测试数据 - 用户的真实Excel结构
const testExcelData = [
    ['商品ID', '商品名称', '商品价格', '商品销量', '好评人数', '加购件数', '近3个月销量', '店铺名称', '店铺粉丝数', '店铺销量', '商品链接', '采集时间'],
    ['test123', '测试商品', '¥5.88', '1597', '98%好评', '400+人加购', '3个月内600+人购买', '测试店铺', '5万粉丝', '4461', 'https://test.com', '2025-08-13']
];

/**
 * 测试1：手动调用processSheetData
 */
function testManualProcessSheetData() {
    console.log('\n🧪 测试1：手动调用processSheetData');
    console.log('─'.repeat(60));

    if (typeof ExcelProcessor === 'undefined') {
        console.log('❌ ExcelProcessor不可用');
        return null;
    }

    const processor = new ExcelProcessor();

    try {
        const result = processor.processSheetData(testExcelData);

        console.log('✅ 手动processSheetData成功');
        console.log('基本信息:', {
            success: result.success,
            validProducts: result.validProducts,
            totalRows: result.totalRows
        });

        if (result.products && result.products.length > 0) {
            const product = result.products[0];
            const additionalDataFields = {
                good_reviews: product.good_reviews,
                goodReviews: product.goodReviews,
                cart_count: product.cart_count,
                cartCount: product.cartCount,
                recent_sales: product.recent_sales,
                recentSales: product.recentSales,
                store_followers: product.store_followers,
                storeFollowers: product.storeFollowers
            };

            console.log('additional_data字段:', additionalDataFields);
            return additionalDataFields;
        }
    } catch (error) {
        console.error('❌ 手动processSheetData失败:', error);
        return null;
    }
}

/**
 * 测试2：模拟真实Excel文件并调用parseFile
 */
async function testSimulatedExcelUpload() {
    console.log('\n🧪 测试2：模拟Excel文件上传');
    console.log('─'.repeat(60));

    // 创建模拟Excel文件
    const mockExcelFile = createMockExcelFile();

    if (!mockExcelFile) {
        console.log('❌ 无法创建模拟Excel文件');
        return null;
    }

    if (typeof ExcelProcessor === 'undefined') {
        console.log('❌ ExcelProcessor不可用');
        return null;
    }

    const processor = new ExcelProcessor();

    try {
        const result = await processor.parseFile(mockExcelFile);

        console.log('✅ 模拟parseFile成功');
        console.log('基本信息:', {
            success: result.success,
            validProducts: result.validProducts,
            totalRows: result.totalRows
        });

        if (result.products && result.products.length > 0) {
            const product = result.products[0];
            const additionalDataFields = {
                good_reviews: product.good_reviews,
                goodReviews: product.goodReviews,
                cart_count: product.cart_count,
                cartCount: product.cartCount,
                recent_sales: product.recent_sales,
                recentSales: product.recentSales,
                store_followers: product.store_followers,
                storeFollowers: product.storeFollowers
            };

            console.log('additional_data字段:', additionalDataFields);
            return additionalDataFields;
        }
    } catch (error) {
        console.error('❌ 模拟parseFile失败:', error);
        return null;
    }
}

/**
 * 创建模拟Excel文件
 */
function createMockExcelFile() {
    try {
        // 使用XLSX库创建Excel文件
        if (typeof XLSX === 'undefined') {
            console.log('❌ XLSX库不可用');
            return null;
        }

        const wb = XLSX.utils.book_new();
        const ws = XLSX.utils.aoa_to_sheet(testExcelData);
        XLSX.utils.book_append_sheet(wb, ws, 'Sheet1');

        // 转换为ArrayBuffer
        const excelBuffer = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });

        // 创建File对象
        const file = new File([excelBuffer], 'test.xlsx', {
            type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        });

        console.log('✅ 模拟Excel文件创建成功:', {
            name: file.name,
            size: file.size,
            type: file.type
        });

        return file;
    } catch (error) {
        console.error('❌ 创建模拟Excel文件失败:', error);
        return null;
    }
}

/**
 * 对比两种方法的结果
 */
function compareResults(manualResult, uploadResult) {
    console.log('\n📊 对比分析');
    console.log('═'.repeat(80));

    if (!manualResult || !uploadResult) {
        console.log('⚠️ 缺少对比数据');
        if (!manualResult) console.log('  - 缺少手动测试结果');
        if (!uploadResult) console.log('  - 缺少上传测试结果');
        return;
    }

    const fields = ['good_reviews', 'goodReviews', 'cart_count', 'cartCount', 'recent_sales', 'recentSales', 'store_followers', 'storeFollowers'];

    let allMatch = true;
    const differences = [];

    console.log('字段对比详情:');
    fields.forEach(field => {
        const manualValue = manualResult[field];
        const uploadValue = uploadResult[field];
        const matches = manualValue === uploadValue;

        console.log(`  ${field}:`);
        console.log(`    手动: "${manualValue}" (${typeof manualValue})`);
        console.log(`    上传: "${uploadValue}" (${typeof uploadValue})`);
        console.log(`    ${matches ? '✅ 一致' : '❌ 不一致'}`);
        console.log('');

        if (!matches) {
            allMatch = false;
            differences.push({ field, manual: manualValue, upload: uploadValue });
        }
    });

    if (allMatch) {
        console.log('🎉 所有字段完全一致！');
        console.log('💡 问题可能在数据保存阶段，不在Excel解析阶段');
    } else {
        console.log('🚨 发现差异:');
        differences.forEach((diff, index) => {
            console.log(`  ${index + 1}. ${diff.field}: 手动="${diff.manual}" 上传="${diff.upload}"`);
        });

        console.log('\n💡 差异可能原因:');
        console.log('  1. parseFile和processSheetData使用不同的逻辑');
        console.log('  2. XLSX解析过程中数据发生变化');
        console.log('  3. 文件读取过程中编码问题');
        console.log('  4. 异步处理差异');
    }
}

/**
 * 运行完整对比测试
 */
async function runCompleteComparison() {
    console.log('🚀 运行完整对比测试');
    console.log('═'.repeat(80));

    // 测试1：手动调用
    const manualResult = testManualProcessSheetData();

    // 测试2：模拟文件上传
    const uploadResult = await testSimulatedExcelUpload();

    // 对比结果
    compareResults(manualResult, uploadResult);

    return { manualResult, uploadResult };
}

// 便捷函数
window.testManualFlow = testManualProcessSheetData;
window.testUploadFlow = testSimulatedExcelUpload;
window.runFlowComparison = runCompleteComparison;

console.log('\n💡 使用方法:');
console.log('   runFlowComparison() - 运行完整对比测试');
console.log('   testManualFlow() - 仅测试手动流程');
console.log('   testUploadFlow() - 仅测试上传流程');