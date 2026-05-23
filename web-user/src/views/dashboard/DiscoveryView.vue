<template>
  <div class="discovery-view">
    <div class="discovery-header">
      <h2>商品发现</h2>
      <p class="discovery-desc">从百万级小红书商品数据库中发现选品机会</p>
      <div class="discovery-quota">
        <el-tag :type="quotaTagType" effect="plain">今日剩余 {{ remainingSearch }} 次搜索</el-tag>
        <el-tag v-if="plan === 'free'" type="warning" effect="plain" class="discovery-upgrade-tag">🔒 升级Pro查看完整数据</el-tag>
        <div v-if="dbStats" class="discovery-db-stats">
          <span>{{ formatStatNumber(dbStats.total_goods) }} 商品</span>
          <span>{{ formatStatNumber(dbStats.total_stores) }} 店铺</span>
        </div>
      </div>
    </div>

    <DiscoverySearchBar
      v-model:keyword="searchKeyword"
      v-model:mode="searchMode"
      v-model:price-min="filterPriceMin"
      v-model:price-max="filterPriceMax"
      v-model:min-sales="filterMinSales"
      v-model:sort-by="filterSortBy"
      @search="handleSearchWithFilters"
      @live-search="handleLiveSearch"
    />

    <div class="discovery-tabs">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="商品搜索" name="goods">
          <div v-if="searchLoading" class="discovery-loading"><el-skeleton :rows="5" animated /></div>
          <div v-else-if="goodsResults.length > 0" class="discovery-grid">
            <DiscoveryGoodsCard
              v-for="item in goodsResults"
              :key="item.ref"
              :item="item"
              @add-to-monitor="addToMonitor"
            />
          </div>
          <div v-else-if="hasSearched" class="empty-state">
            <div class="empty-icon">🔍</div>
            <p>未找到匹配商品</p>
            <p class="empty-hint">尝试更换关键词搜索</p>
          </div>
          <div v-else class="empty-state">
            <div class="empty-icon">🧭</div>
            <p>搜索小红书商品</p>
            <p class="empty-hint">输入关键词搜索商品标题，找到后一键加入监控</p>
          </div>
        </el-tab-pane>

        <el-tab-pane label="店铺搜索" name="stores">
          <div v-if="searchLoading" class="discovery-loading"><el-skeleton :rows="3" animated /></div>
          <div v-else-if="storeResults.length > 0" class="discovery-stores">
            <DiscoveryStoreCard
              v-for="store in storeResults"
              :key="store.ref"
              :store="store"
              @view-goods="viewStoreGoods"
            />
          </div>
          <div v-else-if="hasSearched" class="empty-state">
            <div class="empty-icon">🔍</div>
            <p>未找到匹配店铺</p>
          </div>
        </el-tab-pane>

        <el-tab-pane name="burst">
          <template #label>
            <span>爆品洞察 <el-tag v-if="plan === 'free'" size="small" type="warning" effect="plain" class="pro-badge">Pro</el-tag></span>
          </template>
          <DiscoveryBurstList @add-to-monitor="addToMonitor" />
        </el-tab-pane>

        <el-tab-pane label="热门关键词" name="keywords">
          <div class="discovery-keywords" v-if="keywords.length > 0">
            <el-check-tag
              v-for="kw in keywords"
              :key="kw.keyword"
              @change="quickSearch(kw.keyword)"
              class="discovery-keyword-tag"
            >
              {{ kw.keyword }}
              <span class="discovery-keyword-count">{{ kw.item_count }}</span>
            </el-check-tag>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <div v-if="totalPages > 1" class="discovery-pagination">
      <el-pagination
        v-model:current-page="currentPage"
        :total="totalItems"
        :page-size="pageSize"
        layout="prev, pager, next"
        @current-change="(page: number) => handlePageChange(page)"
      />
    </div>

    <el-dialog
      v-model="showStoreGoods"
      :title="`店铺商品 - ${selectedStore?.store_name || ''}`"
      width="700px"
    >
      <div v-if="storeGoodsLoading" class="discovery-loading"><el-skeleton :rows="4" animated /></div>
      <div v-else class="discovery-store-goods">
        <DiscoveryGoodsCard
          v-for="item in storeGoods"
          :key="item.ref"
          :item="item"
          :compact="true"
          @add-to-monitor="addToMonitor"
        />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import DiscoverySearchBar from "../../components/DiscoverySearchBar.vue";
import DiscoveryGoodsCard from "../../components/DiscoveryGoodsCard.vue";
import DiscoveryStoreCard from "../../components/DiscoveryStoreCard.vue";
import DiscoveryBurstList from "../../components/DiscoveryBurstList.vue";
import { useDiscoveryData } from "../../composables/useDiscoveryData";
import { useAuthStore } from "../../stores/auth";
import api from "../../utils/api";

const authStore = useAuthStore();

const filterPriceMin = ref<number | undefined>(undefined);
const filterPriceMax = ref<number | undefined>(undefined);
const filterMinSales = ref<number | undefined>(undefined);
const filterSortBy = ref("relevance");

const {
  searchKeyword,
  searchMode,
  activeTab,
  currentPage,
  pageSize,
  hasSearched,
  searchLoading,
  storeGoodsLoading,
  goodsResults,
  storeResults,
  storeGoods,
  hotGoods,
  keywords,
  totalItems,
  totalPages,
  remainingSearch,
  dbStats,
  selectedStore,
  showStoreGoods,
  plan,
  handleSearch,
  handleTabChange,
  handlePageChange,
  viewStoreGoods,
  fetchKeywords,
  fetchQuota,
  quickSearch,
  debouncedSearch,
  cancelDebouncedSearch,
} = useDiscoveryData();

const quotaTagType = computed(() => {
  if (remainingSearch.value <= 0) return "danger";
  if (remainingSearch.value <= 3) return "warning";
  return "info";
});

function handleSearchWithFilters() {
  cancelDebouncedSearch();
  handleSearch({
    minPrice: filterPriceMin.value,
    maxPrice: filterPriceMax.value,
    minSold: filterMinSales.value,
    sortBy: filterSortBy.value,
  });
}

function handleLiveSearch() {
  if (!searchKeyword.value.trim()) {
    cancelDebouncedSearch();
    return;
  }
  debouncedSearch({
    minPrice: filterPriceMin.value,
    maxPrice: filterPriceMax.value,
    minSold: filterMinSales.value,
    sortBy: filterSortBy.value,
  });
}

function formatStatNumber(num: number): string {
  if (num >= 10000) return `${(num / 10000).toFixed(0)}万+`;
  if (num >= 1000) return `${(num / 1000).toFixed(0)}k+`;
  return String(num);
}

async function addToMonitor(item: { ref: string; title?: string }) {
  try {
    await ElMessageBox.confirm(
      `确定将商品「${item.title || ""}」加入监控？`,
      "加入监控",
      { confirmButtonText: "确定", cancelButtonText: "取消", type: "info" }
    );

    await api.post("/discovery/add-to-monitor", {
      ref_id: item.ref,
      product_name: item.title,
      mode: "goods",
    });

    ElMessage.success("已加入监控列表");
  } catch (err: any) {
    if (err === "cancel") return;
    if (err?.response?.data?.code === 42013) {
      ElMessageBox.alert(
        "免费版最多监控3个商品，升级Pro可监控50个",
        "商品数量已达上限",
        { confirmButtonText: "升级Pro", type: "warning" }
      ).then(() => {
        window.location.hash = "#/pricing";
      });
    }
  }
}

onMounted(() => {
  authStore.fetchUser();
  fetchQuota();
  fetchKeywords();
});
</script>

<style scoped>
.discovery-view { padding: 4px; }
.discovery-header { margin-bottom: 24px; }
.discovery-header h2 { font-size: 20px; font-weight: 600; color: #e0e0e6; margin: 0 0 4px; }
.discovery-desc { color: #6a6a7a; font-size: 14px; margin: 0 0 12px; }
.discovery-quota { display: flex; align-items: center; gap: 8px; }
.discovery-upgrade-tag { cursor: pointer; }
.discovery-db-stats { display: flex; gap: 12px; font-size: 12px; color: #5a5a6a; margin-left: 8px; }
.discovery-tabs { margin-top: 20px; }
.pro-badge { margin-left: 4px; font-size: 10px; vertical-align: middle; }
.discovery-locked-tab { display: flex; justify-content: center; padding: 60px 0; }
.discovery-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; margin-top: 16px; }
.discovery-stores { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; margin-top: 16px; }
.discovery-keywords { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
.discovery-keyword-tag { cursor: pointer; }
.discovery-keyword-count { font-size: 10px; color: #5a5a6a; margin-left: 4px; }
.discovery-pagination { display: flex; justify-content: center; margin-top: 24px; }
.discovery-loading { padding: 20px; }
.discovery-store-goods { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
.empty-state { text-align: center; padding: 60px 0; color: #6a6a7a; }
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-hint { font-size: 13px; color: #5a5a6a; margin-top: 4px; }
</style>
