<template>
  <div class="discovery fade-in">
    <PageHeader title="商品发现" subtitle="从百万级小红书商品数据库中发现选品机会">
      <template #default>
        <div class="discovery__quota">
          <el-tag :type="quotaTagType" effect="plain">
            今日剩余 {{ remainingSearch }} 次搜索
          </el-tag>
          <el-tag v-if="permissionStore.plan === 'free'" type="warning" effect="plain" class="discovery__upgrade-tag">
            🔒 升级Pro查看完整数据
          </el-tag>
          <div v-if="dbStats" class="discovery__db-stats">
            <span>{{ formatStatNumber(dbStats.total_goods) }} 商品</span>
            <span>{{ formatStatNumber(dbStats.total_stores) }} 店铺</span>
          </div>
        </div>
      </template>
    </PageHeader>

    <DiscoverySearchBar
      v-model:keyword="searchKeyword"
      v-model:mode="searchMode"
      v-model:price-min="filterPriceMin"
      v-model:price-max="filterPriceMax"
      v-model:min-sales="filterMinSales"
      v-model:sort-by="filterSortBy"
      @search="handleSearchWithFilters"
    />

    <div class="discovery__tabs">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="商品搜索" name="goods">
          <div v-if="searchLoading" class="discovery__loading">
            <el-skeleton :rows="5" animated />
          </div>
          <div v-else-if="goodsResults.length > 0" class="discovery__grid">
            <DiscoveryGoodsCard
              v-for="item in goodsResults"
              :key="item.ref"
              :item="item"
              @add-to-monitor="addToMonitor"
            />
          </div>
          <EmptyState
            v-else-if="hasSearched"
            :icon="Search"
            title="未找到匹配商品"
            description="尝试更换关键词搜索"
            compact
          />
          <EmptyState
            v-else
            :icon="Compass"
            title="搜索小红书商品"
            description="输入关键词搜索商品标题，找到后一键加入监控"
            compact
          />
        </el-tab-pane>

        <el-tab-pane label="店铺搜索" name="stores">
          <div v-if="searchLoading" class="discovery__loading">
            <el-skeleton :rows="3" animated />
          </div>
          <div v-else-if="storeResults.length > 0" class="discovery__stores">
            <DiscoveryStoreCard
              v-for="store in storeResults"
              :key="store.ref"
              :store="store"
              @view-goods="viewStoreGoods"
            />
          </div>
          <EmptyState
            v-else-if="hasSearched"
            :icon="Shop"
            title="未找到匹配店铺"
            compact
          />
        </el-tab-pane>

        <el-tab-pane name="burst">
          <template #label>
            <span>
              爆品洞察
              <el-tag v-if="permissionStore.plan === 'free'" size="small" type="warning" effect="plain" class="discovery__pro-badge">Pro</el-tag>
            </span>
          </template>
          <DiscoveryBurstList @add-to-monitor="addToMonitor" />
        </el-tab-pane>

        <el-tab-pane label="热门关键词" name="keywords">
          <div v-if="keywords.length > 0" class="discovery__keywords">
            <el-check-tag
              v-for="kw in keywords"
              :key="kw.keyword"
              class="discovery__keyword-tag"
              @change="quickSearch(kw.keyword)"
            >
              {{ kw.keyword }}
              <span class="discovery__keyword-count">{{ kw.item_count }}</span>
            </el-check-tag>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <div v-if="totalPages > 1" class="discovery__pagination">
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
      <div v-if="storeGoodsLoading" class="discovery__loading">
        <el-skeleton :rows="4" animated />
      </div>
      <div v-else class="discovery__store-goods">
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
import { computed, onMounted } from "vue";
import { Compass, Search, Shop } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import PageHeader from "../components/PageHeader.vue";
import EmptyState from "../components/EmptyState.vue";
import DiscoverySearchBar from "../components/DiscoverySearchBar.vue";
import DiscoveryGoodsCard from "../components/DiscoveryGoodsCard.vue";
import DiscoveryStoreCard from "../components/DiscoveryStoreCard.vue";
import DiscoveryBurstList from "../components/DiscoveryBurstList.vue";
import { useDiscoveryData } from "../composables/useDiscoveryData";
import { usePermissionStore } from "../stores/permission";
import { ref } from "vue";
import { useProductStore } from "../stores/product";
import api from "../utils/api";

const permissionStore = usePermissionStore();
const productStore = useProductStore();

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
    await productStore.fetchProducts();
  } catch (err: any) {
    if (err === "cancel") return;
    if (err?.response?.data?.code === 42013) {
      ElMessageBox.alert(
        "免费版最多监控3个商品，升级Pro可监控50个",
        "商品数量已达上限",
        { confirmButtonText: "升级Pro", type: "warning" }
      ).then(() => {
        window.location.hash = "#/license";
      });
    }
  }
}

onMounted(() => {
  permissionStore.fetchPermissions();
  fetchQuota();
  fetchKeywords();
});
</script>

<style scoped>
.discovery {
  padding: 24px;
  min-height: 100%;
}
.discovery__quota {
  display: flex;
  align-items: center;
  gap: 8px;
}
.discovery__upgrade-tag {
  cursor: pointer;
}
.discovery__db-stats {
  display: flex;
  gap: 12px;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-left: 8px;
}
.discovery__tabs {
  margin-top: 20px;
}
.discovery__pro-badge {
  margin-left: 4px;
  font-size: 10px;
  vertical-align: middle;
}
.discovery__locked-tab {
  display: flex;
  justify-content: center;
  padding: 60px 0;
}
.discovery__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  margin-top: 16px;
}
.discovery__stores {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  margin-top: 16px;
}
.discovery__keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}
.discovery__keyword-tag {
  cursor: pointer;
}
.discovery__keyword-count {
  font-size: 10px;
  color: var(--color-text-tertiary);
  margin-left: 4px;
}
.discovery__pagination {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}
.discovery__loading {
  padding: 20px;
}
.discovery__store-goods {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
}
</style>
