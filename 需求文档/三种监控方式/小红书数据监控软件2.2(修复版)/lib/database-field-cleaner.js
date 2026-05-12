/**
 * 数据库字段清理模块
 * 用于清理重复和冗余的数据库字段
 */

class DatabaseFieldCleaner {
    constructor() {
        // 重复字段映射表：redundant_field -> standard_field
        this.redundantFieldMappings = {
            'price': 'product_price',
            'sales': 'product_sales',
            'storeName': 'store_name',
            'storeSales': 'store_sales',
            'title': 'product_name',
            'url': 'product_url',
            'last_crawled_at': 'extracted_at',
            'lastUpdate': 'extracted_at'
        };

        // 无价值字段列表（完全冗余）
        this.redundantFields = Object.keys(this.redundantFieldMappings);

        console.log('🧹 数据库字段清理器已初始化');
    }

    /**
     * 分析产品记录的字段冗余情况
     * @param {Array} products - 产品记录数组
     * @returns {Object} 分析结果
     */
    analyzeFieldRedundancy(products) {
        const analysis = {
            totalProducts: products.length,
            totalFields: 0,
            redundantFields: [],
            redundancyStats: {},
            cleanupSuggestions: []
        };

        if (products.length === 0) {
            return analysis;
        }

        // 收集所有字段
        const allFields = new Set();
        const fieldUsage = {};

        products.forEach(product => {
            Object.keys(product).forEach(field => {
                allFields.add(field);
                fieldUsage[field] = (fieldUsage[field] || 0) + 1;
            });
        });

        analysis.totalFields = allFields.size;

        // 分析每个重复字段对
        for (const [redundant, standard] of Object.entries(this.redundantFieldMappings)) {
            const redundantUsage = fieldUsage[redundant] || 0;
            const standardUsage = fieldUsage[standard] || 0;

            if (redundantUsage > 0) {
                const redundancyRate = standardUsage > 0 ?
                    (Math.min(redundantUsage, standardUsage) / Math.max(redundantUsage, standardUsage)) * 100 : 0;

                analysis.redundancyStats[redundant] = {
                    redundantCount: redundantUsage,
                    standardCount: standardUsage,
                    redundancyRate: redundancyRate,
                    recommendation: this.getRecommendation(redundancyRate, redundantUsage, standardUsage)
                };

                if (redundancyRate > 50 || standardUsage === 0) {
                    analysis.redundantFields.push(redundant);
                    analysis.cleanupSuggestions.push({
                        action: standardUsage > 0 ? 'merge_and_delete' : 'rename',
                        redundantField: redundant,
                        standardField: standard,
                        affectedRecords: redundantUsage
                    });
                }
            }
        }

        console.log('📊 字段冗余分析完成:', {
            总字段数: analysis.totalFields,
            冗余字段数: analysis.redundantFields.length,
            建议清理: analysis.cleanupSuggestions.length
        });

        return analysis;
    }

    /**
     * 获取字段处理建议
     */
    getRecommendation(redundancyRate, redundantUsage, standardUsage) {
        if (standardUsage === 0) {
            return '重命名为标准字段名';
        } else if (redundancyRate > 80) {
            return '删除重复字段';
        } else if (redundancyRate > 50) {
            return '合并后删除';
        } else {
            return '保留（数据不重复）';
        }
    }

    /**
     * 清理单个产品记录的重复字段
     * @param {Object} product - 产品记录
     * @returns {Object} 清理后的产品记录
     */
    cleanProductFields(product) {
        const cleaned = { ...product };
        const changes = [];

        for (const [redundant, standard] of Object.entries(this.redundantFieldMappings)) {
            if (cleaned.hasOwnProperty(redundant)) {
                // 合并数据：如果标准字段不存在或为空，使用重复字段的值
                if (!cleaned.hasOwnProperty(standard) ||
                    cleaned[standard] === null ||
                    cleaned[standard] === undefined ||
                    cleaned[standard] === '') {

                    cleaned[standard] = cleaned[redundant];
                    changes.push(`${redundant} → ${standard}`);
                } else {
                    // 如果两个字段都有值，检查是否相同
                    if (cleaned[redundant] !== cleaned[standard]) {
                        console.warn(`⚠️ 字段值冲突: ${redundant}="${cleaned[redundant]}" vs ${standard}="${cleaned[standard]}"`);
                        // 保留标准字段的值
                    }
                    changes.push(`删除 ${redundant}`);
                }

                // 删除重复字段
                delete cleaned[redundant];
            }
        }

        return {
            product: cleaned,
            changes: changes,
            fieldReduction: Object.keys(product).length - Object.keys(cleaned).length
        };
    }

    /**
     * 批量清理产品记录
     * @param {Array} products - 产品记录数组
     * @returns {Object} 清理结果
     */
    batchCleanProducts(products) {
        const results = {
            totalProcessed: 0,
            cleanedProducts: [],
            skippedProducts: [],
            errors: [],
            totalFieldsRemoved: 0,
            summary: {
                originalFieldCount: 0,
                cleanedFieldCount: 0,
                storageReduction: 0
            }
        };

        console.log(`🧹 开始批量清理 ${products.length} 个产品记录...`);

        products.forEach((product, index) => {
            try {
                const originalFieldCount = Object.keys(product).length;
                results.summary.originalFieldCount += originalFieldCount;

                // 检查是否需要清理
                const needsCleaning = this.redundantFields.some(field =>
                    product.hasOwnProperty(field)
                );

                if (needsCleaning) {
                    const cleanResult = this.cleanProductFields(product);

                    results.cleanedProducts.push({
                        index: index,
                        id: product.id || product.product_id,
                        name: product.product_name || product.title,
                        original: product,
                        cleaned: cleanResult.product,
                        changes: cleanResult.changes,
                        fieldReduction: cleanResult.fieldReduction
                    });

                    results.totalFieldsRemoved += cleanResult.fieldReduction;
                    results.summary.cleanedFieldCount += Object.keys(cleanResult.product).length;
                } else {
                    results.skippedProducts.push({
                        index: index,
                        reason: '无需清理'
                    });
                    results.summary.cleanedFieldCount += originalFieldCount;
                }

                results.totalProcessed++;

            } catch (error) {
                results.errors.push({
                    index: index,
                    product: product,
                    error: error.message
                });
                console.error(`❌ 清理产品 ${index} 失败:`, error);
            }
        });

        // 计算存储减少百分比
        if (results.summary.originalFieldCount > 0) {
            results.summary.storageReduction =
                ((results.totalFieldsRemoved / results.summary.originalFieldCount) * 100).toFixed(1);
        }

        console.log('✅ 批量清理完成:', {
            处理数量: results.totalProcessed,
            清理数量: results.cleanedProducts.length,
            跳过数量: results.skippedProducts.length,
            错误数量: results.errors.length,
            字段减少: results.totalFieldsRemoved,
            存储减少: results.summary.storageReduction + '%'
        });

        return results;
    }

    /**
     * 验证清理后的数据完整性
     * @param {Object} original - 原始数据
     * @param {Object} cleaned - 清理后数据
     * @returns {Object} 验证结果
     */
    validateDataIntegrity(original, cleaned) {
        const validation = {
            isValid: true,
            issues: [],
            coreFieldsCheck: true,
            dataLossCheck: true
        };

        // 检查核心字段是否完整
        const coreFields = [
            'product_id', 'product_name', 'product_price',
            'product_sales', 'store_name', 'store_sales'
        ];

        for (const field of coreFields) {
            const originalValue = original[field] || original[this.getRedundantField(field)];
            const cleanedValue = cleaned[field];

            if (originalValue && !cleanedValue) {
                validation.issues.push(`核心字段丢失: ${field}`);
                validation.coreFieldsCheck = false;
                validation.isValid = false;
            } else if (originalValue && cleanedValue && originalValue !== cleanedValue) {
                validation.issues.push(`字段值改变: ${field} "${originalValue}" → "${cleanedValue}"`);
            }
        }

        // 检查是否有数据丢失
        for (const [redundant, standard] of Object.entries(this.redundantFieldMappings)) {
            if (original[redundant] && !cleaned[standard]) {
                validation.issues.push(`数据丢失: ${redundant} 的值未迁移到 ${standard}`);
                validation.dataLossCheck = false;
                validation.isValid = false;
            }
        }

        return validation;
    }

    /**
     * 获取标准字段对应的冗余字段
     */
    getRedundantField(standardField) {
        for (const [redundant, standard] of Object.entries(this.redundantFieldMappings)) {
            if (standard === standardField) {
                return redundant;
            }
        }
        return null;
    }

    /**
     * 生成清理报告
     * @param {Object} cleanupResults - 清理结果
     * @returns {string} 格式化的报告
     */
    generateCleanupReport(cleanupResults) {
        let report = '\n' + '='.repeat(60) + '\n';
        report += '🧹 数据库字段清理报告\n';
        report += '='.repeat(60) + '\n';

        report += `📊 处理统计:\n`;
        report += `   总记录数: ${cleanupResults.totalProcessed}\n`;
        report += `   清理记录: ${cleanupResults.cleanedProducts.length}\n`;
        report += `   跳过记录: ${cleanupResults.skippedProducts.length}\n`;
        report += `   错误记录: ${cleanupResults.errors.length}\n`;

        report += `\n💾 存储优化:\n`;
        report += `   删除字段: ${cleanupResults.totalFieldsRemoved}个\n`;
        report += `   存储减少: ${cleanupResults.summary.storageReduction}%\n`;

        if (cleanupResults.cleanedProducts.length > 0) {
            report += `\n🔧 清理详情 (前5条):\n`;
            const sampleSize = Math.min(5, cleanupResults.cleanedProducts.length);

            for (let i = 0; i < sampleSize; i++) {
                const item = cleanupResults.cleanedProducts[i];
                report += `   ${i + 1}. ${item.name || item.id}\n`;
                report += `      字段变化: ${item.changes.join(', ')}\n`;
                report += `      字段减少: ${item.fieldReduction}个\n`;
            }

            if (cleanupResults.cleanedProducts.length > 5) {
                report += `   ...还有 ${cleanupResults.cleanedProducts.length - 5} 条记录\n`;
            }
        }

        if (cleanupResults.errors.length > 0) {
            report += `\n❌ 错误记录:\n`;
            cleanupResults.errors.forEach((error, index) => {
                if (index < 3) { // 只显示前3个错误
                    report += `   ${error.index + 1}: ${error.error}\n`;
                }
            });
            if (cleanupResults.errors.length > 3) {
                report += `   ...还有 ${cleanupResults.errors.length - 3} 个错误\n`;
            }
        }

        report += '\n' + '='.repeat(60) + '\n';
        return report;
    }
}

// 导出到全局作用域
if (typeof window !== 'undefined') {
    window.DatabaseFieldCleaner = DatabaseFieldCleaner;
}

// Node.js环境
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DatabaseFieldCleaner;
}

console.log('📦 DatabaseFieldCleaner 模块已加载');