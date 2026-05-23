<template>
  <div class="burst-list">
    <div class="burst-list__header">
      <div class="burst-list__tabs">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          :class="['burst-list__tab', { 'burst-list__tab--active': activeSubTab === tab.value }]"
          @click="switchTab(tab.value)"
        >
          <span class="burst-list__tab-icon">{{ tab.icon }}</span>
          <span class="burst-list__tab-label">{{ tab.label }}</span>
          <el-tag v-if="tab.value === 'top-sold' && !isPremiumOrAbove" size="small" type="warning" effect="plain" class="burst-list__tab-badge">Premium</el-tag>
        </button>
      </div>

      <div class="burst-list__filters">
        <el-select
          v-model="selectedCategory"
          placeholder="全部分类"
          size="small"
          clearable
          class="burst-list__category-select"
          @change="handleCategoryChange"
        >
          <el-option
            v-for="cat in categoryOptions"
            :key="cat.value"
            :label="cat.label"
            :value="cat.value"
          />
        </el-select>
      </div>
    </div>

    <div v-if="plan === 'free'" class="burst-list__locked">
      <div class="burst-list__locked-inner">
        <div class="burst-list__locked-icon">🔒</div>
        <div class="burst-list__locked-title">爆品洞察为Pro及以上会员专属</div>
        <div class="burst-list__locked-desc">
          升级Pro解锁飙升榜、热门榜、新品榜，发现高销量爆品机会
        </div>
        <el-button type="primary" @click="$router.push('/pricing')">升级Pro</el-button>
      </div>
    </div>

    <div v-else-if="loading" class="burst-list__loading">
      <div v-for="i in 5" :key="i" class="burst-list__skeleton">
        <div class="burst-list__skeleton-rank"></div>
        <div class="burst-list__skeleton-content">
          <div class="burst-list__skeleton-title"></div>
          <div class="burst-list__skeleton-meta"></div>
        </div>
        <div class="burst-list__skeleton-score"></div>
      </div>
    </div>

    <div v-else-if="items.length > 0" class="burst-list__items">
      <div
        v-for="(item, index) in items"
        :key="item.ref"
        class="burst-item"
        @click="$emit('add-to-monitor', item)"
      >
        <div :class="['burst-item__rank', rankClass(index)]">
          <span v-if="index < 3" class="burst-item__rank-medal">{{ index + 1 }}</span>
          <span v-else class="burst-item__rank-number">{{ index + 1 }}</span>
        </div>

        <div class="burst-item__body">
          <div class="burst-item__title" :title="item.title">{{ item.title }}</div>
          <div class="burst-item__meta">
            <span v-if="item.store_name" class="burst-item__store">
              <el-icon :size="11"><Shop /></el-icon>
              {{ item.store_name }}
            </span>
            <el-tag
              v-if="item.keyword"
              size="small"
              type="info"
              effect="plain"
              class="burst-item__keyword"
            >
              {{ item.keyword }}
            </el-tag>
          </div>
        </div>

        <div class="burst-item__metrics">
          <div v-if="item.deal_price_masked" class="burst-item__masked" @click.stop="showUpgradeTip('price')">
            <span class="burst-item__masked-value">¥**</span>
          </div>
          <div v-else-if="item.deal_price != null" class="burst-item__price">
            ¥{{ item.deal_price }}
          </div>

          <div v-if="item.sold_num_masked" class="burst-item__masked" @click.stop="showUpgradeTip('sales')">
            <span class="burst-item__masked-value">
              {{ item.sold_num_approx ? `已售${item.sold_num_approx}` : '已售***' }}
            </span>
          </div>
          <div v-else-if="item.sold_num != null" class="burst-item__sold">
            已售{{ formatNumber(item.sold_num) }}
          </div>

          <div class="burst-item__score-wrap">
            <div
              class="burst-item__score-bar"
              :style="{ width: burstScoreWidth(item.sold_num) }"
            >
              <div
                :class="['burst-item__score-fill', burstScoreClass(item.sold_num)]"
                :style="{ width: '100%' }"
              ></div>
            </div>
            <span class="burst-item__score-label">{{ burstScoreLabel(item.sold_num) }}</span>
          </div>
        </div>

        <div class="burst-item__action">
          <el-button type="primary" size="small" text @click.stop="$emit('add-to-monitor', item)">
            <el-icon><Plus /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <div v-else class="burst-list__empty">
      <el-empty description="暂无爆品数据，切换分类或稍后再试" :image-size="80" />
    </div>

    <div v-if="items.length > 0 && total > pageSize" class="burst-list__pagination">
      <el-pagination
        v-model:current-page="currentPage"
        :total="total"
        :page-size="pageSize"
        layout="prev, pager, next"
        small
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, computed } from "vue";
import { Shop, Plus } from "@element-plus/icons-vue";
import { ElMessageBox } from "element-plus";
import { useAuthStore } from "../stores/auth";
import api from "../utils/api";
import type { DiscoveryGoodsItem } from "../composables/useDiscoveryData";

const emit = defineEmits<{
  "add-to-monitor": [item: DiscoveryGoodsItem];
}>();

const authStore = useAuthStore();
const plan = computed(() => authStore.userPlan || "free");
const isPremiumOrAbove = computed(() => ["premium", "enterprise"].includes(plan.value));

interface BurstTab {
  value: string;
  label: string;
  icon: string;
  apiPath: string;
}

const tabs: BurstTab[] = [
  { value: "rising", label: "飙升榜", icon: "🚀", apiPath: "/discovery/rising-goods" },
  { value: "hot", label: "热门榜", icon: "🔥", apiPath: "/discovery/hot-goods" },
  { value: "top-sold", label: "爆品排行", icon: "💎", apiPath: "/discovery/top-sold" },
  { value: "new", label: "新品榜", icon: "✨", apiPath: "/discovery/new-goods" },
];

const activeSubTab = ref("rising");
const selectedCategory = ref("");
const loading = ref(false);
const items = ref<DiscoveryGoodsItem[]>([]);
const total = ref(0);
const currentPage = ref(1);
const pageSize = ref(20);

const categoryOptions = [
  { label: "服饰鞋包", value: "服饰鞋包" },
  { label: "美妆护肤", value: "美妆护肤" },
  { label: "家居生活", value: "家居生活" },
  { label: "数码电子", value: "数码电子" },
  { label: "食品零食", value: "食品零食" },
  { label: "母婴用品", value: "母婴用品" },
  { label: "运动户外", value: "运动户外" },
  { label: "文具手帐", value: "文具手帐" },
];

async function fetchBurstData() {
  if (plan.value === "free") return;

  const currentTab = tabs.find((t) => t.value === activeSubTab.value);
  if (!currentTab) return;

  if (currentTab.value === "top-sold" && !["premium", "enterprise"].includes(plan.value)) {
    items.value = [];
    return;
  }

  loading.value = true;

  const params: Record<string, unknown> = {
    page: currentPage.value,
    page_size: pageSize.value,
  };
  if (selectedCategory.value) {
    params.category = selectedCategory.value;
  }

  try {
    const { data } = await api.get(currentTab.apiPath, { params });
    if (data.code === 0) {
      items.value = data.data.items;
      total.value = data.data.total;
    }
  } catch {
    items.value = [];
  } finally {
    loading.value = false;
  }
}

function switchTab(tab: string) {
  if (tab === "top-sold" && !isPremiumOrAbove.value) {
    ElMessageBox.alert(
      "爆品排行为Premium及以上会员专属，升级即可查看高销量商品排行",
      "升级解锁",
      { confirmButtonText: "了解Premium套餐", type: "info" }
    ).then(() => {
      window.location.hash = "#/pricing";
    }).catch(() => {});
    return;
  }
  activeSubTab.value = tab;
  currentPage.value = 1;
  fetchBurstData();
}

function handleCategoryChange() {
  currentPage.value = 1;
  fetchBurstData();
}

function handlePageChange(page: number) {
  currentPage.value = page;
  fetchBurstData();
}

function rankClass(index: number): string {
  if (index === 0) return "burst-item__rank--gold";
  if (index === 1) return "burst-item__rank--silver";
  if (index === 2) return "burst-item__rank--bronze";
  return "";
}

function formatNumber(num: number): string {
  if (num >= 10000) return `${(num / 10000).toFixed(1)}万`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}k`;
  return String(num);
}

function burstScoreWidth(soldNum: number | null): string {
  if (soldNum == null) return "0%";
  if (soldNum >= 10000) return "100%";
  if (soldNum >= 5000) return "80%";
  if (soldNum >= 1000) return "60%";
  if (soldNum >= 500) return "40%";
  if (soldNum >= 100) return "20%";
  return "10%";
}

function burstScoreClass(soldNum: number | null): string {
  if (soldNum == null) return "burst-item__score-fill--low";
  if (soldNum >= 5000) return "burst-item__score-fill--burst";
  if (soldNum >= 1000) return "burst-item__score-fill--hot";
  if (soldNum >= 100) return "burst-item__score-fill--warm";
  return "burst-item__score-fill--low";
}

function burstScoreLabel(soldNum: number | null): string {
  if (soldNum == null) return "-";
  if (soldNum >= 10000) return "爆";
  if (soldNum >= 5000) return "热";
  if (soldNum >= 1000) return "升";
  if (soldNum >= 100) return "温";
  return "新";
}

function showUpgradeTip(field: string) {
  const fieldLabel = field === "price" ? "价格" : "销量";
  ElMessageBox.alert(
    `升级Pro即可查看完整${fieldLabel}信息，还可享受更多搜索次数和高级筛选功能`,
    `${fieldLabel}数据已隐藏`,
    { confirmButtonText: "了解Pro套餐", type: "info" }
  ).then(() => {
    window.location.hash = "#/pricing";
  }).catch(() => {});
}

onMounted(() => {
  fetchBurstData();
});
</script>

<style scoped>
.burst-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.burst-list__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.burst-list__tabs {
  display: flex;
  gap: 4px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
  padding: 3px;
}

.burst-list__tab {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  transition: all 0.2s;
  white-space: nowrap;
}

.burst-list__tab:hover {
  color: var(--el-text-color-primary);
  background: var(--el-fill-color);
}

.burst-list__tab--active {
  background: var(--el-color-primary);
  color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.burst-list__tab--active:hover {
  background: var(--el-color-primary);
  color: #fff;
}

.burst-list__tab-icon {
  font-size: 14px;
}

.burst-list__tab-badge {
  font-size: 9px;
  padding: 0 4px;
  height: 16px;
  line-height: 16px;
  border-radius: 4px;
  margin-left: 2px;
}

.burst-list__category-select {
  width: 140px;
}

.burst-list__locked {
  display: flex;
  justify-content: center;
  padding: 60px 20px;
}

.burst-list__locked-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
  max-width: 320px;
}

.burst-list__locked-icon {
  font-size: 48px;
  opacity: 0.8;
}

.burst-list__locked-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.burst-list__locked-desc {
  font-size: 13px;
  color: var(--el-text-color-placeholder);
  line-height: 1.6;
}

.burst-list__loading {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.burst-list__skeleton {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--el-bg-color);
  border-radius: 8px;
}

.burst-list__skeleton-rank {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--el-fill-color-light);
  animation: pulse 1.5s infinite;
}

.burst-list__skeleton-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.burst-list__skeleton-title {
  height: 14px;
  width: 60%;
  border-radius: 4px;
  background: var(--el-fill-color-light);
  animation: pulse 1.5s infinite;
}

.burst-list__skeleton-meta {
  height: 10px;
  width: 40%;
  border-radius: 4px;
  background: var(--el-fill-color-light);
  animation: pulse 1.5s infinite;
}

.burst-list__skeleton-score {
  width: 60px;
  height: 14px;
  border-radius: 4px;
  background: var(--el-fill-color-light);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.burst-list__items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.burst-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--el-bg-color);
  border-radius: 8px;
  border: 1px solid var(--el-border-color-lighter);
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.burst-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateX(4px);
  border-color: var(--el-color-primary-light-5);
}

.burst-item__rank {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.burst-item__rank-medal {
  color: #fff;
  font-size: 12px;
  font-weight: 800;
}

.burst-item__rank--gold {
  background: linear-gradient(135deg, #FFD700, #FFA500);
  box-shadow: 0 2px 8px rgba(255, 215, 0, 0.4);
}

.burst-item__rank--silver {
  background: linear-gradient(135deg, #C0C0C0, #A8A8A8);
  box-shadow: 0 2px 8px rgba(192, 192, 192, 0.4);
}

.burst-item__rank--bronze {
  background: linear-gradient(135deg, #CD7F32, #B8860B);
  box-shadow: 0 2px 8px rgba(205, 127, 50, 0.4);
}

.burst-item__rank-number {
  color: var(--el-text-color-placeholder);
  background: var(--el-fill-color-light);
  border-radius: 50%;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.burst-item__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.burst-item__title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.burst-item__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.burst-item__store {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 120px;
}

.burst-item__keyword {
  font-size: 10px;
}

.burst-item__metrics {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.burst-item__price {
  font-size: 13px;
  font-weight: 700;
  color: var(--el-color-danger);
  min-width: 50px;
  text-align: right;
}

.burst-item__sold {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  min-width: 60px;
  text-align: right;
}

.burst-item__masked {
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--el-fill-color-light);
  transition: background 0.2s;
}

.burst-item__masked:hover {
  background: var(--el-fill-color);
}

.burst-item__masked-value {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  font-style: italic;
}

.burst-item__score-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 90px;
}

.burst-item__score-bar {
  width: 50px;
  height: 6px;
  border-radius: 3px;
  background: var(--el-fill-color-light);
  overflow: hidden;
}

.burst-item__score-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

.burst-item__score-fill--burst {
  background: linear-gradient(90deg, #EF4444, #F97316);
}

.burst-item__score-fill--hot {
  background: linear-gradient(90deg, #F97316, #EAB308);
}

.burst-item__score-fill--warm {
  background: linear-gradient(90deg, #3B82F6, #60A5FA);
}

.burst-item__score-fill--low {
  background: var(--el-text-color-placeholder);
}

.burst-item__score-label {
  font-size: 11px;
  font-weight: 700;
  min-width: 14px;
  text-align: center;
}

.burst-item__action {
  flex-shrink: 0;
}

.burst-list__empty {
  display: flex;
  justify-content: center;
  padding: 40px 0;
}

.burst-list__pagination {
  display: flex;
  justify-content: center;
  padding-top: 8px;
}
</style>
