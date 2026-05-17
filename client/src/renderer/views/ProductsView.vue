<template>
  <div class="products fade-in">
    <PageHeader title="我的商品" subtitle="管理您的商品监控，发现选品机会">
      <el-button v-permission="'gate:monitor:add'" type="primary" @click="showAdd = true">
        <el-icon><Plus /></el-icon>
        添加商品
      </el-button>
      <el-button v-permission="'gate:monitor:add'" @click="showCollect = true">
        <el-icon><Download /></el-icon>
        立即采集
      </el-button>
    </PageHeader>

    <div class="products__toolbar">
      <SearchInput placeholder="搜索商品..." @search="searchQuery = $event" />
      <div class="products__view-toggle">
        <el-button-group>
          <el-button :type="viewMode === 'card' ? 'primary' : ''" @click="viewMode = 'card'" size="small">
            <el-icon><Grid /></el-icon>
          </el-button>
          <el-button :type="viewMode === 'table' ? 'primary' : ''" @click="viewMode = 'table'" size="small">
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

    <div v-else class="products__table-wrapper">
      <el-table :data="filteredProducts" v-loading="productStore.loading" stripe>
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
              <span class="cell-rank__number">#{{ getRankingInfo(row.id).rank }}</span>
              <span class="cell-rank__total" v-if="getRankingInfo(row.id).total">/{{ getRankingInfo(row.id).total }}</span>
              <el-tag v-if="getRankingInfo(row.id).trend" size="small" effect="light"
                :type="getRankingInfo(row.id).trend === '上升' ? 'success' : getRankingInfo(row.id).trend === '下降' ? 'danger' : 'info'">
                {{ getRankingInfo(row.id).trend }}
              </el-tag>
            </div>
            <span v-else class="cell-secondary">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="360" fixed="right">
          <template #default="{ row }">
            <div class="product-cell__actions">
              <el-button size="small" @click="$router.push(`/products/${row.id}`)">详情</el-button>
              <el-button size="small" type="primary" @click="collectSingle(row)">采集</el-button>
              <el-dropdown v-permission="'gate:ai:basic_analysis'" @command="(cmd: string) => quickAIAnalysis(row, cmd)" size="small">
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
              <el-button v-permission="'gate:monitor:auto_refresh'" size="small" @click="addSchedule(row)">定时</el-button>
              <el-button size="small" type="danger" plain @click="confirmDelete(row.id)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="showAdd" title="添加小红书商品" width="560px">
      <el-form :model="addForm" :rules="addRules" ref="addFormRef">
        <el-form-item label="商品链接" prop="noteInput">
          <el-input v-model="addForm.noteInput" placeholder="粘贴小红书商品链接或商品ID" />
        </el-form-item>
        <el-form-item label="备注名称" prop="product_name">
          <el-input v-model="addForm.product_name" placeholder="可选，方便识别" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" @click="addProduct">添加并采集</el-button>
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
            <el-radio value="all">全部商品</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCollect = false">取消</el-button>
        <el-button type="primary" @click="startBatchCollect">开始采集</el-button>
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
  </div>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { Plus, Download, Goods, Grid, List, Search, MagicStick } from "@element-plus/icons-vue";
import PageHeader from "../components/PageHeader.vue";
import SearchInput from "../components/SearchInput.vue";
import EmptyState from "../components/EmptyState.vue";
import ProductCard from "../components/ProductCard.vue";
import { useProductsData } from "../composables/useProductsData";

const {
  productStore,
  showAdd, showCollect, showSchedule,
  addFormRef, addForm, addRules,
  concurrency, collectScope, scheduleFrequency,
  viewMode, searchQuery, filteredProducts,
  formatDate,
  addProduct, collectSingle, startBatchCollect,
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
  color: #D97706;
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
</style>
