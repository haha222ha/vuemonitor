<template>
  <div class="products-page">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">小红书商品监控</h1>
        <p class="page-subtitle">管理和监控您的小红书商品数据</p>
      </div>
      <div class="header-actions">
        <el-button v-permission="'gate:monitor:add'" class="btn-primary" @click="showAdd = true">
          <el-icon><Plus /></el-icon>
          添加商品
        </el-button>
        <el-button v-permission="'gate:monitor:add'" class="btn-success" @click="showCollect = true">
          <el-icon><Download /></el-icon>
          立即采集
        </el-button>
      </div>
    </div>

    <div class="products-table-wrapper">
      <el-table :data="productStore.products" v-loading="productStore.loading" class="modern-table" stripe>
        <el-table-column label="商品" min-width="280">
          <template #default="{ row }">
            <div class="product-cell">
              <el-image v-if="row.image_url" :src="row.image_url" class="product-image" fit="cover" />
              <div class="product-info">
                <div class="product-name">{{ row.product_name }}</div>
                <div class="product-shop">{{ row.shop_name || '-' }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="商品ID" prop="platform_product_id" width="180">
          <template #default="{ row }">
            <span class="product-id">{{ row.platform_product_id }}</span>
          </template>
        </el-table-column>
        <el-table-column label="最新采集" width="160">
          <template #default="{ row }">
            <span class="collect-time">{{ row.last_collected_at ? formatDate(row.last_collected_at) : '未采集' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button size="small" class="btn-detail" @click="$router.push(`/products/${row.id}`)">详情</el-button>
              <el-button size="small" type="primary" class="btn-collect" @click="collectSingle(row)">采集</el-button>
              <el-button v-permission="'gate:monitor:auto_refresh'" size="small" class="btn-schedule" @click="addSchedule(row)">定时</el-button>
              <el-button size="small" class="btn-delete" @click="confirmDelete(row.id)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog 
      v-model="showAdd" 
      title="添加小红书商品" 
      width="560px"
      class="modern-dialog"
      :close-on-click-modal="true"
      :close-on-press-escape="true"
      :show-close="true"
    >
      <div class="dialog-body">
        <el-form :model="addForm" :rules="addRules" ref="addFormRef" class="modern-form">
          <el-form-item label="商品链接" prop="noteInput">
            <el-input 
              v-model="addForm.noteInput" 
              placeholder="粘贴小红书商品链接或商品ID"
              class="modern-input"
            />
          </el-form-item>
          <el-form-item label="备注名称" prop="product_name">
            <el-input 
              v-model="addForm.product_name" 
              placeholder="可选，方便识别"
              class="modern-input"
            />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showAdd = false">取消</el-button>
          <el-button type="primary" @click="addProduct">添加并采集</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog 
      v-model="showCollect" 
      title="批量采集" 
      width="560px"
      class="modern-dialog"
      :close-on-click-modal="true"
      :close-on-press-escape="true"
      :show-close="true"
    >
      <div class="dialog-body">
        <el-form class="modern-form" label-position="top">
          <el-form-item label="并发数">
            <div class="slider-wrapper">
              <el-slider v-model="concurrency" :min="1" :max="10" :step="1" class="modern-slider" />
              <span class="slider-value">{{ concurrency }}</span>
            </div>
          </el-form-item>
          <el-form-item label="采集范围">
            <el-radio-group v-model="collectScope" class="modern-radio-group">
              <el-radio value="all">全部商品</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showCollect = false">取消</el-button>
          <el-button type="primary" @click="startBatchCollect">开始采集</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog 
      v-model="showSchedule" 
      title="设置定时采集" 
      width="480px"
      class="modern-dialog"
      :close-on-click-modal="true"
      :close-on-press-escape="true"
      :show-close="true"
    >
      <div class="dialog-body">
        <el-form class="modern-form" label-position="top">
          <el-form-item label="采集频率">
            <el-select v-model="scheduleFrequency" class="modern-select" style="width: 100%">
              <el-option label="每30分钟" :value="30" />
              <el-option label="每1小时" :value="60" />
              <el-option label="每2小时" :value="120" />
              <el-option label="每6小时" :value="360" />
              <el-option label="每12小时" :value="720" />
              <el-option label="每天" :value="1440" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showSchedule = false">取消</el-button>
          <el-button type="primary" @click="confirmSchedule">确认</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useProductStore } from "../stores/product";
import { useCollectStore } from "../stores/collect";
import { useSchedulerStore } from "../stores/scheduler";
import { usePermissionStore } from "../stores/permission";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { parseXHSUrl } from "@shared/constants/platforms";
import { Plus, Download } from "@element-plus/icons-vue";

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

const addRules: FormRules = {
  noteInput: [{ required: true, message: "请输入小红书商品链接或ID", trigger: "blur" }],
};

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function resolveProductInput(input: string): { productId: string; targetType: string; targetUrl?: string } {
  const trimmed = input.trim();
  const parsed = parseXHSUrl(trimmed);
  if (parsed.type === "goods" && parsed.id) {
    return { productId: parsed.id, targetType: "goods" };
  }
  if (parsed.type === "note" && parsed.id && parsed.id !== "short_url") {
    return { productId: parsed.id, targetType: "note" };
  }
  if (parsed.type === "note" && parsed.id === "short_url") {
    return { productId: "short_url", targetType: "note", targetUrl: trimmed };
  }
  if (/^[a-f0-9]{8,}$/.test(trimmed)) {
    return { productId: trimmed, targetType: "goods" };
  }
  return { productId: trimmed, targetType: "goods", targetUrl: trimmed };
}

async function addProduct() {
  const valid = await addFormRef.value?.validate().catch(() => false);
  if (!valid) return;

  if (!permissionStore.canAddProduct) {
    ElMessage.warning("当前套餐商品数量已达上限，请升级");
    return;
  }

  const { productId, targetType, targetUrl } = resolveProductInput(addForm.value.noteInput);

  try {
    await window.electronAPI.invoke("storage:insert-product", {
      platform: "xhs",
      platform_product_id: productId,
      product_name: addForm.value.product_name || `XHS商品 ${productId}`,
      target_url: targetUrl,
    });
    ElMessage.success("添加成功");
    showAdd.value = false;
    addForm.value = { noteInput: "", product_name: "" };
    await productStore.fetchProducts();
    collectSingle({ platform: "xhs", platform_product_id: productId, target_url: targetUrl, targetType });
  } catch {
    ElMessage.error("添加失败");
  }
}

async function collectSingle(product: Record<string, unknown>) {
  const targetType = (product.targetType as string) || "goods";
  await collectStore.startCollect([
    {
      targetId: product.platform_product_id as string,
      targetType: targetType as "goods" | "note",
      targetUrl: product.target_url as string | undefined,
    },
  ]);
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
  if (!permissionStore.canAutoRefresh) {
    ElMessage.warning("定时采集需要Pro及以上版本");
    return;
  }
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
  } catch {
    ElMessage.error("创建定时任务失败");
  }
}

async function confirmDelete(id: string) {
  try {
    await ElMessageBox.confirm("确定要删除该商品监控吗？", "确认删除", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
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
.products-page {
  padding: 24px;
  background: #f5f7fa;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  gap: 16px;
}

.header-left {
  flex: 1;
}

.page-title {
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  letter-spacing: -0.5px;
}

.page-subtitle {
  margin: 0;
  font-size: 14px;
  color: #6b7280;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.btn-primary,
.btn-success {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border-radius: 10px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-primary {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border: none;
  color: #fff;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
}

.btn-success {
  background: linear-gradient(135deg, #10b981, #34d399);
  border: none;
  color: #fff;
}

.btn-success:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.products-table-wrapper {
  background: #fff;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #f3f4f6;
}

.modern-table {
  border-radius: 8px;
}

.product-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.product-image {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  flex-shrink: 0;
  border: 1px solid #f3f4f6;
}

.product-info {
  flex: 1;
  min-width: 0;
}

.product-name {
  font-weight: 500;
  font-size: 14px;
  color: #1a1a2e;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.product-shop {
  color: #9ca3af;
  font-size: 12px;
}

.product-id {
  font-family: monospace;
  font-size: 13px;
  color: #6b7280;
}

.collect-time {
  font-size: 13px;
  color: #6b7280;
}

.action-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.btn-detail,
.btn-collect,
.btn-schedule,
.btn-delete {
  border-radius: 8px;
  font-size: 13px;
}

.btn-delete {
  color: #ef4444;
  border-color: #fecaca;
}

.btn-delete:hover {
  background: #fef2f2;
  border-color: #ef4444;
}

.modern-dialog :deep(.el-dialog__header) {
  padding: 20px 24px;
  border-bottom: 1px solid #f3f4f6;
  margin-right: 0;
}

.modern-dialog :deep(.el-dialog__title) {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a2e;
}

.modern-dialog :deep(.el-dialog__body) {
  padding: 24px;
}

.modern-dialog :deep(.el-dialog__footer) {
  padding: 16px 24px;
  border-top: 1px solid #f3f4f6;
}

.dialog-body {
  padding: 8px 0;
}

.modern-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.modern-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: #374151;
  margin-bottom: 8px;
}

.modern-input {
  border-radius: 10px;
}

.slider-wrapper {
  display: flex;
  align-items: center;
  gap: 16px;
}

.modern-slider {
  flex: 1;
}

.slider-value {
  font-size: 18px;
  font-weight: 600;
  color: #6366f1;
  min-width: 32px;
  text-align: center;
}

.modern-radio-group {
  display: flex;
  gap: 16px;
}

.modern-select {
  border-radius: 10px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 768px) {
  .products-page {
    padding: 16px;
  }
  
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .header-actions {
    width: 100%;
  }
  
  .btn-primary,
  .btn-success {
    flex: 1;
    justify-content: center;
  }
  
  .action-buttons {
    flex-direction: column;
  }
}
</style>
