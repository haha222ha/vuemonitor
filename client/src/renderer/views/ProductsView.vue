<template>
  <div class="products fade-in">
    <PageHeader title="商品监控" subtitle="管理和监控您的小红书商品数据">
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
      <div v-for="product in filteredProducts" :key="product.id" class="product-card">
        <div class="product-card__header">
          <el-image v-if="product.image_url" :src="product.image_url" class="product-card__image" fit="cover" />
          <div v-else class="product-card__image product-card__image--placeholder">
            <el-icon :size="24"><Goods /></el-icon>
          </div>
          <div class="product-card__info">
            <div class="product-card__name">{{ product.product_name }}</div>
            <div class="product-card__shop">{{ product.shop_name || '未知店铺' }}</div>
          </div>
        </div>
        <div class="product-card__body">
          <div class="product-card__meta">
            <span class="product-card__id">{{ product.platform_product_id }}</span>
            <span class="product-card__time">{{ product.last_collected_at ? formatDate(product.last_collected_at) : '未采集' }}</span>
          </div>
        </div>
        <div class="product-card__actions">
          <el-button size="small" @click="$router.push(`/products/${product.id}`)">详情</el-button>
          <el-button size="small" type="primary" @click="collectSingle(product)">采集</el-button>
          <el-button v-permission="'gate:monitor:auto_refresh'" size="small" @click="addSchedule(product)">定时</el-button>
          <el-button size="small" type="danger" plain @click="confirmDelete(product.id)">删除</el-button>
        </div>
      </div>
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
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <div class="product-cell__actions">
              <el-button size="small" @click="$router.push(`/products/${row.id}`)">详情</el-button>
              <el-button size="small" type="primary" @click="collectSingle(row)">采集</el-button>
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
import { ref, computed, onMounted } from "vue";
import { useProductStore } from "../stores/product";
import { useCollectStore } from "../stores/collect";
import { useSchedulerStore } from "../stores/scheduler";
import { usePermissionStore } from "../stores/permission";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { parseXHSUrl } from "@shared/constants/platforms";
import { Plus, Download, Goods, Grid, List, Search } from "@element-plus/icons-vue";
import PageHeader from "../components/PageHeader.vue";
import SearchInput from "../components/SearchInput.vue";
import EmptyState from "../components/EmptyState.vue";

const productStore = useProductStore();
const collectStore = useCollectStore();
const schedulerStore = useSchedulerStore();
const permissionStore = usePermissionStore();

const showAdd = ref(false);
const showCollect = ref(false);
const showSchedule = ref(false);
const addFormRef = ref<FormInstance>();
const addForm = ref({ noteInput: "", product_name: "" });
const concurrency = ref(3);
const collectScope = ref("all");
const scheduleFrequency = ref(60);
const scheduleProduct = ref<Record<string, unknown> | null>(null);
const viewMode = ref<"card" | "table">("card");
const searchQuery = ref("");

const addRules: FormRules = {
  noteInput: [{ required: true, message: "请输入小红书商品链接或ID", trigger: "blur" }],
};

const filteredProducts = computed(() => {
  if (!searchQuery.value) return productStore.products;
  const q = searchQuery.value.toLowerCase();
  return productStore.products.filter(
    (p) =>
      p.product_name?.toLowerCase().includes(q) ||
      p.platform_product_id?.toLowerCase().includes(q) ||
      p.shop_name?.toLowerCase().includes(q)
  );
});

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function resolveProductInput(input: string): { productId: string; targetType: string; targetUrl?: string } {
  const trimmed = input.trim();
  const parsed = parseXHSUrl(trimmed);
  if (parsed.type === "goods" && parsed.id) return { productId: parsed.id, targetType: "goods" };
  if (parsed.type === "note" && parsed.id && parsed.id !== "short_url") return { productId: parsed.id, targetType: "note" };
  if (parsed.type === "note" && parsed.id === "short_url") return { productId: "short_url", targetType: "note", targetUrl: trimmed };
  if (/^[a-f0-9]{8,}$/.test(trimmed)) return { productId: trimmed, targetType: "goods" };
  return { productId: trimmed, targetType: "goods", targetUrl: trimmed };
}

async function addProduct() {
  const valid = await addFormRef.value?.validate().catch(() => false);
  if (!valid) return;
  if (!permissionStore.canAddProduct) { ElMessage.warning("当前套餐商品数量已达上限，请升级"); return; }
  const { productId, targetType, targetUrl } = resolveProductInput(addForm.value.noteInput);
  try {
    await window.electronAPI.invoke("storage:insert-product", {
      platform: "xhs", platform_product_id: productId,
      product_name: addForm.value.product_name || `XHS商品 ${productId}`, target_url: targetUrl,
    });
    ElMessage.success("添加成功");
    showAdd.value = false;
    addForm.value = { noteInput: "", product_name: "" };
    await productStore.fetchProducts();
    collectSingle({ platform: "xhs", platform_product_id: productId, target_url: targetUrl, targetType });
  } catch { ElMessage.error("添加失败"); }
}

async function collectSingle(product: Record<string, unknown>) {
  const targetType = (product.targetType as string) || "goods";
  await collectStore.startCollect([{
    targetId: product.platform_product_id as string,
    targetType: targetType as "goods" | "note",
    targetUrl: product.target_url as string | undefined,
  }]);
  ElMessage.success("采集任务已提交");
}

async function startBatchCollect() {
  await collectStore.setConcurrency(concurrency.value);
  const targets = productStore.products.map((p) => ({
    targetId: p.platform_product_id,
    targetType: ((p as Record<string, unknown>).targetType as "goods" | "note") || "goods",
    targetUrl: (p as Record<string, unknown>).target_url as string | undefined,
  }));
  await collectStore.startCollect(targets);
  showCollect.value = false;
  ElMessage.success(`已提交 ${targets.length} 个采集任务`);
}

function addSchedule(product: Record<string, unknown>) {
  if (!permissionStore.canAutoRefresh) { ElMessage.warning("定时采集需要Pro及以上版本"); return; }
  scheduleProduct.value = product;
  showSchedule.value = true;
}

async function confirmSchedule() {
  if (!scheduleProduct.value) return;
  try {
    await schedulerStore.addTask({
      product_id: scheduleProduct.value.id as string,
      platform: "xhs",
      platform_product_id: scheduleProduct.value.platform_product_id as string,
      product_name: scheduleProduct.value.product_name as string,
      frequency_minutes: scheduleFrequency.value,
      is_active: true,
    });
    ElMessage.success("定时任务已创建");
    showSchedule.value = false;
  } catch { ElMessage.error("创建定时任务失败"); }
}

async function confirmDelete(id: string) {
  try {
    await ElMessageBox.confirm("确定要删除该商品监控吗？", "确认删除", {
      confirmButtonText: "删除", cancelButtonText: "取消", type: "warning",
    });
    await window.electronAPI.invoke("storage:run", "UPDATE products SET is_active = 0 WHERE id = ?", [id]);
    ElMessage.success("删除成功");
    await productStore.fetchProducts();
  } catch {}
}

onMounted(() => {
  productStore.fetchProducts();
  collectStore.setupListeners();
  collectStore.fetchStatus();
  permissionStore.fetchPermissions();
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

.product-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-light);
  padding: 20px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.product-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.product-card__header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.product-card__image {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-base);
  flex-shrink: 0;
  border: 1px solid var(--color-border-light);
}

.product-card__image--placeholder {
  background: var(--color-bg-page);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary);
}

.product-card__info {
  flex: 1;
  min-width: 0;
}

.product-card__name {
  font-weight: 500;
  font-size: var(--text-base);
  color: var(--color-text-primary);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.product-card__shop {
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

.product-card__body {
  margin-bottom: 16px;
}

.product-card__meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.product-card__id {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

.product-card__time {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.product-card__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
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
  .product-card__actions {
    flex-direction: column;
  }
}
</style>
