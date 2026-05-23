<template>
  <div class="waterfall">
    <div class="waterfall__header">
      <div class="waterfall__filters">
        <el-select
          v-model="selectedCategory"
          placeholder="选择分类"
          class="filter-select"
        >
          <el-option label="全部" value="" />
          <el-option
            v-for="cat in categories"
            :key="cat.id"
            :label="cat.name"
            :value="cat.id"
          />
        </el-select>
        <el-select
          v-model="sortBy"
          placeholder="排序方式"
          class="filter-select"
        >
          <el-option label="默认" value="default" />
          <el-option label="销量最高" value="sales" />
          <el-option label="价格最高" value="price_desc" />
          <el-option label="价格最低" value="price_asc" />
          <el-option label="最新采集" value="latest" />
        </el-select>
        <el-input
          v-model="searchKeyword"
          placeholder="搜索商品ID"
          class="search-input"
          @input="handleSearch"
        >
          <template #prefix>
            <Search />
          </template>
        </el-input>
      </div>
      <div class="waterfall__view-toggle">
        <button
          :class="['view-btn', { active: viewMode === 'grid' }]"
          title="网格视图"
          @click="viewMode = 'grid'"
        >
          <Grid />
        </button>
        <button
          :class="['view-btn', { active: viewMode === 'list' }]"
          title="列表视图"
          @click="viewMode = 'list'"
        >
          <List />
        </button>
      </div>
    </div>

    <div
      ref="waterfallContainer"
      :class="['waterfall__content', `waterfall__content--${viewMode}`]"
    >
      <div
        v-for="product in displayedProducts"
        :key="product.id"
        class="waterfall-card"
        @click="$emit('select', product)"
      >
        <div class="waterfall-card__image">
          <img
            :src="product.imageUrl || defaultImage"
            :alt="product.title"
            class="product-image"
            loading="lazy"
          >
          <div
            v-if="product.isHot"
            class="waterfall-card__badge waterfall-card__badge--hot"
          >
            🔥 爆款
          </div>
          <div
            v-if="product.isNew"
            class="waterfall-card__badge waterfall-card__badge--new"
          >
            ✨ 新品
          </div>
        </div>
        <div class="waterfall-card__info">
          <h3 class="waterfall-card__title">{{ truncateTitle(product.title) }}</h3>
          <div class="waterfall-card__price">
            <span class="price-current">¥{{ formatPrice(product.price) }}</span>
            <span v-if="product.originalPrice" class="price-original">
              ¥{{ formatPrice(product.originalPrice) }}
            </span>
          </div>
          <div class="waterfall-card__stats">
            <span class="stat-item">
              <TopRight />
              {{ formatNumber(product.sales) }} 销量
            </span>
            <span class="stat-item">
              <Star />
              {{ formatNumber(product.likes) }}
            </span>
          </div>
          <div class="waterfall-card__footer">
            <span class="waterfall-card__shop">{{ product.shopName }}</span>
            <span class="waterfall-card__time">{{ formatDate(product.collectedAt) }}</span>
          </div>
        </div>
        <div class="waterfall-card__actions">
          <button class="action-btn action-btn--collect" @click.stop="collectProduct(product)">
            <Download />
            <span>采集</span>
          </button>
          <button class="action-btn action-btn--view" @click.stop="viewProduct(product)">
            <View />
            <span>详情</span>
          </button>
        </div>
      </div>
    </div>

    <div v-if="displayedProducts.length === 0" class="waterfall__empty">
      <el-empty description="暂无商品数据" />
    </div>

    <div v-if="hasMore" class="waterfall__load-more">
      <el-button
        type="primary"
        :loading="loading"
        class="load-more-btn"
        @click="loadMore"
      >
        {{ loading ? '加载中...' : '加载更多' }}
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import {
  Search,
  Grid,
  List,
  TopRight,
  Star,
  Download,
  View,
} from "@element-plus/icons-vue";

interface Product {
  id: string;
  title: string;
  imageUrl: string;
  price: number;
  originalPrice?: number;
  sales: number;
  likes: number;
  shopName: string;
  collectedAt: string;
  isHot?: boolean;
  isNew?: boolean;
}

interface Category {
  id: string;
  name: string;
}

const props = defineProps<{
  products: Product[];
  categories?: Category[];
}>();

const emit = defineEmits<{
  (e: "select", product: Product): void;
  (e: "collect", product: Product): void;
  (e: "view", product: Product): void;
  (e: "load-more"): void;
}>();

const defaultImage =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 200 200'%3E%3Crect fill='%23f5f5f5' width='200' height='200'/%3E%3Ctext fill='%23ccc' font-family='sans-serif' font-size='14' x='50%25' y='50%25' text-anchor='middle' dominant-baseline='middle'%3E商品图片%3C/text%3E%3C/svg%3E";

const viewMode = ref<"grid" | "list">("grid");
const selectedCategory = ref("");
const sortBy = ref("default");
const searchKeyword = ref("");
const loading = ref(false);
const pageSize = 20;
const currentPage = ref(1);

const categories = computed(() => props.categories || []);

const filteredProducts = computed(() => {
  let result = [...props.products];

  if (selectedCategory.value) {
    result = result.filter((p) => p.id.includes(selectedCategory.value));
  }

  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase();
    result = result.filter(
      (p) =>
        p.id.toLowerCase().includes(keyword) ||
        p.title.toLowerCase().includes(keyword)
    );
  }

  switch (sortBy.value) {
    case "sales":
      result.sort((a, b) => b.sales - a.sales);
      break;
    case "price_desc":
      result.sort((a, b) => b.price - a.price);
      break;
    case "price_asc":
      result.sort((a, b) => a.price - b.price);
      break;
    case "latest":
      result.sort(
        (a, b) =>
          new Date(b.collectedAt).getTime() - new Date(a.collectedAt).getTime()
      );
      break;
  }

  return result;
});

const displayedProducts = computed(() => {
  return filteredProducts.value.slice(0, currentPage.value * pageSize);
});

const hasMore = computed(() => {
  return displayedProducts.value.length < filteredProducts.value.length;
});

function handleSearch() {
  currentPage.value = 1;
}

function loadMore() {
  loading.value = true;
  setTimeout(() => {
    currentPage.value++;
    loading.value = false;
    emit("load-more");
  }, 500);
}

function truncateTitle(title: string): string {
  if (title.length <= 30) return title;
  return title.slice(0, 30) + "...";
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

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (days === 0) return "今天";
  if (days === 1) return "昨天";
  if (days < 7) return `${days}天前`;
  return date.toLocaleDateString("zh-CN");
}

function collectProduct(product: Product) {
  emit("collect", product);
}

function viewProduct(product: Product) {
  emit("view", product);
}

onMounted(() => {
  currentPage.value = 1;
});
</script>

<style lang="scss" scoped>
.waterfall {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.waterfall__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #eee;
}

.waterfall__filters {
  display: flex;
  gap: 12px;
  flex: 1;
}

.filter-select {
  width: 120px;
}

.search-input {
  width: 200px;
}

.waterfall__view-toggle {
  display: flex;
  gap: 4px;
  background: #f5f5f5;
  border-radius: 6px;
  padding: 4px;
}

.view-btn {
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #666;
  transition: all 0.2s;

  &:hover {
    background: #eee;
  }

  &.active {
    background: #fff;
    color: #409eff;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }
}

.waterfall__content {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;

  &--list {
    grid-template-columns: 1fr;
  }
}

.waterfall-card {
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  }

  &__image {
    position: relative;
    width: 100%;
    padding-top: 100%;
    overflow: hidden;
    background: #fafafa;
  }

  &__badge {
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
}

.product-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.waterfall-card__info {
  padding: 12px;
}

.waterfall-card__title {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin: 0 0 8px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
}

.waterfall-card__price {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 8px;
}

.price-current {
  font-size: 18px;
  font-weight: 600;
  color: #e74c3c;
}

.price-original {
  font-size: 12px;
  color: #999;
  text-decoration: line-through;
}

.waterfall-card__stats {
  display: flex;
  gap: 16px;
  margin-bottom: 8px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #666;
}

.waterfall-card__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid #f5f5f5;
}

.waterfall-card__shop {
  font-size: 12px;
  color: #999;
  max-width: 60%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.waterfall-card__time {
  font-size: 11px;
  color: #bbb;
}

.waterfall-card__actions {
  position: absolute;
  bottom: 12px;
  right: 12px;
  display: flex;
  gap: 8px;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.waterfall-card:hover .waterfall-card__actions {
  opacity: 1;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border: none;
  border-radius: 16px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;

  &--collect {
    background: rgba(231, 76, 60, 0.9);
    color: #fff;
  }

  &--view {
    background: rgba(64, 158, 255, 0.9);
    color: #fff;
  }

  &:hover {
    transform: scale(1.05);
  }
}

.waterfall__content--list .waterfall-card {
  display: flex;
  gap: 16px;

  &__image {
    width: 120px;
    height: 120px;
    padding-top: 0;
    flex-shrink: 0;
  }

  &__info {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  &__title {
    -webkit-line-clamp: 1;
  }
}

.waterfall__empty {
  padding: 60px 0;
}

.waterfall__load-more {
  text-align: center;
  padding: 20px;
}

.load-more-btn {
  min-width: 160px;
}
</style>