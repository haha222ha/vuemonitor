<template>
  <div class="discovery-search">
    <div class="search-header">
      <div class="search-box">
        <el-input
          v-model="searchQuery"
          placeholder="搜索商品标题、关键词、店铺名..."
          size="large"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <Search />
          </template>
          <template #suffix>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
          </template>
        </el-input>
      </div>

      <div class="search-filters">
        <el-select
          v-model="filterOptions.category"
          placeholder="商品分类"
          class="filter-item"
        >
          <el-option label="全部" value="" />
          <el-option label="服饰鞋包" value="fashion" />
          <el-option label="美妆护肤" value="beauty" />
          <el-option label="家居生活" value="home" />
          <el-option label="数码电子" value="digital" />
          <el-option label="食品零食" value="food" />
          <el-option label="母婴用品" value="baby" />
        </el-select>

        <el-select
          v-model="filterOptions.priceRange"
          placeholder="价格区间"
          class="filter-item"
        >
          <el-option label="全部" value="" />
          <el-option label="0-50" value="0-50" />
          <el-option label="50-100" value="50-100" />
          <el-option label="100-300" value="100-300" />
          <el-option label="300-500" value="300-500" />
          <el-option label="500+" value="500+" />
        </el-select>

        <el-select
          v-model="filterOptions.sortBy"
          placeholder="排序方式"
          class="filter-item"
        >
          <el-option label="综合排序" value="default" />
          <el-option label="销量优先" value="sales" />
          <el-option label="价格从低到高" value="price_asc" />
          <el-option label="价格从高到低" value="price_desc" />
          <el-option label="热度优先" value="hot" />
        </el-select>
      </div>
    </div>

    <div class="search-stats">
      <span class="stats-text">共找到 <strong>{{ totalCount }}</strong> 件商品</span>
      <span v-if="searchQuery" class="stats-tag">关键词: {{ searchQuery }}</span>
      <span v-if="filterOptions.category" class="stats-tag">分类: {{ getCategoryLabel(filterOptions.category) }}</span>
    </div>

    <div class="search-content">
      <div class="results-grid">
        <div
          v-for="product in products"
          :key="product.id"
          class="result-card"
          @click="viewProduct(product)"
        >
          <div class="card-image">
            <img :src="product.imageUrl" :alt="product.title" loading="lazy">
            <div v-if="product.isHot" class="card-badge card-badge--hot">🔥 爆款</div>
            <div v-if="product.isNew" class="card-badge card-badge--new">✨ 新品</div>
          </div>
          <div class="card-info">
            <h3 class="card-title">{{ truncateText(product.title, 40) }}</h3>
            <p class="card-tags">
              <span
                v-for="tag in product.tags.slice(0, 3)"
                :key="tag"
                class="tag"
              >
                #{{ tag }}
              </span>
            </p>
            <div class="card-metrics">
              <span class="metric">
                <TopRight />
                {{ formatNumber(product.sales) }} 销量
              </span>
              <span class="metric">
                <Star />
                {{ formatNumber(product.likes) }}
              </span>
            </div>
            <div class="card-footer">
              <span class="card-price">¥{{ formatPrice(product.price) }}</span>
              <span class="card-shop">{{ truncateText(product.shopName, 12) }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="search-sidebar">
        <div class="sidebar-section">
          <h4 class="section-title">搜索热度</h4>
          <div class="hot-keywords">
            <button
              v-for="(keyword, index) in hotKeywords"
              :key="keyword"
              :class="['keyword-btn', { 'top': index < 3 }]"
              @click="searchQuery = keyword; handleSearch()"
            >
              <span v-if="index < 3" class="keyword-rank">{{ index + 1 }}</span>
              {{ keyword }}
            </button>
          </div>
        </div>

        <div class="sidebar-section">
          <h4 class="section-title">分类浏览</h4>
          <div class="category-list">
            <button
              v-for="cat in categoryList"
              :key="cat.value"
              :class="['category-btn', { active: filterOptions.category === cat.value }]"
              @click="filterOptions.category = cat.value; handleSearch()"
            >
              <span class="category-icon">{{ cat.icon }}</span>
              <span class="category-name">{{ cat.label }}</span>
              <span class="category-count">{{ cat.count }}</span>
            </button>
          </div>
        </div>

        <div class="sidebar-section upgrade-section">
          <h4 class="section-title">🚀 升级高级版</h4>
          <p class="upgrade-desc">解锁完整数据洞察能力</p>
          <ul class="upgrade-features">
            <li>✓ 完整商品标题查看</li>
            <li>✓ 历史价格趋势分析</li>
            <li>✓ 竞品对比分析</li>
            <li>✓ 爆品洞察报告</li>
          </ul>
          <el-button type="primary" class="upgrade-btn">立即升级</el-button>
        </div>
      </div>
    </div>

    <div v-if="hasMore" class="search-footer">
      <el-button
        type="primary"
        :loading="loading"
        class="load-more-btn"
        @click="loadMore"
      >
        {{ loading ? '加载中...' : '加载更多' }}
      </el-button>
    </div>

    <div v-if="products.length === 0 && !loading" class="search-empty">
      <el-empty description="未找到相关商品，试试其他关键词" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { Search, TopRight, Star } from "@element-plus/icons-vue";

interface Product {
  id: string;
  title: string;
  imageUrl: string;
  price: number;
  sales: number;
  likes: number;
  shopName: string;
  tags: string[];
  isHot?: boolean;
  isNew?: boolean;
}

const emit = defineEmits<{
  (e: "search", query: string, filters: Record<string, string>): void;
  (e: "view", product: Product): void;
}>();

const searchQuery = ref("");
const loading = ref(false);
const totalCount = ref(0);
const currentPage = ref(1);

const filterOptions = reactive({
  category: "",
  priceRange: "",
  sortBy: "default",
});

const products = ref<Product[]>([]);
const hasMore = ref(true);

const hotKeywords = [
  "夏季穿搭",
  "护肤套装",
  "家居好物",
  "数码配件",
  "零食推荐",
  "母婴用品",
  "网红爆款",
  "平价替代",
];

const categoryList = [
  { value: "fashion", label: "服饰鞋包", icon: "👔", count: 12580 },
  { value: "beauty", label: "美妆护肤", icon: "💄", count: 8920 },
  { value: "home", label: "家居生活", icon: "🏠", count: 6540 },
  { value: "digital", label: "数码电子", icon: "📱", count: 4320 },
  { value: "food", label: "食品零食", icon: "🍪", count: 9870 },
  { value: "baby", label: "母婴用品", icon: "👶", count: 3450 },
];

function handleSearch() {
  currentPage.value = 1;
  hasMore.value = true;
  fetchProducts();
}

async function fetchProducts() {
  loading.value = true;
  try {
    const priceRange = filterOptions.priceRange;
    let minPrice: number | undefined;
    let maxPrice: number | undefined;
    if (priceRange) {
      const parts = priceRange.split("-");
      if (parts[0]) minPrice = Number(parts[0]);
      if (parts[1]) maxPrice = Number(parts[1]);
    }

    const sortByMap: Record<string, string> = {
      default: "relevance",
      sales: "sales_desc",
      price_asc: "price_asc",
      price_desc: "price_desc",
      hot: "sales_desc",
    };

    const response = (await window.electronAPI?.invoke?.("discovery:search", {
      keyword: searchQuery.value,
      page: currentPage.value,
      page_size: 20,
      min_price: minPrice,
      max_price: maxPrice,
      sort_by: sortByMap[filterOptions.sortBy] || "relevance",
    })) as { data?: { items?: Record<string, unknown>[]; total?: number } } | undefined;

    const items = response?.data?.items || [];
    const total = response?.data?.total || 0;

    const mapped = items.map((item: Record<string, unknown>) => ({
      id: item.goods_id as string || item.ref as string,
      title: item.title as string || "",
      imageUrl: (item.image_url as string) || "",
      price: (item.deal_price as number) ?? 0,
      sales: (item.sold_num as number) ?? 0,
      likes: 0,
      shopName: item.store_name as string || "",
      tags: item.keyword ? [item.keyword as string] : [],
      isHot: (item.sold_num as number) > 1000,
      isNew: false,
    }));

    if (currentPage.value === 1) {
      products.value = mapped;
    } else {
      products.value = [...products.value, ...mapped];
    }

    totalCount.value = total;
    hasMore.value = products.value.length < total;
  } catch (error) {
    console.error("搜索失败:", error);
  } finally {
    loading.value = false;
  }
}

function loadMore() {
  currentPage.value++;
  fetchProducts();
}

function viewProduct(product: Product) {
  emit("view", product);
}

function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + "...";
}

function formatPrice(price: number): string {
  return price.toFixed(2);
}

function formatNumber(num: number): string {
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + "w";
  }
  return num.toString();
}

function getCategoryLabel(value: string): string {
  const cat = categoryList.find((c) => c.value === value);
  return cat?.label || "";
}

onMounted(() => {
});
</script>

<style lang="scss" scoped>
.discovery-search {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.search-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 24px;
  border-radius: 12px;
}

.search-box {
  margin-bottom: 16px;
}

.search-box :deep(.el-input__wrapper) {
  border-radius: 8px;
  background: #fff;
}

.search-filters {
  display: flex;
  gap: 12px;
}

.filter-item {
  width: 140px;

  :deep(.el-input__wrapper) {
    background: rgba(255, 255, 255, 0.9);
    border-radius: 6px;
  }
}

.search-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: #fafafa;
  border-radius: 8px;
}

.stats-text {
  font-size: 14px;
  color: #666;
}

.stats-tag {
  font-size: 12px;
  color: #666;
  background: #fff;
  padding: 4px 10px;
  border-radius: 12px;
  border: 1px solid #eee;
}

.search-content {
  display: flex;
  gap: 20px;
}

.results-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.result-card {
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  }
}

.card-image {
  position: relative;
  width: 100%;
  padding-top: 100%;
  overflow: hidden;
  background: #fafafa;

  img {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.card-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;

  &--hot {
    background: linear-gradient(135deg, #ff6b6b, #ee5a5a);
    color: #fff;
  }

  &--new {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: #fff;
  }
}

.card-info {
  padding: 12px;
}

.card-title {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin: 0 0 8px 0;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0 0 10px 0;
}

.tag {
  font-size: 11px;
  color: #667eea;
  background: #f0f0ff;
  padding: 2px 8px;
  border-radius: 4px;
}

.card-metrics {
  display: flex;
  gap: 16px;
  margin-bottom: 10px;
}

.metric {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #666;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid #f5f5f5;
}

.card-price {
  font-size: 18px;
  font-weight: 600;
  color: #e74c3c;
}

.card-shop {
  font-size: 12px;
  color: #999;
}

.search-sidebar {
  width: 260px;
  flex-shrink: 0;
}

.sidebar-section {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: #333;
}

.hot-keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.keyword-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: none;
  border-radius: 16px;
  background: #f5f5f5;
  font-size: 12px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #e8e8ff;
    color: #667eea;
  }

  &.top {
    background: linear-gradient(135deg, #fff3e0, #ffe0b2);
    color: #e65100;
  }
}

.keyword-rank {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #ff9800;
  color: #fff;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.category-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: none;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #f5f5f5;
  }

  &.active {
    background: #f0f0ff;
    color: #667eea;
  }
}

.category-icon {
  font-size: 18px;
}

.category-name {
  flex: 1;
  text-align: left;
  font-size: 13px;
}

.category-count {
  font-size: 12px;
  color: #999;
}

.upgrade-section {
  background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
  border: 1px solid #ffcc80;
}

.upgrade-desc {
  font-size: 12px;
  color: #e65100;
  margin: 4px 0 12px 0;
}

.upgrade-features {
  list-style: none;
  padding: 0;
  margin: 0 0 16px 0;
}

.upgrade-features li {
  font-size: 12px;
  color: #666;
  padding: 4px 0;
}

.upgrade-btn {
  width: 100%;
  background: linear-gradient(135deg, #ff9800, #f57c00);
  border: none;

  &:hover {
    background: linear-gradient(135deg, #f57c00, #e65100);
  }
}

.search-footer {
  text-align: center;
  padding: 20px;
}

.load-more-btn {
  min-width: 160px;
}

.search-empty {
  padding: 60px 0;
  text-align: center;
}
</style>