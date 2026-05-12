/**
 * 流量蜂小红书数据监控助手 - 本地数据管理器
 * Local Data Manager for Xiaohongshu Monitor Extension
 * 
 * 基于IndexedDB + Dexie.js的本地数据存储解决方案
 * 完全替代Feishu云端存储，实现离线数据管理
 */

class LocalDataManager {
    constructor() {
        this.dbName = 'XiaohongshuMonitor';
        this.dbVersion = 2; // 升级到版本2，添加异常检测字段
        this.db = null;
        this.isInitialized = false;
        
        // 数据库Schema配置
        this.schema = {
            categories: 'id, name, created_at',
            products: 'id, product_id, category_id, created_at, extracted_at, product_sales, store_sales',
            anomalies: 'id, product_id, detected_at, type, severity',
            settings: 'key, value'
        };

        // 默认分类配置
        this.defaultCategory = {
            id: 1,
            name: '未分类',
            description: '默认分类，用于存储未指定分类的商品',
            color: '#6366f1',
            created_at: new Date()
        };

        this.init();
    }

    /**
     * 初始化数据库
     */
    async init() {
        try {
            console.log('🔧 开始初始化IndexedDB数据库...');
            
            // 检查IndexedDB支持
            if (!window.indexedDB) {
                throw new Error('当前浏览器不支持IndexedDB');
            }

            // 由于不能直接使用Dexie，我们使用原生IndexedDB API
            await this.initNativeIndexedDB();
            this.isInitialized = true;

            // 确保默认分类存在（放在init阶段，避免在IndexedDB连接成功前调用）
            await this.ensureDefaultCategory();
            
            console.log('✅ 数据库初始化完成');
            
        } catch (error) {
            console.error('❌ 数据库初始化失败:', error);
            throw error;
        }
    }

    /**
     * 使用原生IndexedDB API初始化数据库
     */
    async initNativeIndexedDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);

            request.onerror = () => {
                reject(new Error('IndexedDB打开失败: ' + request.error));
            };

            request.onsuccess = () => {
                this.db = request.result;
                console.log('✅ IndexedDB连接成功');
                resolve();
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                const oldVersion = event.oldVersion;
                const newVersion = event.newVersion;

                console.log(`🔄 正在升级数据库Schema... ${oldVersion} -> ${newVersion}`);

                // 创建基础表结构（适用于全新安装）
                this.createTables(db);

                // 执行版本升级逻辑
                this.upgradeSchema(db, oldVersion, newVersion);

                console.log('✅ 数据库Schema升级完成');
            };
        });
    }

    /**
     * 创建数据库表结构
     */
    createTables(db) {
        // 创建分类表
        if (!db.objectStoreNames.contains('categories')) {
            const categoriesStore = db.createObjectStore('categories', { 
                keyPath: 'id', 
                autoIncrement: true 
            });
            categoriesStore.createIndex('name', 'name', { unique: true });
            categoriesStore.createIndex('created_at', 'created_at');
            console.log('✅ categories表创建成功');
        }

        // 创建产品表
        if (!db.objectStoreNames.contains('products')) {
            const productsStore = db.createObjectStore('products', { 
                keyPath: 'id', 
                autoIncrement: true 
            });
            productsStore.createIndex('product_id', 'product_id');
            productsStore.createIndex('category_id', 'category_id');
            productsStore.createIndex('extracted_at', 'extracted_at');
            productsStore.createIndex('product_sales', 'product_sales');
            productsStore.createIndex('store_sales', 'store_sales');
            productsStore.createIndex('category_time', ['category_id', 'extracted_at']);
            console.log('✅ products表创建成功');
        }


        // 创建异常表
        if (!db.objectStoreNames.contains('anomalies')) {
            const anomaliesStore = db.createObjectStore('anomalies', { 
                keyPath: 'id', 
                autoIncrement: true 
            });
            anomaliesStore.createIndex('product_id', 'product_id');
            anomaliesStore.createIndex('detected_at', 'detected_at');
            anomaliesStore.createIndex('type', 'type');
            anomaliesStore.createIndex('severity', 'severity');
            anomaliesStore.createIndex('type_time', ['type', 'detected_at']);
            console.log('✅ anomalies表创建成功');
        }

        // 创建设置表
        if (!db.objectStoreNames.contains('settings')) {
            const settingsStore = db.createObjectStore('settings', { 
                keyPath: 'key' 
            });
            console.log('✅ settings表创建成功');
        }
    }

    /**
     * 数据库版本升级逻辑
     * @param {IDBDatabase} db - 数据库实例
     * @param {number} oldVersion - 旧版本号
     * @param {number} newVersion - 新版本号
     */
    upgradeSchema(db, oldVersion, newVersion) {
        console.log(`🔄 执行数据库升级: v${oldVersion} -> v${newVersion}`);

        // 版本1到版本2：为products表添加is_anomaly字段
        if (oldVersion < 2 && newVersion >= 2) {
            console.log('📝 升级到v2: 添加异常检测字段...');

            // 在事务完成后异步添加字段（因为在onupgradeneeded中无法直接修改现有记录）
            setTimeout(() => {
                this.addAnomalyFieldToExistingProducts();
            }, 1000);
        }

        console.log('✅ 数据库升级逻辑执行完成');
    }

    /**
     * 为现有商品添加is_anomaly字段
     */
    async addAnomalyFieldToExistingProducts() {
        if (!this.db) {
            console.warn('⚠️ 数据库未初始化，跳过字段添加');
            return;
        }

        try {
            console.log('🔄 为现有商品添加is_anomaly字段...');

            const transaction = this.db.transaction(['products'], 'readwrite');
            const store = transaction.objectStore('products');

            let updateCount = 0;
            const request = store.openCursor();

            request.onsuccess = (event) => {
                const cursor = event.target.result;
                if (cursor) {
                    const product = cursor.value;

                    // 如果商品没有is_anomaly字段，添加默认值
                    if (!product.hasOwnProperty('is_anomaly')) {
                        product.is_anomaly = false;
                        cursor.update(product);
                        updateCount++;
                    }

                    cursor.continue();
                } else {
                    console.log(`✅ 完成字段添加，更新了 ${updateCount} 个商品记录`);
                }
            };

            request.onerror = () => {
                console.error('❌ 添加is_anomaly字段失败:', request.error);
            };

        } catch (error) {
            console.error('❌ 为现有商品添加字段时发生错误:', error);
        }
    }

    /**
     * 确保默认分类存在
     */
    async ensureDefaultCategory() {
        try {
            const existingCategory = await this.getCategoryById(1);
            if (!existingCategory) {
                await this.createCategory(
                    this.defaultCategory.name,
                    this.defaultCategory.description,
                    this.defaultCategory.color
                );
                console.log('✅ 默认分类创建成功');
            } else {
                console.log('✅ 默认分类已存在');
            }
        } catch (error) {
            console.warn('⚠️ 默认分类创建失败:', error);
        }
    }

    /**
     * 检查数据库是否已初始化
     */
    checkInitialized() {
        if (!this.isInitialized || !this.db) {
            throw new Error('数据库尚未初始化，请先调用init()方法');
        }
    }

    // ==================== 分类管理方法 ====================

    /**
     * 创建新分类
     */
    async createCategory(name, description = '', color = '#6366f1') {
        this.checkInitialized();
        
        const category = {
            name: name.trim(),
            description: description.trim(),
            color: color,
            created_at: new Date(),
            product_count: 0
        };

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['categories'], 'readwrite');
            const store = transaction.objectStore('categories');
            const request = store.add(category);

            request.onsuccess = () => {
                const categoryId = request.result;
                console.log(`✅ 分类创建成功: ${name} (ID: ${categoryId})`);
                resolve({...category, id: categoryId});
            };

            request.onerror = () => {
                const error = new Error(`分类创建失败: ${request.error}`);
                console.error('❌', error);
                reject(error);
            };
        });
    }

    /**
     * 更新分类
     */
    async updateCategory(id, updates) {
        this.checkInitialized();
        
        // 先获取现有分类数据
        const existingCategory = await this.getCategoryById(id);
        if (!existingCategory) {
            throw new Error('分类不存在');
        }
        
        // 合并现有数据和更新数据
        const updatedCategory = {
            ...existingCategory,
            ...updates,
            id: id
        };

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['categories'], 'readwrite');
            const store = transaction.objectStore('categories');
            const request = store.put(updatedCategory);

            request.onsuccess = () => {
                console.log(`✅ 分类更新成功: ID ${id}`);
                resolve(updatedCategory);
            };

            request.onerror = () => {
                const error = new Error(`分类更新失败: ${request.error}`);
                console.error('❌', error);
                reject(error);
            };
        });
    }

    /**
     * 删除分类（将其商品移动到默认分类）
     */
    async deleteCategory(id, moveToId = 1) {
        this.checkInitialized();
        
        if (id === 1) {
            throw new Error('默认分类不能被删除');
        }

        // 先移动该分类下的所有商品
        await this.moveProductsToCategory(id, moveToId);
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['categories'], 'readwrite');
            const store = transaction.objectStore('categories');
            const request = store.delete(id);

            request.onsuccess = () => {
                console.log(`✅ 分类删除成功: ID ${id}`);
                resolve(true);
            };

            request.onerror = () => {
                const error = new Error(`分类删除失败: ${request.error}`);
                console.error('❌', error);
                reject(error);
            };
        });
    }

    /**
     * 获取所有分类
     */
    async getCategories() {
        this.checkInitialized();
        
        try {
            // 第一步：获取分类基础数据（避免在事务回调中使用async/await）
            const categories = await this.getCategoriesBasic();
            
            // 第二步：并发获取所有分类的商品数量
            const categoriesWithCount = await Promise.all(
                categories.map(async (category) => {
                    const productCount = await this.getProductCountByCategory(category.id);
                    return {
                        ...category,
                        product_count: productCount
                    };
                })
            );
            
            // 按创建时间排序
            categoriesWithCount.sort((a, b) => a.created_at - b.created_at);
            
            return categoriesWithCount;
            
        } catch (error) {
            console.error('❌ 获取分类列表失败:', error);
            throw error;
        }
    }

    /**
     * 获取分类基础数据（不包含商品数量统计）
     */
    async getCategoriesBasic() {
        this.checkInitialized();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['categories'], 'readonly');
            const store = transaction.objectStore('categories');
            const request = store.getAll();

            request.onsuccess = () => {
                const categories = request.result || [];
                resolve(categories);
            };

            request.onerror = () => {
                const error = new Error(`获取分类基础数据失败: ${request.error}`);
                console.error('❌', error);
                reject(error);
            };
        });
    }

    /**
     * 根据ID获取分类
     */
    async getCategoryById(id) {
        this.checkInitialized();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['categories'], 'readonly');
            const store = transaction.objectStore('categories');
            const request = store.get(id);

            request.onsuccess = () => {
                resolve(request.result || null);
            };

            request.onerror = () => {
                reject(new Error(`获取分类失败: ${request.error}`));
            };
        });
    }

    // ==================== 产品数据管理方法 ====================

    /**
     * 标准化产品字段名，将各种字段变体映射到标准字段名
     * @param {Object} productData - 原始产品数据
     * @returns {Object} 标准化后的产品数据
     */
    standardizeProductFields(productData) {
        const standardized = { ...productData };

        // 字段标准化映射表
        const fieldMappings = {
            'productName': 'product_name',
            'productPrice': 'product_price',
            'productSales': 'product_sales',
            'storeSales': 'store_sales',
            'storeName': 'store_name',
            'productUrl': 'product_url',
            'productId': 'product_id',
            'title': 'product_name',
            'price': 'product_price',
            'sales': 'product_sales',
            'url': 'product_url',
            'last_crawled_at': 'extracted_at',
            'lastUpdate': 'extracted_at',
            // 'crawl_time': 'extracted_at', // 🚨 修复：crawl_time 必须保留为独立字段！
            'anomaly_detected_at': 'extracted_at',
            'goodReviews': 'good_reviews',
            'cartCount': 'cart_count',
            'recentSales': 'recent_sales',
            'storeFollowers': 'store_followers',
            'extractedAt': 'extracted_at'
        };

        // 执行字段标准化
        for (const [oldField, newField] of Object.entries(fieldMappings)) {
            if (standardized[oldField] !== undefined && standardized[newField] === undefined) {
                standardized[newField] = standardized[oldField];
            }
            // 删除非标准字段（保留additional_data等重要对象）
            if (oldField !== 'additional_data') {
                delete standardized[oldField];
            }
        }


        return standardized;
    }

    /**
     * 保存产品数据
     */
    async saveProduct(productData, categoryId = 1) {
        this.checkInitialized();

        const product = {
            product_id: productData.product_id || productData.商品ID,
            product_name: productData.product_name || productData.商品名称,
            product_url: productData.product_url || productData.商品链接,
            product_price: this.parsePrice(productData.product_price || productData.商品价格),
            product_sales: this.parseSales(productData.product_sales || productData.商品销量),
            store_sales: this.parseSales(productData.store_sales || productData.店铺销量),
            store_name: productData.store_name || productData.店铺名称,
            category_id: categoryId,
            extracted_at: this.parseDate(productData.extracted_at || productData.采集时间 || productData.爬取时间) || new Date(),
            additional_data: productData.additional_data || {
                good_reviews: productData.good_reviews !== undefined ? productData.good_reviews : '',
                cart_count: productData.cart_count !== undefined ? productData.cart_count : '',
                recent_sales: productData.recent_sales !== undefined ? productData.recent_sales : '',
                store_followers: productData.store_followers !== undefined ? productData.store_followers : ''
            },
            notes: productData.notes || productData.备注 || ''
        };

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['products'], 'readwrite');
            const store = transaction.objectStore('products');
            const request = store.add(product);

            request.onsuccess = () => {
                const productId = request.result;
                // 性能优化：移除日志输出，由批量操作统一输出
                resolve({...product, id: productId});
            };

            request.onerror = () => {
                const error = new Error(`商品保存失败: ${request.error}`);
                console.error('❌', error);
                reject(error);
            };
        });
    }

    /**
     * 批量保存产品数据
     */
    async batchSaveProducts(products, categoryId = 1) {
        this.checkInitialized();
        
        const results = [];
        const errors = [];
        
        for (let i = 0; i < products.length; i++) {
            try {
                const result = await this.saveProduct(products[i], categoryId);
                results.push(result);
                console.log(`进度: ${i + 1}/${products.length} 商品保存成功`);
            } catch (error) {
                errors.push({ index: i, product: products[i], error: error.message });
                console.error(`商品 ${i + 1} 保存失败:`, error.message);
            }
        }
        
        return {
            success: results.length,
            failed: errors.length,
            results: results,
            errors: errors
        };
    }

    /**
     * 批量保存产品数据（带去重功能）
     * 如果商品ID已存在，则更新现有记录；否则创建新记录
     * ✅ 性能优化版：减少日志输出，添加进度节流
     */
    async batchSaveProductsWithDedup(products, categoryId = 1) {
        this.checkInitialized();

        const results = [];
        const errors = [];
        const skippedDuplicates = [];
        const totalCount = products.length;

        console.log(`🚀 开始批量保存 ${totalCount} 个商品到分类 ${categoryId}，启用去重功能...`);

        // 性能优化：减少日志输出频率
        const PROGRESS_INTERVAL = 50; // 每50条输出一次进度
        const startTime = Date.now();

        for (let i = 0; i < products.length; i++) {
            try {
                const productData = products[i];
                const productId = productData.productId || productData.商品ID || productData.product_id;

                if (!productId) {
                    // 如果没有商品ID，直接保存（不去重）
                    const result = await this.saveProduct(productData, categoryId);
                    results.push({ ...result, operation: 'created_no_id' });
                    continue;
                }

                // 只在第一条记录时输出调试信息
                if (i === 0) {
                    console.log('🔍 Excel解析的第一个商品原始数据:', productData);
                    console.log('🔍 可用字段:', Object.keys(productData));
                }

                // 智能字段映射 - 支持多种字段名格式 (阶段2扩展字段整合优化)
                const mappedProductData = {
                    product_id: productId,
                    product_name: productData.productName || productData.product_name || productData['商品名称'] || productData['产品名称'] || productData.title || productData.name || `商品_${productId}`,
                    product_url: productData.productUrl || productData.product_url || productData['商品链接'] || productData['产品链接'] || productData.url || productData.link,
                    product_price: this.parsePrice(productData.productPrice || productData.product_price || productData['商品价格'] || productData['产品价格'] || productData.price || 0),
                    product_sales: this.parseSales(productData.productSales || productData.product_sales || productData['商品销量'] || productData['产品销量'] || productData.sales || 0),
                    store_sales: this.parseSales(productData.storeSales || productData.store_sales || productData['店铺销量'] || productData['店铺总销量'] || 0),
                    store_name: productData.storeName || productData.store_name || productData['店铺名称'] || productData['店铺'] || productData.store || '',
                    // 时间字段统一映射 (ultrathink优化)
                    extracted_at: productData.extractedAt || productData.extracted_at || productData.lastCrawledAt || productData.last_crawled_at || productData.lastUpdate || productData['采集时间'] || productData['提取时间'] || productData['最后更新时间'],
                    // 🚨 修复：crawl_time 必须作为独立字段保存 (爬取时间)
                    crawl_time: productData.crawl_time || productData['爬取时间'] || productData['最后爬取时间'] || productData['数据爬取时间'] || new Date().toISOString(),
                    // 🎯 ultrathink 彻底重写：直接使用Excel解析阶段构建的additional_data，避免重复映射
                    additional_data: this.buildAdditionalData(productData),
                    notes: productData.notes || productData['备注'] || ''
                };

                // 使用upsert方法进行去重保存，启用静默模式
                const result = await this.upsertProduct(mappedProductData, categoryId, { silent: true });

                results.push(result);

                // 性能优化：每PROGRESS_INTERVAL条或最后一条输出进度
                if ((i + 1) % PROGRESS_INTERVAL === 0 || i === totalCount - 1) {
                    const progress = Math.round(((i + 1) / totalCount) * 100);
                    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
                    const speed = ((i + 1) / elapsed).toFixed(1);
                    console.log(`📊 进度: ${i + 1}/${totalCount} (${progress}%) | 耗时: ${elapsed}s | 速度: ${speed}条/秒`);
                }

            } catch (error) {
                errors.push({ index: i, product: products[i], error: error.message });
                // 只输出错误，不输出每条成功信息
                if (errors.length <= 10) { // 只输出前10条错误
                    console.error(`❌ 商品 ${i + 1} 保存失败:`, error.message);
                }
            }
        }

        const createdCount = results.filter(r => r.operation === 'created').length;
        const updatedCount = results.filter(r => r.operation === 'updated').length;
        const noIdCount = results.filter(r => r.operation === 'created_no_id').length;
        const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
        const avgSpeed = (totalCount / totalTime).toFixed(1);

        console.log(`✅ 批量保存完成：新建 ${createdCount} 个，更新 ${updatedCount} 个，无ID ${noIdCount} 个，失败 ${errors.length} 个`);
        console.log(`⏱️ 总耗时: ${totalTime}s | 平均速度: ${avgSpeed}条/秒`);

        return {
            success: results.length,
            failed: errors.length,
            created: createdCount,
            updated: updatedCount,
            noId: noIdCount,
            results: results,
            errors: errors
        };
    }

    /**
     * 清理所有产品数据 - 用于重新导入
     */
    async clearAllProducts() {
        this.checkInitialized();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['products'], 'readwrite');
            const store = transaction.objectStore('products');
            const request = store.clear();
            
            request.onsuccess = () => {
                console.log('✅ 所有产品数据已清理');
                resolve();
            };
            
            request.onerror = () => {
                reject(new Error('清理产品数据失败: ' + request.error));
            };
        });
    }

    /**
     * 获取指定分类的产品列表
     */
    async getProducts(categoryId = null, filters = {}, pagination = { page: 1, limit: 20 }) {
        this.checkInitialized();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['products'], 'readonly');
            const store = transaction.objectStore('products');
            
            let request;
            if (categoryId) {
                const index = store.index('category_id');
                request = index.getAll(categoryId);
            } else {
                request = store.getAll();
            }

            request.onsuccess = () => {
                let products = request.result || [];
                
                // 应用过滤器
                if (filters.search) {
                    const searchTerm = filters.search.toLowerCase();
                    products = products.filter(p => 
                        (p.product_name && p.product_name.toLowerCase().includes(searchTerm)) ||
                        (p.product_id && p.product_id.toLowerCase().includes(searchTerm)) ||
                        (p.store_name && p.store_name.toLowerCase().includes(searchTerm))
                    );
                }
                
                // 排序
                if (filters.sortBy) {
                    products.sort((a, b) => {
                        const sortField = filters.sortBy.replace('_desc', '').replace('_asc', '');
                        const isDesc = filters.sortBy.includes('_desc');
                        
                        let aVal = a[sortField];
                        let bVal = b[sortField];
                        
                        if (sortField === 'extracted_at') {
                            aVal = new Date(aVal);
                            bVal = new Date(bVal);
                        }
                        
                        const comparison = aVal > bVal ? 1 : (aVal < bVal ? -1 : 0);
                        return isDesc ? -comparison : comparison;
                    });
                }
                
                // 分页
                const total = products.length;
                const startIndex = (pagination.page - 1) * pagination.limit;
                const endIndex = startIndex + pagination.limit;
                const paginatedProducts = products.slice(startIndex, endIndex);
                
                resolve({
                    products: paginatedProducts,
                    pagination: {
                        page: pagination.page,
                        limit: pagination.limit,
                        total: total,
                        totalPages: Math.ceil(total / pagination.limit)
                    }
                });
            };

            request.onerror = () => {
                reject(new Error(`获取商品列表失败: ${request.error}`));
            };
        });
    }

    /**
     * 获取单个商品信息
     */
    async getProduct(productId) {
        this.checkInitialized();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['products'], 'readonly');
            const store = transaction.objectStore('products');
            const request = store.get(productId);

            request.onsuccess = () => {
                const product = request.result;
                if (product) {
                    resolve({
                        success: true,
                        product: product
                    });
                } else {
                    resolve({
                        success: false,
                        message: `商品 ID ${productId} 不存在`
                    });
                }
            };

            request.onerror = () => {
                reject(new Error(`获取商品失败: ${request.error}`));
            };
        });
    }

    /**
     * 根据product_id查找商品（新增方法）
     * 专门用于upsert操作中查找现有商品，确保返回完整的时间序列字段
     * @param {string} productId - 产品的product_id字段
     * @returns {Object|null} 找到的完整产品记录，包含所有时间序列字段
     */
    async getProductByProductId(productId) {
        this.checkInitialized();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['products'], 'readonly');
            const store = transaction.objectStore('products');

            // ✅ 性能优化：使用索引查询替代全表扫描（性能提升100倍+）
            // 从O(n)全表遍历优化为O(log n)索引查询
            const index = store.index('product_id');
            const request = index.get(productId);

            request.onsuccess = () => {
                // 索引查询直接返回匹配的记录，包括所有时间序列字段
                resolve(request.result || null);
            };

            request.onerror = () => {
                reject(new Error(`查找商品失败: ${request.error}`));
            };
        });
    }

    /**
     * 获取指定分类的商品数量（增强版）
     */
    async getProductCountByCategory(categoryId) {
        this.checkInitialized();
        
        return new Promise((resolve, reject) => {
            try {
                const transaction = this.db.transaction(['products'], 'readonly');
                const store = transaction.objectStore('products');
                const index = store.index('category_id');
                const request = index.count(categoryId);

                request.onsuccess = () => {
                    const count = request.result || 0;
                    console.log(`📈 分类 ${categoryId} 商品数量: ${count}`);
                    resolve(count);
                };

                request.onerror = () => {
                    console.warn(`⚠️ 获取分类 ${categoryId} 商品数量失败:`, request.error);
                    resolve(0); // 出错时返回0
                };
                
                transaction.onerror = () => {
                    console.warn(`⚠️ 事务错误 (分类 ${categoryId}):`, transaction.error);
                    resolve(0);
                };
                
            } catch (error) {
                console.error(`❌ 获取分类 ${categoryId} 商品数量出现异常:`, error);
                resolve(0);
            }
        });
    }

    /**
     * 批量获取多个分类的商品数量（性能优化）
     */
    async getBatchProductCounts(categoryIds) {
        this.checkInitialized();
        
        if (!categoryIds || categoryIds.length === 0) {
            return {};
        }
        
        try {
            // 使用Promise.all并发查询，提高性能
            const countPromises = categoryIds.map(async (categoryId) => {
                const count = await this.getProductCountByCategory(categoryId);
                return { categoryId, count };
            });
            
            const results = await Promise.all(countPromises);
            
            // 转换为对象格式
            const countMap = {};
            results.forEach(({ categoryId, count }) => {
                countMap[categoryId] = count;
            });
            
            console.log('📈 批量获取商品数量完成:', countMap);
            return countMap;
            
        } catch (error) {
            console.error('❌ 批量获取商品数量失败:', error);
            // 返回默认值
            const defaultCounts = {};
            categoryIds.forEach(id => {
                defaultCounts[id] = 0;
            });
            return defaultCounts;
        }
    }

    /**
     * 将商品移动到其他分类
     */
    async moveProductsToCategory(fromCategoryId, toCategoryId) {
        this.checkInitialized();
        
        const products = await this.getProducts(fromCategoryId);
        
        for (let product of products.products) {
            product.category_id = toCategoryId;
            
            await new Promise((resolve, reject) => {
                const transaction = this.db.transaction(['products'], 'readwrite');
                const store = transaction.objectStore('products');
                const request = store.put(product);
                
                request.onsuccess = () => resolve();
                request.onerror = () => reject(request.error);
            });
        }
        
        console.log(`✅ 已将 ${products.products.length} 个商品从分类 ${fromCategoryId} 移动到 ${toCategoryId}`);
    }

    // ==================== 快照和异常检测相关方法 ====================



    // ==================== 工具方法 ====================

    /**
     * 解析销量数字
     */
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
        
        return Math.floor(number);
    }

    /**
     * 解析价格
     */
    parsePrice(priceText) {
        if (typeof priceText === 'number') return priceText;
        if (!priceText) return 0;
        
        const text = String(priceText).replace(/[¥$￥]/g, '').trim();
        const number = parseFloat(text.replace(/,/g, ''));
        
        return isNaN(number) ? 0 : number;
    }
    
    /**
     * 解析日期时间 - ultrathink 增强版
     * 支持多种日期格式，包括Excel序列日期格式
     */
    parseDate(dateText) {
        if (!dateText) return null;

        // 如果已经是Date对象，直接返回
        if (dateText instanceof Date) return dateText;

        const text = String(dateText).trim();
        if (!text) return null;

        // 🎯 ultrathink: 检测Excel序列日期格式
        if (/^\d+(\.\d+)?$/.test(text)) {
            const serialNumber = parseFloat(text);
            // Excel日期序列号范围：1 到 2958465 (1900-01-01 到 9999-12-31)
            if (serialNumber >= 1 && serialNumber <= 2958465) {
                try {
                    // Excel日期序列号转换（修正Excel的1900年闰年错误）
                    // Excel错误地认为1900年是闰年，所以序列号1对应1900年1月1日
                    // 但实际需要减去1天来修正这个错误
                    let adjustedSerial = serialNumber;
                    if (serialNumber >= 60) {
                        adjustedSerial = serialNumber - 1; // 修正1900年闰年错误
                    }

                    // 计算日期和时间
                    const daysPart = Math.floor(adjustedSerial);
                    const timePart = adjustedSerial - daysPart;

                    // 从1900年1月1日开始计算
                    const baseDate = new Date(1900, 0, 1); // 1900年1月1日
                    const targetDate = new Date(baseDate.getTime() + (daysPart - 1) * 24 * 60 * 60 * 1000);

                    // 添加时间部分（小数部分转换为小时、分钟、秒）
                    const totalMinutes = timePart * 24 * 60;
                    const hours = Math.floor(totalMinutes / 60);
                    const minutes = Math.floor(totalMinutes % 60);
                    const seconds = Math.floor((totalMinutes % 1) * 60);

                    const finalDate = new Date(
                        targetDate.getFullYear(),
                        targetDate.getMonth(),
                        targetDate.getDate(),
                        hours,
                        minutes,
                        seconds
                    );

                    if (!isNaN(finalDate.getTime())) {
                        // 性能优化：移除日志输出
                        return finalDate;
                    }
                } catch (error) {
                    console.warn(`⚠️ [日期解析] Excel序列格式解析失败: "${text}"`, error);
                }
            }
        }

        // 尝试解析各种日期格式
        try {
            // 🚀 ultrathink: 支持的日期格式列表（按优先级）
            const supportedFormats = [
                // 新增格式：2025/08/19 23:09
                { pattern: /^(\d{4})\/(\d{1,2})\/(\d{1,2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?$/, name: 'YYYY/MM/DD HH:mm(:ss)' },

                // 现有格式：2025-09-10 12:23
                { pattern: /^(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?$/, name: 'YYYY-MM-DD HH:mm(:ss)' },

                // ISO格式：2025-09-10T12:23:00Z
                { pattern: /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/, name: 'ISO 8601' },

                // 简化日期格式：2025/08/19
                { pattern: /^(\d{4})\/(\d{1,2})\/(\d{1,2})$/, name: 'YYYY/MM/DD' },

                // 简化日期格式：2025-09-10
                { pattern: /^(\d{4})-(\d{1,2})-(\d{1,2})$/, name: 'YYYY-MM-DD' }
            ];

            // 1. 尝试特定格式解析（更精确）
            for (const format of supportedFormats) {
                const match = text.match(format.pattern);
                if (match) {
                    let year, month, day, hour = 0, minute = 0, second = 0;

                    if (format.name.includes('YYYY/MM/DD') || format.name.includes('YYYY-MM-DD')) {
                        [, year, month, day, hour, minute, second] = match;
                    }

                    // 构建标准化的Date对象
                    const parsedDate = new Date(
                        parseInt(year),
                        parseInt(month) - 1, // JavaScript月份从0开始
                        parseInt(day),
                        parseInt(hour || 0),
                        parseInt(minute || 0),
                        parseInt(second || 0)
                    );

                    if (!isNaN(parsedDate.getTime())) {
                        // 性能优化：移除日志输出
                        return parsedDate;
                    }
                }
            }

            // 2. 备用方案：使用JavaScript原生Date构造函数
            const date = new Date(text);

            // 检查是否为有效日期
            if (isNaN(date.getTime())) {
                // 性能优化：只在失败时输出警告
                if (text && text.length > 0) {
                    console.warn(`❌ [日期解析] 无效日期格式: "${text}"`);
                }
                return null;
            }

            return date;

        } catch (error) {
            console.warn(`❌ [日期解析] 解析失败: "${text}"`, error);
            return null;
        }
    }

    /**
     * 🎯 ultrathink 彻底重写：构建additional_data对象
     * 优先使用Excel解析阶段已构建的additional_data，确保数据完整性
     */
    buildAdditionalData(productData) {
        // 如果Excel解析阶段已经构建了完整的additional_data，直接使用
        if (productData.additional_data &&
            typeof productData.additional_data === 'object' &&
            productData.additional_data.good_reviews !== undefined &&
            productData.additional_data.cart_count !== undefined &&
            productData.additional_data.recent_sales !== undefined &&
            productData.additional_data.store_followers !== undefined) {

            return productData.additional_data;
        }

        // 否则，重新构建（确保不会出现undefined）
        const additional_data = {
            good_reviews: this.getFieldValue(productData, ['goodReviews', 'good_reviews', '好评人数'], ''),
            cart_count: this.getFieldValue(productData, ['cartCount', 'cart_count', '加购件数'], ''),
            recent_sales: this.getFieldValue(productData, ['recentSales', 'recent_sales', '近3个月销量'], ''),
            store_followers: this.getFieldValue(productData, ['storeFollowers', 'store_followers', '店铺粉丝数'], '')
        };

        return additional_data;
    }

    /**
     * 🎯 ultrathink 辅助方法：按优先级获取字段值，确保不返回undefined
     */
    getFieldValue(data, fieldNames, defaultValue = '') {
        for (const fieldName of fieldNames) {
            const value = data[fieldName];
            if (value !== undefined && value !== null) {
                return value;
            }
        }
        return defaultValue;
    }

    /**
     * 获取统计信息（优化版）
     */
    async getStatistics() {
        this.checkInitialized();
        
        try {
            const categories = await this.getCategories();
            const totalProducts = categories.reduce((sum, cat) => sum + (cat.product_count || 0), 0);
            const categoriesWithData = categories.filter(cat => (cat.product_count || 0) > 0).length;
            
            const stats = {
                totalProducts: totalProducts,
                totalCategories: categories.length,
                categoriesWithData: categoriesWithData,
                lastUpdateTime: new Date(),
                categories: categories.map(cat => ({
                    id: cat.id,
                    name: cat.name,
                    product_count: cat.product_count || 0
                }))
            };
            
            console.log('📈 系统统计信息:', {
                总商品数: stats.totalProducts,
                总分类数: stats.totalCategories,
                有数据分类: stats.categoriesWithData
            });
            
            return stats;
            
        } catch (error) {
            console.error('❌ 获取统计信息失败:', error);
            throw error;
        }
    }

    /**
     * 验证修复效果（调试用）
     */
    async validateFix() {
        try {
            console.log('🔍 开始验证修复效果...');
            
            const categories = await this.getCategories();
            console.log('✅ 获取分类列表成功:', categories.length, '个分类');
            
            categories.forEach(cat => {
                console.log(`  - ${cat.name} (ID: ${cat.id}): ${cat.product_count || 0} 件商品`);
            });
            
            const stats = await this.getStatistics();
            console.log('✅ 统计信息获取成功:', stats);
            
            return {
                success: true,
                categories: categories,
                statistics: stats,
                message: '修复验证成功！商品数量统计正常显示。'
            };
            
        } catch (error) {
            console.error('❌ 修复验证失败:', error);
            return {
                success: false,
                error: error.message,
                message: '修复验证失败，请检查控制台错误信息。'
            };
        }
    }

    /**
     * 清理过期数据
     */
    async cleanupExpiredData() {
        this.checkInitialized();

        // 清理30天前的异常记录
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

        console.log('🔄 开始清理过期异常数据...');

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['anomalies'], 'readwrite');
            const store = transaction.objectStore('anomalies');
            const index = store.index('detected_at');
            const range = IDBKeyRange.upperBound(thirtyDaysAgo);
            const request = index.openCursor(range);

            let deletedCount = 0;

            request.onsuccess = (event) => {
                const cursor = event.target.result;
                if (cursor) {
                    cursor.delete();
                    deletedCount++;
                    cursor.continue();
                } else {
                    console.log(`✅ 清理完成，删除了 ${deletedCount} 条过期异常记录`);
                    resolve(deletedCount);
                }
            };

            request.onerror = () => {
                reject(new Error('清理过期数据失败: ' + request.error));
            };
        });
    }

    // ==================== 数据管理器专用方法 ====================

    /**
     * 获取商品总数
     */
    async getTotalProductCount() {
        this.checkInitialized();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['products'], 'readonly');
            const store = transaction.objectStore('products');
            const request = store.count();
            
            request.onsuccess = () => {
                resolve(request.result || 0);
            };
            
            request.onerror = () => {
                reject(new Error('获取商品总数失败: ' + request.error));
            };
        });
    }

    /**
     * 获取快照总数（替代实现）
     * 返回当前商品数据的时间序列字段总数
     */
    async getTotalSnapshotCount() {
        this.checkInitialized();

        try {
            const products = await this.getAllProducts();
            let totalTimeSeriesFields = 0;

            products.forEach(product => {
                // 统计包含日期的动态字段数量
                Object.keys(product).forEach(key => {
                    if (key.match(/\d{4}-\d{2}-\d{2}/)) {
                        totalTimeSeriesFields++;
                    }
                });
            });

            return totalTimeSeriesFields;
        } catch (error) {
            console.error('获取时间序列数据统计失败:', error);
            return 0;
        }
    }

    /**
     * 获取所有商品数据（用于数据分析和展示）
     */
    async getAllProducts() {
        this.checkInitialized();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['products'], 'readonly');
            const store = transaction.objectStore('products');
            const request = store.getAll();
            
            request.onsuccess = () => {
                resolve(request.result || []);
            };
            
            request.onerror = () => {
                reject(new Error('获取所有商品失败: ' + request.error));
            };
        });
    }

    /**
     * 获取销量趋势数据（基于商品24小时增长数据）
     * @param {number} days 天数
     */
    async getSalesTrend(days = 30) {
        this.checkInitialized();

        try {
            const products = await this.getAllProducts();
            const endDate = new Date();
            const dataMap = new Map();

            // 遍历所有商品，收集时间序列数据
            products.forEach(product => {
                Object.keys(product).forEach(key => {
                    const dateMatch = key.match(/新增销量_(\d{4}-\d{2}-\d{2})/);
                    if (dateMatch) {
                        const dateStr = dateMatch[1];
                        const date = new Date(dateStr);
                        const dateKey = date.toISOString().split('T')[0];

                        // 检查是否在指定天数范围内
                        const daysDiff = Math.floor((endDate - date) / (1000 * 60 * 60 * 24));
                        if (daysDiff >= 0 && daysDiff < days) {
                            if (!dataMap.has(dateKey)) {
                                dataMap.set(dateKey, 0);
                            }
                            dataMap.set(dateKey, dataMap.get(dateKey) + (product[key] || 0));
                        }
                    }
                });
            });

            // 生成完整的日期序列
            const labels = [];
            const values = [];

            for (let i = 0; i < days; i++) {
                const date = new Date();
                date.setDate(endDate.getDate() - (days - 1 - i));
                const dateKey = date.toISOString().split('T')[0];
                const dateLabel = date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });

                labels.push(dateLabel);
                values.push(dataMap.get(dateKey) || 0);
            }

            return { labels, values };

        } catch (error) {
            console.error('获取销量趋势失败:', error);

            // 返回空数据作为fallback
            const labels = [];
            const values = [];
            const endDate = new Date();

            for (let i = 0; i < days; i++) {
                const date = new Date();
                date.setDate(endDate.getDate() - (days - 1 - i));
                const dateLabel = date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
                labels.push(dateLabel);
                values.push(0);
            }

            return { labels, values };
        }
    }

    /**
     * 获取最近的活动记录（基于商品更新数据）
     * @param {number} limit 限制数量
     */
    async getRecentSnapshots(limit = 10) {
        this.checkInitialized();

        try {
            const products = await this.getAllProducts();
            const results = [];

            // 收集所有带有时间序列数据的商品记录
            products.forEach(product => {
                // 查找最新的时间序列数据
                let latestDate = null;
                let latestData = null;

                Object.keys(product).forEach(key => {
                    const salesMatch = key.match(/新增销量_(\d{4}-\d{2}-\d{2})/);
                    const revenueMatch = key.match(/新增销售额_(\d{4}-\d{2}-\d{2})/);

                    if (salesMatch) {
                        const dateStr = salesMatch[1];
                        const date = new Date(dateStr);

                        if (!latestDate || date > latestDate) {
                            latestDate = date;
                            latestData = {
                                date: dateStr,
                                newSales: product[key] || 0,
                                newRevenue: product[`新增销售额_${dateStr}`] || 0,
                                crawlTime: product[`爬取时间_${dateStr}`]
                            };
                        }
                    }
                });

                if (latestData) {
                    results.push({
                        id: `${product.product_id}_${latestData.date}`,
                        product_id: product.product_id,
                        productTitle: product.product_name || '未知商品',
                        timestamp: latestDate,
                        currentSales: product.product_sales || 0,
                        newSales: latestData.newSales,
                        newRevenue: latestData.newRevenue,
                        previousSales: (product.product_sales || 0) - latestData.newSales,
                        crawlTime: latestData.crawlTime,
                        dateStr: latestData.date
                    });
                }
            });

            // 按时间排序并限制数量
            results.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
            return results.slice(0, limit);

        } catch (error) {
            console.error('获取最近活动记录失败:', error);
            return [];
        }
    }

    /**
     * 删除商品及相关数据
     */
    async deleteProduct(productId) {
        this.checkInitialized();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['products', 'anomalies'], 'readwrite');

            // 删除商品记录
            const productStore = transaction.objectStore('products');
            productStore.delete(productId);

            // 删除相关异常记录
            const anomalyStore = transaction.objectStore('anomalies');
            const anomalyIndex = anomalyStore.index('product_id');
            const anomalyRequest = anomalyIndex.openCursor(productId);

            anomalyRequest.onsuccess = (event) => {
                const cursor = event.target.result;
                if (cursor) {
                    cursor.delete();
                    cursor.continue();
                }
            };

            transaction.oncomplete = () => {
                resolve();
            };

            transaction.onerror = () => {
                reject(new Error('删除商品失败: ' + transaction.error));
            };
        });
    }

    /**
     * 更新商品信息
     */
    async updateProduct(productData) {
        this.checkInitialized();
        
        if (!productData.id) {
            throw new Error('更新商品需要提供商品ID');
        }
        
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['products'], 'readwrite');
            const store = transaction.objectStore('products');
            const request = store.put(productData);
            
            request.onsuccess = () => {
                resolve(productData);
            };
            
            request.onerror = () => {
                reject(new Error('更新商品失败: ' + request.error));
            };
        });
    }

    /**
     * Upsert商品信息 (存在则更新，不存在则创建)
     * 专为批量监控设计，支持销量数据的时间序列更新
     */
    async upsertProduct(productData, categoryId = 1, options = {}) {
        this.checkInitialized();

        // 性能优化：支持静默模式减少日志输出
        const silent = options.silent || false;

        try {
            // 1. 尝试根据product_id查找现有商品 - 使用专门的方法确保获取完整记录
            let existingProduct = null;
            if (productData.product_id) {
                try {
                    existingProduct = await this.getProductByProductId(productData.product_id);
                } catch (err) {
                    if (!silent) console.warn('❌ [Upsert查找] 查找现有商品时出错:', err);
                    existingProduct = null;
                }
            }

            if (existingProduct) {
                // 2. 更新现有商品 - 保留基准数据，不覆盖product_sales和store_sales
                const updatedProduct = {
                    ...existingProduct,
                    // 保留基准数据用于增长计算 - 不更新这些字段
                    // product_sales: 保持原值作为基准
                    // store_sales: 保持原值作为基准
                    // 只更新价格（价格可能变化）
                    product_price: productData.product_price || existingProduct.product_price,
                    // 更新时间戳
                    last_crawled_at: new Date(),
                    // 保留原始数据，添加新的爬取数据
                    raw_data: {
                        ...(existingProduct.raw_data || {}),
                        latest_crawl: {
                            timestamp: new Date().toISOString(),
                            data: productData.raw_data || productData
                        }
                    }
                };

                const result = await this.updateProduct(updatedProduct);
                return { ...result, operation: 'updated' };
            } else {
                // 3. 创建新商品
                const newProductData = {
                    ...productData,
                    category_id: categoryId,
                    extracted_at: this.parseDate(productData.extracted_at || productData.last_crawled_at || productData.lastUpdate || productData.采集时间 || productData.提取时间 || productData.最后更新时间) || new Date(),
                    // 🚨 修复：crawl_time 必须作为独立字段保存 (爬取时间)
                    crawl_time: this.parseDate(productData.crawl_time || productData.爬取时间 || productData.最后爬取时间 || productData.数据爬取时间) || new Date(),
                    raw_data: {
                        original: productData.raw_data || productData,
                        first_crawl: {
                            timestamp: new Date().toISOString(),
                            data: productData.raw_data || productData
                        }
                    }
                };

                const result = await this.saveProduct(newProductData, categoryId);
                return { ...result, operation: 'created' };
            }

        } catch (error) {
            console.error('❌ Upsert商品失败:', error);
            throw new Error(`Upsert商品失败: ${error.message}`);
        }
    }

    /**
     * 带时间序列的Upsert商品信息
     * 支持动态日期字段创建和更新
     */
    async upsertProductWithTimeSeries(productData, categoryId = 1, crawlDate = new Date()) {
        this.checkInitialized();
        
        try {
            // 1. 初始化时间序列数据管理器（如果尚未初始化）
            if (!this.timeSeriesManager) {
                this.timeSeriesManager = new TimeSeriesDataManager();
            }
            
            // 2. 执行基础的upsert操作
            const baseResult = await this.upsertProduct(productData, categoryId);
            
            // 3. 应用时间序列字段更新
            const timeSeriesResult = await this.timeSeriesManager.upsertTimeSeriesData(
                baseResult, 
                {
                    productSales: productData.product_sales,
                    storeSales: productData.store_sales,
                    productPrice: productData.product_price || productData.price
                },
                crawlDate
            );
            
            // 4. 如果时间序列更新成功，保存到数据库
            if (timeSeriesResult.success) {
                const updateResult = await this.updateProduct(baseResult);
                
                // 5. 合并结果信息
                return {
                    ...updateResult,
                    operation: baseResult.operation,
                    timeSeriesOperation: timeSeriesResult.operation,
                    dateStr: timeSeriesResult.dateStr,
                    timeSeriesCount: timeSeriesResult.timeSeriesCount,
                    productSales: timeSeriesResult.productSales,
                    storeSales: timeSeriesResult.storeSales,
                    crawlTime: timeSeriesResult.crawlTime,
                    fields: timeSeriesResult.fields
                };
            } else {
                console.error('❌ 时间序列数据处理失败:', timeSeriesResult.error);
                throw new Error(`时间序列数据处理失败: ${timeSeriesResult.error}`);
            }
            
        } catch (error) {
            console.error('❌ 带时间序列的Upsert商品失败:', error);
            throw new Error(`带时间序列的Upsert商品失败: ${error.message}`);
        }
    }

    /**
     * 获取商品的销量历史数据
     */
    async getProductSalesHistory(productId) {
        this.checkInitialized();
        
        try {
            // 获取商品记录
            const product = await this.getProduct(productId);
            if (!product) {
                throw new Error('商品不存在');
            }
            
            // 初始化时间序列管理器（如果需要）
            if (!this.timeSeriesManager) {
                this.timeSeriesManager = new TimeSeriesDataManager();
            }
            
            // 返回销量历史
            return this.timeSeriesManager.getSalesHistory(product);
            
        } catch (error) {
            console.error('❌ 获取销量历史失败:', error);
            throw new Error(`获取销量历史失败: ${error.message}`);
        }
    }

    /**
     * 获取商品的销量趋势分析
     */
    async getProductSalesTrend(productId, days = 7) {
        this.checkInitialized();
        
        try {
            // 获取商品记录
            const product = await this.getProduct(productId);
            if (!product) {
                throw new Error('商品不存在');
            }
            
            // 初始化时间序列管理器（如果需要）
            if (!this.timeSeriesManager) {
                this.timeSeriesManager = new TimeSeriesDataManager();
            }
            
            // 返回趋势分析
            return this.timeSeriesManager.calculateSalesGrowthTrend(product, days);
            
        } catch (error) {
            console.error('❌ 获取销量趋势失败:', error);
            throw new Error(`获取销量趋势失败: ${error.message}`);
        }
    }

    /**
     * 批量获取商品时间序列统计
     */
    async getBatchTimeSeriesStats(categoryId = null, limit = 100) {
        this.checkInitialized();
        
        try {
            // 获取商品列表
            const result = await this.getProducts(categoryId, {}, { page: 1, limit });
            const products = result.products;
            
            // 初始化时间序列管理器
            if (!this.timeSeriesManager) {
                this.timeSeriesManager = new TimeSeriesDataManager();
            }
            
            const stats = {
                totalProducts: products.length,
                withTimeSeriesData: 0,
                totalTimeSeriesFields: 0,
                averageDaysTracked: 0,
                latestCrawlDate: null,
                oldestCrawlDate: null,
                productStats: []
            };
            
            const allCrawlDates = [];
            
            products.forEach(product => {
                const timeSeriesCount = this.timeSeriesManager.getTimeSeriesCount(product);
                const salesHistory = this.timeSeriesManager.getSalesHistory(product);
                
                if (timeSeriesCount.uniqueDays > 0) {
                    stats.withTimeSeriesData++;
                    stats.totalTimeSeriesFields += timeSeriesCount.total;
                    
                    // 收集爬取日期
                    salesHistory.forEach(entry => {
                        if (entry.crawlTime) {
                            allCrawlDates.push(new Date(entry.crawlTime));
                        }
                    });
                    
                    stats.productStats.push({
                        productId: product.product_id,
                        productName: product.product_name,
                        daysTracked: timeSeriesCount.uniqueDays,
                        totalFields: timeSeriesCount.total,
                        latestSales: salesHistory.length > 0 ? salesHistory[salesHistory.length - 1] : null
                    });
                }
            });
            
            // 计算日期统计
            if (allCrawlDates.length > 0) {
                stats.latestCrawlDate = new Date(Math.max(...allCrawlDates));
                stats.oldestCrawlDate = new Date(Math.min(...allCrawlDates));
                stats.averageDaysTracked = Math.round(
                    stats.totalTimeSeriesFields / 3 / stats.withTimeSeriesData
                ); // 除以3是因为每天有3个字段（销量、店铺销量、爬取时间）
            }
            
            return stats;
            
        } catch (error) {
            console.error('❌ 获取批量时间序列统计失败:', error);
            throw new Error(`获取批量时间序列统计失败: ${error.message}`);
        }
    }

    /**
     * 获取异常记录
     */
    /**
     * @deprecated ultrathink: 此方法已废弃，使用简化的 getAnomalyProducts() 代替
     */
    async getAnomalies(filters = {}) {
        this.checkInitialized();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['anomalies'], 'readonly');
            const store = transaction.objectStore('anomalies');
            const request = store.getAll();
            
            request.onsuccess = () => {
                let anomalies = request.result || [];
                
                // 应用筛选条件
                if (filters.severity) {
                    anomalies = anomalies.filter(a => a.severity === filters.severity);
                }
                
                if (filters.type) {
                    anomalies = anomalies.filter(a => a.type === filters.type);
                }
                
                if (filters.startDate && filters.endDate) {
                    anomalies = anomalies.filter(a => {
                        const date = new Date(a.detected_at);
                        return date >= filters.startDate && date <= filters.endDate;
                    });
                }
                
                // 按检测时间倒序排序
                anomalies.sort((a, b) => new Date(b.detected_at) - new Date(a.detected_at));
                
                resolve(anomalies);
            };
            
            request.onerror = () => {
                reject(new Error('获取异常记录失败: ' + request.error));
            };
        });
    }

    /**
     * 保存异常记录
     * @deprecated ultrathink: 此方法已废弃，使用简化的 is_anomaly 字段标记代替
     */
    async saveAnomaly(anomalyData) {
        this.checkInitialized();
        
        const anomaly = {
            product_id: anomalyData.productId,
            type: anomalyData.type,
            severity: anomalyData.severity,
            description: anomalyData.description,
            detected_at: new Date(),
            resolved: false,
            metadata: anomalyData.metadata || {}
        };
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['anomalies'], 'readwrite');
            const store = transaction.objectStore('anomalies');
            const request = store.add(anomaly);
            
            request.onsuccess = () => {
                resolve({ ...anomaly, id: request.result });
            };
            
            request.onerror = () => {
                reject(new Error('保存异常记录失败: ' + request.error));
            };
        });
    }

    /**
     * 更新商品异常状态
     * @param {number} productId - 商品ID
     * @param {boolean} isAnomaly - 是否为异常
     */
    async updateProductAnomalyStatus(productId, isAnomaly) {
        this.checkInitialized();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['products'], 'readwrite');
            const store = transaction.objectStore('products');

            const getRequest = store.get(productId);

            getRequest.onsuccess = () => {
                const product = getRequest.result;
                if (!product) {
                    reject(new Error(`商品ID ${productId} 不存在`));
                    return;
                }

                product.is_anomaly = isAnomaly;
                product.anomaly_updated_at = new Date().toISOString();

                const updateRequest = store.put(product);

                updateRequest.onsuccess = () => {
                    console.log(`✅ 商品 ${productId} 异常状态已更新为: ${isAnomaly}`);
                    resolve({ id: productId, is_anomaly: isAnomaly });
                };

                updateRequest.onerror = () => {
                    reject(new Error('更新商品异常状态失败: ' + updateRequest.error));
                };
            };

            getRequest.onerror = () => {
                reject(new Error('获取商品信息失败: ' + getRequest.error));
            };
        });
    }

    /**
     * 获取异常商品列表
     * @param {Array} categoryIds - 分类ID数组，空数组表示获取所有分类
     * @returns {Promise<Array>} 异常商品列表
     */
    async getAnomalyProducts(categoryIds = []) {
        this.checkInitialized();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['products'], 'readonly');
            const store = transaction.objectStore('products');
            const request = store.getAll();

            request.onsuccess = () => {
                let products = request.result || [];

                // 过滤异常商品
                products = products.filter(product => product.is_anomaly === true);

                // 如果指定了分类，按分类过滤
                if (categoryIds.length > 0) {
                    products = products.filter(product =>
                        categoryIds.includes(product.category_id)
                    );
                }

                // 按更新时间倒序排列
                products.sort((a, b) => {
                    const timeA = new Date(a.anomaly_updated_at || a.updated_at || 0);
                    const timeB = new Date(b.anomaly_updated_at || b.updated_at || 0);
                    return timeB - timeA;
                });

                console.log(`📊 获取异常商品: ${products.length}个 (分类过滤: ${categoryIds.join(',')})`);
                resolve(products);
            };

            request.onerror = () => {
                reject(new Error('获取异常商品列表失败: ' + request.error));
            };
        });
    }

    /**
     * 获取异常商品数量统计
     * @param {Array} categoryIds - 分类ID数组，空数组表示所有分类
     * @returns {Promise<number>} 异常商品总数
     */
    async getAnomalyProductsCount(categoryIds = []) {
        this.checkInitialized();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['products'], 'readonly');
            const store = transaction.objectStore('products');
            const request = store.getAll();

            request.onsuccess = () => {
                let products = request.result || [];

                // 过滤异常商品
                let anomalyProducts = products.filter(product => product.is_anomaly === true);

                // 如果指定了分类，按分类过滤
                if (categoryIds.length > 0) {
                    anomalyProducts = anomalyProducts.filter(product =>
                        categoryIds.includes(product.category_id)
                    );
                }

                const count = anomalyProducts.length;
                console.log(`📊 异常商品数量统计: ${count}个`);
                resolve(count);
            };

            request.onerror = () => {
                reject(new Error('获取异常商品数量失败: ' + request.error));
            };
        });
    }

    /**
     * 导出所有数据
     */
    async exportAllData() {
        this.checkInitialized();
        
        try {
            const categories = await this.getCategories();
            const products = await this.getAllProducts();
            // 快照数据已移除，使用商品时间序列数据进行导出
            const timeSeriesData = await this.getBatchTimeSeriesStats();
            
            // ultrathink: 使用简化的异常商品而不是旧的anomalies表
            const anomalies = await this.getAnomalyProducts();
            
            return {
                exportDate: new Date(),
                version: '2.0',
                data: {
                    categories,
                    products,
                    timeSeriesData,
                    anomalies
                }
            };
        } catch (error) {
            throw new Error('导出数据失败: ' + error.message);
        }
    }

    /**
     * 导出数据 (exportAllData的别名)
     */
    async exportData() {
        return await this.exportAllData();
    }

    /**
     * 导入数据
     */
    async importData(exportData) {
        this.checkInitialized();
        
        if (!exportData.data) {
            throw new Error('无效的导入数据格式');
        }
        
        try {
            const { categories, products, anomalies, timeSeriesData } = exportData.data;

            // 清空现有数据
            await this.clearAllData();

            // 导入分类
            if (categories) {
                for (const category of categories) {
                    await this.createCategory(category);
                }
            }

            // 导入商品
            if (products) {
                for (const product of products) {
                    await this.saveProduct(product);
                }
            }

            // ultrathink: 不再导入旧的异常记录，使用简化的is_anomaly字段
            // 异常标记已在商品数据中处理

            console.log('✅ 数据导入完成（快照功能已移除，使用商品时间序列数据）');
        } catch (error) {
            throw new Error('导入数据失败: ' + error.message);
        }
    }

    /**
     * 清空所有数据
     */
    async clearAllData() {
        this.checkInitialized();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['categories', 'products', 'anomalies'], 'readwrite');

            const stores = ['products', 'anomalies']; // 保留默认分类
            let completed = 0;

            stores.forEach(storeName => {
                const store = transaction.objectStore(storeName);
                const request = store.clear();

                request.onsuccess = () => {
                    completed++;
                    if (completed === stores.length) {
                        // 重新创建默认分类
                        this.ensureDefaultCategory().then(resolve).catch(reject);
                    }
                };
            });

            transaction.onerror = () => {
                reject(new Error('清空数据失败: ' + transaction.error));
            };
        });
    }
}

/**
 * 简化版分类管理器 - 为了保持与sidepanel.js的兼容性
 * 实际上是LocalDataManager分类方法的包装器
 */
class SimpleCategoryManager {
    constructor(localDataManager) {
        this.dataManager = localDataManager;
    }

    async getCategories() {
        return await this.dataManager.getCategories();
    }

    async createCategory(name, description = '', color = '#6366f1') {
        return await this.dataManager.createCategory(name, description, color);
    }

    async getCategoryById(id) {
        return await this.dataManager.getCategoryById(id);
    }

    async updateCategory(id, updates) {
        return await this.dataManager.updateCategory(id, updates);
    }

    async deleteCategory(id) {
        return await this.dataManager.deleteCategory(id);
    }
}

// 导出给其他模块使用
window.LocalDataManager = LocalDataManager;
window.SimpleCategoryManager = SimpleCategoryManager;
// DataMigrator is now provided by lib/data-migrator.js
