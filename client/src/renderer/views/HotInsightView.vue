<template>
  <div class="hot-insight fade-in">
    <PageHeader title="爆品洞察" subtitle="热门商品排行，发现市场爆款趋势">
      <el-select v-model="selectedCategory" placeholder="选择品类" clearable style="width: 180px" @change="fetchHotGoods">
        <el-option v-for="cat in categoryOptions" :key="cat" :label="cat" :value="cat" />
      </el-select>
      <el-button :loading="loading" @click="fetchHotGoods">刷新</el-button>
    </PageHeader>

    <div v-if="isLocked" class="hot-insight__locked">
      <el-icon :size="48" color="var(--color-text-tertiary)"><Lock /></el-icon>
      <h3>Premium 专属功能</h3>
      <p>热门商品榜为 Pro 及以上会员专属，升级即可查看爆品排行</p>
      <el-button type="primary" @click="$router.push('/license')">升级会员</el-button>
    </div>

    <template v-else>
      <div class="hot-insight__stats">
        <StatCard :icon="TrendCharts" variant="primary" label="爆品数" :value="totalItems" />
        <StatCard :icon="Goods" variant="success" label="当前品类" :value="selectedCategory || '全品类'" />
        <StatCard :icon="Timer" variant="amber" label="数据更新" :value="lastUpdated" />
      </div>

      <div class="card">
        <div class="card__header">
          <div class="card__title-group">
            <el-icon class="card__icon" :size="20"><TrendCharts /></el-icon>
            <h3 class="card__title">热门商品排行</h3>
          </div>
          <div class="card__actions">
            <el-radio-group v-model="viewMode" size="small">
              <el-radio-button value="table">列表</el-radio-button>
              <el-radio-button value="grid">卡片</el-radio-button>
            </el-radio-group>
          </div>
        </div>

        <div v-if="loading" class="hot-insight__loading">
          <el-skeleton :rows="8" animated />
        </div>

        <template v-else-if="hotGoods.length > 0">
          <div v-if="viewMode === 'table'" class="hot-insight__table">
            <el-table :data="hotGoods" stripe>
              <el-table-column label="排名" width="70" align="center">
                <template #default="{ $index }">
                  <span :class="['rank-badge', `rank-${$index + 1}`]">{{ $index + 1 }}</span>
                </template>
              </el-table-column>
              <el-table-column label="商品" min-width="280">
                <template #default="{ row }">
                  <div class="goods-cell">
                    <img v-if="row.image_url" :src="row.image_url" class="goods-cell__img">
                    <div v-else class="goods-cell__img goods-cell__img--placeholder">
                      <el-icon><Goods /></el-icon>
                    </div>
                    <div class="goods-cell__info">
                      <span class="goods-cell__title">{{ row.title }}</span>
                      <span class="goods-cell__store">{{ row.store_name }}</span>
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="价格" width="110" sortable>
                <template #default="{ row }">
                  <span v-if="row.deal_price_masked" class="masked-value">***</span>
                  <span v-else class="price-value">{{ row.deal_price != null ? `¥${row.deal_price}` : '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="销量" width="120" sortable>
                <template #default="{ row }">
                  <span v-if="row.sold_num_masked" class="masked-value">{{ row.sold_num_approx || '***' }}</span>
                  <span v-else class="sales-value">{{ row.sold_num != null ? formatNumber(row.sold_num) : '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="关键词" width="120">
                <template #default="{ row }">
                  <el-tag v-if="row.keyword" size="small" effect="plain">{{ row.keyword }}</el-tag>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" text type="primary" @click="addToMonitor(row)">加入监控</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div v-else class="hot-insight__grid">
            <div v-for="(item, idx) in hotGoods" :key="item.ref" class="hot-card">
              <span :class="['hot-card__rank', `rank-${idx + 1}`]">{{ idx + 1 }}</span>
              <img v-if="item.image_url" :src="item.image_url" class="hot-card__img">
              <div v-else class="hot-card__img hot-card__img--placeholder">
                <el-icon :size="32"><Goods /></el-icon>
              </div>
              <div class="hot-card__body">
                <h4 class="hot-card__title">{{ item.title }}</h4>
                <span class="hot-card__store">{{ item.store_name }}</span>
                <div class="hot-card__metrics">
                  <span v-if="item.deal_price_masked" class="masked-value">¥***</span>
                  <span v-else class="hot-card__price">{{ item.deal_price != null ? `¥${item.deal_price}` : '-' }}</span>
                  <span v-if="item.sold_num_masked" class="masked-value">{{ item.sold_num_approx || '***' }}销量</span>
                  <span v-else class="hot-card__sales">{{ item.sold_num != null ? formatNumber(item.sold_num) : '-' }}销量</span>
                </div>
                <el-tag v-if="item.keyword" size="small" effect="plain" class="hot-card__tag">{{ item.keyword }}</el-tag>
              </div>
              <el-button size="small" type="primary" text class="hot-card__action" @click="addToMonitor(item)">+ 监控</el-button>
            </div>
          </div>

          <div v-if="hasMore" class="hot-insight__pagination">
            <el-button :loading="loadingMore" @click="loadMore">加载更多</el-button>
          </div>
        </template>

        <EmptyState v-else :icon="TrendCharts" title="暂无热门商品数据" description="连接云端服务获取爆品排行" compact />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { TrendCharts, Goods, Timer, Lock } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import PageHeader from "../components/PageHeader.vue";
import StatCard from "../components/StatCard.vue";
import EmptyState from "../components/EmptyState.vue";
import api from "../utils/api";
import { usePermissionStore } from "../stores/permission";

interface HotGoodsItem {
  ref: string;
  title: string;
  store_name: string;
  keyword: string;
  deal_price: number | null;
  deal_price_masked?: boolean;
  sold_num: number | null;
  sold_num_masked?: boolean;
  sold_num_approx?: string;
  image_url?: string;
}

const permissionStore = usePermissionStore();
const isLocked = computed(() => permissionStore.plan === "free");

const hotGoods = ref<HotGoodsItem[]>([]);
const loading = ref(false);
const loadingMore = ref(false);
const selectedCategory = ref("");
const viewMode = ref<"table" | "grid">("table");
const currentPage = ref(1);
const totalItems = ref(0);
const hasMore = ref(false);
const lastUpdated = ref("刚刚");
const categoryOptions = ref<string[]>([]);

function isElectron(): boolean {
  return !!(window as unknown as { electronAPI?: unknown }).electronAPI;
}

async function invokeIpc(channel: string, ...args: unknown[]): Promise<unknown> {
  const w = window as unknown as { electronAPI?: { invoke: (ch: string, ...a: unknown[]) => Promise<unknown> } };
  if (!w.electronAPI?.invoke) throw new Error("electronAPI not available");
  return w.electronAPI.invoke(channel, ...args);
}

function formatNumber(num: number): string {
  if (num >= 10000) return (num / 10000).toFixed(1) + "万";
  if (num >= 1000) return (num / 1000).toFixed(1) + "k";
  return String(num);
}

async function fetchHotGoods() {
  loading.value = true;
  currentPage.value = 1;
  hotGoods.value = [];
  try {
    const params: Record<string, unknown> = { page: 1, page_size: 20 };
    if (selectedCategory.value) params.category = selectedCategory.value;
    const { data } = await api.get("/discovery/hot-goods", { params });
    if (data.code === 0) {
      hotGoods.value = data.data.items || [];
      totalItems.value = data.data.total || 0;
      hasMore.value = hotGoods.value.length < totalItems.value;
    }
  } catch (err: unknown) {
    const axiosErr = err as { response?: { data?: { code?: number; message?: string } } };
    if (axiosErr?.response?.data?.code === 42023) {
      ElMessage.warning(axiosErr.response.data.message || "已达上限");
      return;
    }
    if (isElectron()) {
      try {
        const ipcParams: Record<string, unknown> = { page: 1, page_size: 20 };
        if (selectedCategory.value) ipcParams.category = selectedCategory.value;
        const result = await invokeIpc("discovery:hot-goods", ipcParams) as { code?: number; data?: { items?: HotGoodsItem[]; total?: number } };
        if (result?.code === 0 && result?.data) {
          hotGoods.value = result.data.items || [];
          totalItems.value = result.data.total || 0;
          hasMore.value = hotGoods.value.length < totalItems.value;
        }
      } catch { /* ignore */ }
    }
  } finally {
    loading.value = false;
  }
}

async function loadMore() {
  loadingMore.value = true;
  currentPage.value++;
  try {
    const params: Record<string, unknown> = { page: currentPage.value, page_size: 20 };
    if (selectedCategory.value) params.category = selectedCategory.value;
    const { data } = await api.get("/discovery/hot-goods", { params });
    if (data.code === 0) {
      hotGoods.value = [...hotGoods.value, ...(data.data.items || [])];
      hasMore.value = hotGoods.value.length < (data.data.total || 0);
    }
  } catch {
    if (isElectron()) {
      try {
        const ipcParams: Record<string, unknown> = { page: currentPage.value, page_size: 20 };
        if (selectedCategory.value) ipcParams.category = selectedCategory.value;
        const result = await invokeIpc("discovery:hot-goods", ipcParams) as { code?: number; data?: { items?: HotGoodsItem[]; total?: number } };
        if (result?.code === 0 && result?.data) {
          hotGoods.value = [...hotGoods.value, ...(result.data.items || [])];
          hasMore.value = hotGoods.value.length < (result.data.total || 0);
        }
      } catch { /* ignore */ }
    }
  } finally {
    loadingMore.value = false;
  }
}

async function addToMonitor(item: HotGoodsItem) {
  try {
    const { data } = await api.post("/discovery/add-to-monitor", {
      ref_id: item.ref,
      product_name: item.title,
      mode: "goods",
    });
    if (data.code === 0) {
      ElMessage.success("已加入监控");
    }
  } catch {
    if (isElectron()) {
      try {
        await invokeIpc("discovery:add-to-monitor", { ref_id: item.ref, product_name: item.title, mode: "goods" });
        ElMessage.success("已加入监控（本地）");
      } catch (err) {
        ElMessage.error("添加失败：" + String(err));
      }
    }
  }
}

async function fetchCategories() {
  try {
    const { data } = await api.get("/discovery/keywords", { params: { page: 1, page_size: 50 } });
    if (data.code === 0) {
      categoryOptions.value = (data.data.items || []).map((i: { keyword: string }) => i.keyword);
    }
  } catch {
    if (isElectron()) {
      try {
        const result = await invokeIpc("discovery:keywords", { page: 1, page_size: 50 }) as { code?: number; data?: { items?: { keyword: string }[] } };
        if (result?.code === 0 && result?.data) {
          categoryOptions.value = (result.data.items || []).map((i) => i.keyword);
        }
      } catch { /* ignore */ }
    }
  }
}

onMounted(() => {
  if (!isLocked.value) {
    fetchHotGoods();
    fetchCategories();
  }
});
</script>

<style scoped>
.hot-insight { padding: 24px; min-height: 100%; }
.hot-insight__stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 24px; }
.hot-insight__locked { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 80px 24px; text-align: center; gap: 16px; }
.hot-insight__locked h3 { margin: 0; font-size: 20px; color: var(--color-text-primary); }
.hot-insight__locked p { margin: 0; color: var(--color-text-secondary); max-width: 360px; }
.hot-insight__loading { padding: 24px; }
.hot-insight__table { padding: 0 16px 16px; }
.hot-insight__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; padding: 16px; }
.hot-insight__pagination { display: flex; justify-content: center; padding: 16px; }

.card { background: var(--color-bg-card); border-radius: var(--radius-lg); box-shadow: var(--shadow-sm); border: 1px solid var(--color-border-light); overflow: hidden; }
.card__header { padding: 20px 24px; border-bottom: 1px solid var(--color-border-light); display: flex; justify-content: space-between; align-items: center; }
.card__title-group { display: flex; align-items: center; gap: 10px; }
.card__icon { color: var(--color-primary); }
.card__title { margin: 0; font-size: var(--text-lg); font-weight: 600; color: var(--color-text-primary); }
.card__actions { display: flex; align-items: center; gap: 8px; }

.rank-badge { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 50%; font-size: 13px; font-weight: 700; background: var(--color-bg-page); color: var(--color-text-secondary); }
.rank-badge.rank-1 { background: linear-gradient(135deg, #FFD700, #FFA500); color: #fff; }
.rank-badge.rank-2 { background: linear-gradient(135deg, #C0C0C0, #A0A0A0); color: #fff; }
.rank-badge.rank-3 { background: linear-gradient(135deg, #CD7F32, #B8860B); color: #fff; }

.goods-cell { display: flex; align-items: center; gap: 12px; }
.goods-cell__img { width: 44px; height: 44px; border-radius: 8px; object-fit: cover; flex-shrink: 0; }
.goods-cell__img--placeholder { display: flex; align-items: center; justify-content: center; background: var(--color-bg-page); color: var(--color-text-tertiary); }
.goods-cell__info { display: flex; flex-direction: column; gap: 2px; overflow: hidden; }
.goods-cell__title { font-weight: 500; color: var(--color-text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.goods-cell__store { font-size: 12px; color: var(--color-text-tertiary); }

.price-value { font-weight: 600; color: var(--color-danger, #F56C6C); }
.sales-value { font-weight: 500; color: var(--color-text-primary); }
.masked-value { color: var(--color-text-tertiary); font-style: italic; }

.hot-card { position: relative; background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); overflow: hidden; transition: box-shadow 0.3s; }
.hot-card:hover { box-shadow: var(--shadow-md); }
.hot-card__rank { position: absolute; top: 8px; left: 8px; z-index: 1; display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 24px; border-radius: 50%; font-size: 12px; font-weight: 700; background: var(--color-bg-page); color: var(--color-text-secondary); }
.hot-card__rank.rank-1 { background: linear-gradient(135deg, #FFD700, #FFA500); color: #fff; }
.hot-card__rank.rank-2 { background: linear-gradient(135deg, #C0C0C0, #A0A0A0); color: #fff; }
.hot-card__rank.rank-3 { background: linear-gradient(135deg, #CD7F32, #B8860B); color: #fff; }
.hot-card__img { width: 100%; height: 160px; object-fit: cover; display: block; }
.hot-card__img--placeholder { display: flex; align-items: center; justify-content: center; background: var(--color-bg-page); color: var(--color-text-tertiary); }
.hot-card__body { padding: 12px; display: flex; flex-direction: column; gap: 4px; }
.hot-card__title { margin: 0; font-size: 14px; font-weight: 500; color: var(--color-text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hot-card__store { font-size: 12px; color: var(--color-text-tertiary); }
.hot-card__metrics { display: flex; justify-content: space-between; align-items: center; margin-top: 4px; }
.hot-card__price { font-weight: 600; color: var(--color-danger, #F56C6C); }
.hot-card__sales { font-size: 12px; color: var(--color-text-secondary); }
.hot-card__tag { margin-top: 4px; align-self: flex-start; }
.hot-card__action { margin: 4px 12px 12px; }

@media (max-width: 768px) {
  .hot-insight { padding: 16px; }
  .hot-insight__stats { grid-template-columns: 1fr; }
  .hot-insight__grid { grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); }
}
</style>
