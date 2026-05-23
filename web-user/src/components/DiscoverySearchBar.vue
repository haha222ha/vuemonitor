<template>
  <div class="discovery-search-bar">
    <div class="discovery-search-bar__main">
      <el-input
        v-model="keyword"
        placeholder="搜索商品标题或店铺名称..."
        size="large"
        clearable
        @keyup.enter="$emit('search')"
        @input="$emit('live-search')"
        class="discovery-search-bar__input"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
        <template #append>
          <el-button type="primary" @click="$emit('search')">搜索</el-button>
        </template>
      </el-input>

      <el-radio-group v-model="mode" size="small" class="discovery-search-bar__mode">
        <el-radio-button value="goods">商品</el-radio-button>
        <el-radio-button value="stores">店铺</el-radio-button>
      </el-radio-group>
    </div>

    <div class="discovery-search-bar__filters">
      <div class="discovery-search-bar__filter-group">
        <span class="discovery-search-bar__filter-label">价格区间</span>
        <el-input-number v-model="priceMin" :min="0" :precision="0" placeholder="最低价" size="small" controls-position="right" class="discovery-search-bar__filter-input" />
        <span class="discovery-search-bar__filter-sep">-</span>
        <el-input-number v-model="priceMax" :min="0" :precision="0" placeholder="最高价" size="small" controls-position="right" class="discovery-search-bar__filter-input" />
      </div>

      <div class="discovery-search-bar__filter-group">
        <span class="discovery-search-bar__filter-label">最低销量</span>
        <el-input-number v-model="minSales" :min="0" :precision="0" placeholder="0" size="small" controls-position="right" class="discovery-search-bar__filter-input" />
      </div>

      <div class="discovery-search-bar__filter-group">
        <span class="discovery-search-bar__filter-label">排序</span>
        <el-select v-model="sortBy" size="small" class="discovery-search-bar__filter-select">
          <el-option label="相关度" value="relevance" />
          <el-option label="价格从低到高" value="price_asc" />
          <el-option label="价格从高到低" value="price_desc" />
          <el-option label="销量从高到低" value="sales_desc" />
          <el-option label="销量从低到高" value="sales_asc" />
        </el-select>
      </div>

      <el-button size="small" text @click="resetFilters">
        <el-icon><RefreshLeft /></el-icon>
        重置
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Search, RefreshLeft } from "@element-plus/icons-vue";

const keyword = defineModel<string>("keyword");
const mode = defineModel<"goods" | "stores">("mode");
const priceMin = defineModel<number>("priceMin", { default: undefined as unknown as number });
const priceMax = defineModel<number>("priceMax", { default: undefined as unknown as number });
const minSales = defineModel<number>("minSales", { default: undefined as unknown as number });
const sortBy = defineModel<string>("sortBy", { default: "relevance" });

defineEmits<{ search: []; 'live-search': [] }>();

function resetFilters() {
  priceMin.value = undefined as unknown as number;
  priceMax.value = undefined as unknown as number;
  minSales.value = undefined as unknown as number;
  sortBy.value = "relevance";
}
</script>

<style scoped>
.discovery-search-bar { margin-bottom: 16px; }
.discovery-search-bar__main { display: flex; gap: 12px; align-items: center; }
.discovery-search-bar__input { flex: 1; }
.discovery-search-bar__mode { flex-shrink: 0; }
.discovery-search-bar__filters { display: flex; gap: 12px; align-items: center; margin-top: 8px; flex-wrap: wrap; }
.discovery-search-bar__filter-group { display: flex; align-items: center; gap: 4px; }
.discovery-search-bar__filter-label { font-size: 12px; color: #8a8a9a; white-space: nowrap; }
.discovery-search-bar__filter-input { width: 100px; }
.discovery-search-bar__filter-sep { color: #5a5a6a; font-size: 12px; }
.discovery-search-bar__filter-select { width: 140px; }
</style>
