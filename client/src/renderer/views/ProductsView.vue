<template>
  <div class="products fade-in">
    <PageHeader title="我的商品" subtitle="管理您的商品监控，发现选品机会">
      <el-button v-permission="'gate:monitor:add'" type="primary" @click="showAdd = true">
        <el-icon><Plus /></el-icon>
        添加商品
      </el-button>
      <el-button v-permission="'gate:monitor:add'" @click="showExcelImport = true">
        <el-icon><Upload /></el-icon>
        批量导入
      </el-button>
      <el-button v-permission="'gate:monitor:add'" @click="showCollect = true">
        <el-icon><Download /></el-icon>
        立即采集
      </el-button>
      <el-button @click="showProgress = true">
        <el-icon><DataLine /></el-icon>
        采集进度
      </el-button>
      <el-button @click="showExport = true">
        <el-icon><Document /></el-icon>
        导出
      </el-button>
    </PageHeader>

    <div class="products__toolbar">
      <SearchInput placeholder="搜索商品..." @search="searchQuery = $event" />
      <div class="products__category-filter">
        <CategorySidebar
          :active-category="activeCategoryId"
          :total-count="productStore.products.length"
          @select="handleCategorySelect"
        />
      </div>
      <div class="products__view-toggle">
        <el-button-group>
          <el-button :type="viewMode === 'card' ? 'primary' : ''" size="small" @click="viewMode = 'card'">
            <el-icon><Grid /></el-icon>
          </el-button>
          <el-button :type="viewMode === 'waterfall' ? 'primary' : ''" size="small" @click="viewMode = 'waterfall'">
            <el-icon><Menu /></el-icon>
          </el-button>
          <el-button :type="viewMode === 'table' ? 'primary' : ''" size="small" @click="viewMode = 'table'">
            <el-icon><List /></el-icon>
          </el-button>
        </el-button-group>
      </div>
    </div>

    <EmptyState
      v-if="!productStore.loading && filteredProducts.length === 0 && !searchQuery"
      :icon="Goods"
      title="暂无监控商品"
      description="添加第一个商品开始监控数据变化"
      action-label="添加商品"
      :action-icon="Plus"
      @action="showAdd = true"
    />

    <EmptyState
      v-else-if="!productStore.loading && filteredProducts.length === 0 && searchQuery"
      :icon="Search"
      title="未找到匹配商品"
      :description="`没有找到包含「${searchQuery}」的商品`"
    />

    <div v-else-if="viewMode === 'card'" class="products__grid">
      <ProductCard
        v-for="product in filteredProducts"
        :key="product.id"
        :product="product"
        :ranking="getRankingInfo(product.id)"
        @detail="$router.push(`/products/${product.id}`)"
        @collect="collectSingle"
        @ai-analysis="quickAIAnalysis"
        @schedule="addSchedule"
        @delete="confirmDelete"
      />
    </div>

    <WaterfallLayout
      v-else-if="viewMode === 'waterfall'"
      :items="filteredProducts"
      :item-key="(p: any) => p.id"
      :column-count="3"
      :gap="16"
    >
      <template #default="{ item }">
        <ProductWaterfallCard
          :product="item"
          @detail="$router.push(`/products/${item.id}`)"
          @collect="collectSingle"
          @delete="confirmDelete"
        />
      </template>
    </WaterfallLayout>

    <div v-else class="products__table-wrapper">
      <el-table v-loading="productStore.loading" :data="filteredProducts" stripe>
        <el-table-column label="商品" min-width="280">
          <template #default="{ row }">
            <div class="product-cell">
              <el-image v-if="row.image_url" :src="row.image_url" class="product-cell__image" fit="cover" />
              <div v-else class="product-cell__image product-cell__image--placeholder">
                <el-icon :size="16"><Goods /></el-icon>
              </div>
              <div class="product-cell__info">
                <div class="product-cell__name">{{ row.product_name }}</div>
                <div class="product-cell__shop">{{ row.shop_name || '-' }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="商品ID" prop="platform_product_id" width="180">
          <template #default="{ row }">
            <span class="cell-mono">{{ row.platform_product_id }}</span>
          </template>
        </el-table-column>
        <el-table-column label="最新采集" width="160">
          <template #default="{ row }">
            <span class="cell-secondary">{{ row.last_collected_at ? formatDate(row.last_collected_at) : '未采集' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="排名" width="120">
          <template #default="{ row }">
            <div v-if="getRankingInfo(row.id)" class="cell-rank">
              <span class="cell-rank__number">#{{ getRankingInfo(row.id)!.rank }}</span>
              <span v-if="getRankingInfo(row.id)!.total" class="cell-rank__total">/{{ getRankingInfo(row.id)!.total }}</span>
              <el-tag
                v-if="getRankingInfo(row.id)!.trend" size="small" effect="light"
                :type="getRankingInfo(row.id)!.trend === '上升' ? 'success' : getRankingInfo(row.id)!.trend === '下降' ? 'danger' : 'info'"
              >
                {{ getRankingInfo(row.id)!.trend }}
              </el-tag>
            </div>
            <span v-else class="cell-secondary">-</span>
          </template>
        </el-table-column>
        <el-table-column label="24h增长" width="120">
          <template #default="{ row }">
            <span
              v-if="row.growth_24h && row.growth_24h.sales_pct != null"
              :class="['cell-growth', row.growth_24h.sales_pct > 0 ? 'cell-growth--up' : row.growth_24h.sales_pct < 0 ? 'cell-growth--down' : '']"
            >
              {{ row.growth_24h.sales_pct >= 0 ? '+' : '' }}{{ row.growth_24h.sales_pct }}%
            </span>
            <span v-else class="cell-secondary">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="360" fixed="right">
          <template #default="{ row }">
            <div class="product-cell__actions">
              <el-button size="small" @click="$router.push(`/products/${row.id}`)">详情</el-button>
              <el-button size="small" type="primary" @click="collectSingle(row)">采集</el-button>
              <el-dropdown v-permission="'gate:ai:basic_analysis'" size="small" @command="(cmd: string) => quickAIAnalysis(row, cmd)">
                <el-button size="small" type="warning">
                  <el-icon><MagicStick /></el-icon>AI
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="trend_score">趋势评分</el-dropdown-item>
                    <el-dropdown-item command="prediction">爆品预测</el-dropdown-item>
                    <el-dropdown-item command="risk_warning">风险预警</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
              <el-button size="small" @click="addSchedule(row)">定时</el-button>
              <el-button size="small" type="danger" plain @click="confirmDelete(row.id)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="showAdd" title="添加小红书商品" width="640px" @close="resetAddDialog">
      <el-tabs v-model="addTab" class="add-product-tabs">
        <el-tab-pane label="粘贴链接" name="link">
          <el-alert
            type="info"
            :closable="false"
            show-icon
            class="add-quota-note"
            title="不占用发现库额度"
            description="自行粘贴小红书商品链接或填写商品 ID 添加，不计入「搜索添加」每日次数。"
          />
          <el-form ref="addFormRef" :model="addForm" :rules="addRules" style="margin-top: 16px">
            <el-form-item label="商品链接" prop="noteInput">
              <el-input v-model="addForm.noteInput" placeholder="粘贴小红书商品链接或商品ID" />
            </el-form-item>
            <el-form-item label="备注名称" prop="product_name">
              <el-input v-model="addForm.product_name" placeholder="可选，方便识别" />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane name="search">
          <template #label>
            <span>🔍 搜索添加</span>
          </template>
          <div class="add-search" style="margin-top: 16px">
            <el-alert
              type="info"
              :closable="false"
              show-icon
              class="add-quota-note"
            >
              <template #title>
                云端搜索添加
                <span
                  v-if="discoveryQuota && discoveryQuota.daily_limit >= 0"
                  class="add-quota-note__count"
                >
                  · 今日剩余 {{ discoveryQuota.remaining }} / {{ discoveryQuota.daily_limit }} 次
                </span>
                <span v-else-if="discoveryQuota && discoveryQuota.daily_limit < 0">
                  · 不限次数
                </span>
              </template>
              <p class="add-quota-note__desc">
                {{ discoveryQuota?.quota_hint || '按账号与当前 IP 合计计次：免费每日 20 次，Pro 每日 200 次。' }}
              </p>
            </el-alert>
            <div class="add-search__bar">
              <el-input
                v-model="discoveryKeyword"
                placeholder="搜索商品标题或店铺名称..."
                clearable
                @input="debouncedSearchDiscovery"
                @keyup.enter="searchDiscovery"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
              <el-button type="primary" :loading="discoveryLoading" @click="searchDiscovery">
                搜索
              </el-button>
            </div>

            <div v-if="discoveryLoading" class="add-search__loading">
              <el-skeleton :rows="4" animated />
            </div>

            <div v-else-if="discoveryResults.length > 0" class="add-search__results">
              <div
                v-for="item in discoveryResults"
                :key="item.ref"
                class="add-search__item"
              >
                <div class="add-search__item-info">
                  <div class="add-search__item-title">{{ item.title }}</div>
                  <div class="add-search__item-meta">
                    <span v-if="item.store_name" class="add-search__item-store">
                      <el-icon :size="12"><Shop /></el-icon>
                      {{ item.store_name }}
                    </span>
                  </div>
                </div>
                <el-button type="primary" size="small" @click="addFromDiscovery(item)">
                  <el-icon><Plus /></el-icon> 加入监控
                </el-button>
              </div>
            </div>

            <EmptyState
              v-else-if="discoveryHasSearched"
              :icon="Search"
              title="未找到匹配商品"
              description="尝试更换关键词搜索"
              compact
            />

            <div v-else class="add-search__hint">
              <el-icon :size="32" color="var(--color-text-tertiary)"><Compass /></el-icon>
              <p>从商品数据库中搜索发现，一键加入监控</p>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button v-if="addTab === 'link'" type="primary" @click="addProduct">添加并采集</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showCollect" title="批量采集" width="560px">
      <el-form label-position="top">
        <el-form-item label="并发数">
          <div class="slider-wrapper">
            <el-slider v-model="concurrency" :min="1" :max="10" :step="1" />
            <span class="slider-value">{{ concurrency }}</span>
          </div>
        </el-form-item>
        <el-form-item label="采集范围">
          <el-radio-group v-model="collectScope">
            <el-radio value="all">全部商品 ({{ productStore.products.length }})</el-radio>
            <el-radio value="uncollected">未采集 ({{ uncollectedCount }})</el-radio>
            <el-radio value="stale">超24h未采集 ({{ staleCount }})</el-radio>
            <el-radio value="failed">采集失败 ({{ failedCount }})</el-radio>
            <el-radio value="category">按分类</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="collectScope === 'category'" label="选择分类">
          <el-select v-model="collectCategory" placeholder="选择分类" clearable style="width: 100%">
            <el-option v-for="cat in categoryList" :key="cat" :label="cat" :value="cat" />
          </el-select>
        </el-form-item>
        <el-form-item label="预计耗时">
          <div class="collect-estimate">
            <span class="collect-estimate__count">采集 {{ batchCollectCount }} 个商品</span>
            <span class="collect-estimate__time">约 {{ estimatedTime }}</span>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCollect = false">取消</el-button>
        <el-button type="primary" :disabled="batchCollectCount === 0" @click="startBatchCollect">开始采集</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showSchedule" title="设置定时采集" width="480px">
      <el-form label-position="top">
        <el-form-item label="采集频率">
          <el-select v-model="scheduleFrequency" style="width: 100%">
            <el-option label="每30分钟" :value="30" />
            <el-option label="每1小时" :value="60" />
            <el-option label="每2小时" :value="120" />
            <el-option label="每6小时" :value="360" />
            <el-option label="每12小时" :value="720" />
            <el-option label="每天" :value="1440" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSchedule = false">取消</el-button>
        <el-button type="primary" @click="confirmSchedule">确认</el-button>
      </template>
    </el-dialog>

    <CollectProgressPanel :visible="showProgress" @update:visible="showProgress = $event" />
    <ExcelImportDialog :visible="showExcelImport" @update:visible="showExcelImport = $event" />
    <ExportDialog
      v-model="showExport"
      :products="filteredProducts"
      :total-count="productStore.products.length"
      :filtered-count="filteredProducts.length"
      :selected-count="0"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Plus, Download, Goods, Grid, List, Search, MagicStick, Shop, Compass, DataLine, Upload, Menu, Document } from "@element-plus/icons-vue";
import PageHeader from "../components/PageHeader.vue";
import SearchInput from "../components/SearchInput.vue";
import EmptyState from "../components/EmptyState.vue";
import ProductCard from "../components/ProductCard.vue";
import CollectProgressPanel from "../components/CollectProgressPanel.vue";
import ExcelImportDialog from "../components/ExcelImportDialog.vue";
import ExportDialog from "../components/ExportDialog.vue";
import ProductWaterfallCard from "../components/ProductWaterfallCard.vue";
import WaterfallLayout from "../components/WaterfallLayout.vue";
import CategorySidebar from "../components/CategorySidebar.vue";
import { useProductsData } from "../composables/useProductsData";
import { usePermissionStore } from "../stores/permission";

const permissionStore = usePermissionStore();
const showProgress = ref(false);
const showExcelImport = ref(false);
const showExport = ref(false);
const activeCategoryId = ref<string | null>(null);

function handleCategorySelect(categoryId: string | null, categoryName: string | null) {
  activeCategoryId.value = categoryId;
  categoryFilter.value = categoryName;
}

const {
  productStore,
  showAdd, addTab, discoveryKeyword, discoveryResults, discoveryLoading, discoveryHasSearched, discoveryQuota,
  showCollect, showSchedule,
  addFormRef, addForm, addRules,
  concurrency, collectScope, collectCategory, scheduleFrequency,
  viewMode, searchQuery, categoryFilter, filteredProducts,
  categoryList, uncollectedCount, staleCount, failedCount, batchCollectCount, estimatedTime,
  formatDate, formatNumber,
  addProduct, searchDiscovery, debouncedSearchDiscovery, cancelDebouncedSearchDiscovery, addFromDiscovery, resetAddDialog,
  collectSingle, startBatchCollect,
  addSchedule, confirmSchedule, confirmDelete,
  getRankingInfo,
  quickAIAnalysis, init,
} = useProductsData();

onMounted(() => {
  init();
});
</script>

<style scoped>
.products {
  padding: 24px;
  min-height: 100%;
}

.products__toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  gap: 16px;
}

.products__category-filter {
  flex: 1;
  min-width: 0;
}

.products__category-filter :deep(.category-sidebar) {
  background: transparent;
}

.products__category-filter :deep(.category-sidebar__header) {
  display: none;
}

.products__category-filter :deep(.category-sidebar__list) {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding: 0;
}

.products__category-filter :deep(.category-sidebar__item) {
  flex-shrink: 0;
  padding: 4px 12px;
  border-radius: var(--radius-lg);
  font-size: var(--text-xs);
  border: 1px solid var(--color-border-light);
  background: var(--color-bg-card);
}

.products__category-filter :deep(.category-sidebar__item--active) {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.products__category-filter :deep(.category-sidebar__more) {
  display: none;
}

.products__category-filter :deep(.category-sidebar__count) {
  margin-left: 2px;
  font-size: 10px;
  opacity: 0.7;
}

.products__view-toggle {
  flex-shrink: 0;
}

.products__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.products__table-wrapper {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-light);
}

.product-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.product-cell__image {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
  border: 1px solid var(--color-border-light);
}

.product-cell__image--placeholder {
  background: var(--color-bg-page);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary);
}

.product-cell__info {
  flex: 1;
  min-width: 0;
}

.product-cell__name {
  font-weight: 500;
  font-size: var(--text-base);
  color: var(--color-text-primary);
  margin-bottom: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.product-cell__shop {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.product-cell__actions {
  display: flex;
  gap: 8px;
}

.cell-rank {
  display: flex;
  align-items: center;
  gap: 6px;
}

.cell-rank__number {
  font-weight: 700;
  color: var(--color-warning);
  font-size: var(--text-sm);
}

.cell-rank__total {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.cell-mono {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.cell-secondary {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.cell-growth {
  font-weight: 600;
  font-size: var(--text-sm);
}

.cell-growth--up {
  color: var(--color-success);
}

.cell-growth--down {
  color: var(--color-danger);
}

.collect-estimate {
  display: flex;
  align-items: center;
  gap: var(--space-lg);
  padding: var(--space-sm) var(--space-base);
  background: var(--color-bg-page);
  border-radius: var(--radius-base);
}

.collect-estimate__count {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.collect-estimate__time {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-primary);
}

.slider-wrapper {
  display: flex;
  align-items: center;
  gap: 16px;
}

.slider-value {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-primary);
  min-width: 32px;
  text-align: center;
}

@media (max-width: 768px) {
  .products {
    padding: 16px;
  }
  .products__grid {
    grid-template-columns: 1fr;
  }
}

.add-product-tabs :deep(.el-tabs__nav) {
  width: 100%;
}
.add-product-tabs :deep(.el-tabs__item) {
  flex: 1;
  text-align: center;
}
.add-search__bar {
  display: flex;
  gap: 8px;
}
.add-search__loading {
  margin-top: 16px;
}
.add-search__results {
  margin-top: 16px;
  max-height: 400px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.add-search__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--color-bg-page);
  border-radius: var(--radius-base);
  border: 1px solid var(--color-border-light);
  transition: all 0.2s;
}
.add-search__item:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}
.add-search__item-info {
  flex: 1;
  min-width: 0;
  margin-right: 12px;
}
.add-search__item-title {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.add-search__item-meta {
  display: flex;
  gap: 12px;
  margin-top: 4px;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}
.add-search__item-store {
  display: flex;
  align-items: center;
  gap: 2px;
}
.add-search__hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 32px 0;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

.add-quota-note {
  margin-bottom: 12px;
}

.add-quota-note__count {
  font-weight: 600;
  color: var(--color-primary);
}

.add-quota-note__desc {
  margin: 4px 0 0;
  line-height: 1.5;
  font-size: var(--text-sm);
}

</style>
