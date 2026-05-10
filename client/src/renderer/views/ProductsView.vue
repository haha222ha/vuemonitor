<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px">
      <h2>小红书商品监控</h2>
      <div style="display: flex; gap: 8px; align-items: center">
        <el-button v-permission="'gate:monitor:add'" type="primary" @click="showAdd = true">添加商品</el-button>
        <el-button v-permission="'gate:monitor:add'" type="success" @click="showCollect = true">立即采集</el-button>
      </div>
    </div>

    <el-table :data="productStore.products" v-loading="productStore.loading" stripe>
      <el-table-column label="商品" min-width="280">
        <template #default="{ row }">
          <div style="display: flex; align-items: center; gap: 8px">
            <el-image v-if="row.image_url" :src="row.image_url" style="width: 40px; height: 40px; border-radius: 4px" fit="cover" />
            <div>
              <div style="font-weight: 500; font-size: 13px">{{ row.product_name }}</div>
              <div style="color: #909399; font-size: 12px">{{ row.shop_name || '-' }}</div>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="商品ID" prop="platform_product_id" width="180" />
      <el-table-column label="最新采集" width="160">
        <template #default="{ row }">{{ row.last_collected_at ? formatDate(row.last_collected_at) : '未采集' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="260">
        <template #default="{ row }">
          <el-button size="small" @click="$router.push(`/products/${row.id}`)">详情</el-button>
          <el-button size="small" type="primary" @click="collectSingle(row)">采集</el-button>
          <el-button v-permission="'gate:monitor:auto_refresh'" size="small" type="warning" @click="addSchedule(row)">定时</el-button>
          <el-button size="small" type="danger" @click="confirmDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showAdd" title="添加小红书商品" width="500px">
      <el-form :model="addForm" :rules="addRules" ref="addFormRef" label-width="80px">
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

    <el-dialog v-model="showCollect" title="批量采集" width="500px">
      <el-form label-width="80px">
        <el-form-item label="并发数">
          <el-slider v-model="concurrency" :min="1" :max="10" :step="1" show-input />
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

    <el-dialog v-model="showSchedule" title="设置定时采集" width="400px">
      <el-form label-width="80px">
        <el-form-item label="采集频率">
          <el-select v-model="scheduleFrequency">
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
import { ref, onMounted } from "vue";
import { useProductStore } from "../stores/product";
import { useCollectStore } from "../stores/collect";
import { useSchedulerStore } from "../stores/scheduler";
import { usePermissionStore } from "../stores/permission";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { parseXHSUrl } from "../../../shared/constants/platforms";

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

function resolveNoteInput(input: string): { noteId: string; targetUrl?: string } {
  const trimmed = input.trim();
  const parsed = parseXHSUrl(trimmed);
  if (parsed.type === "note" && parsed.id && parsed.id !== "short_url") {
    return { noteId: parsed.id };
  }
  if (parsed.type === "note" && parsed.id === "short_url") {
    return { noteId: "short_url", targetUrl: trimmed };
  }
  if (/^[a-f0-9]{8,}$/.test(trimmed)) {
    return { noteId: trimmed };
  }
  return { noteId: trimmed, targetUrl: trimmed };
}

async function addProduct() {
  const valid = await addFormRef.value?.validate().catch(() => false);
  if (!valid) return;

  if (!permissionStore.canAddProduct) {
    ElMessage.warning("当前套餐商品数量已达上限，请升级");
    return;
  }

  const { noteId, targetUrl } = resolveNoteInput(addForm.value.noteInput);

  try {
    await window.electronAPI.invoke("storage:insert-product", {
      platform: "xhs",
      platform_product_id: noteId,
      product_name: addForm.value.product_name || `XHS商品 ${noteId}`,
      target_url: targetUrl,
    });
    ElMessage.success("添加成功");
    showAdd.value = false;
    addForm.value = { noteInput: "", product_name: "" };
    await productStore.fetchProducts();
    collectSingle({ platform: "xhs", platform_product_id: noteId, target_url: targetUrl });
  } catch {
    ElMessage.error("添加失败");
  }
}

async function collectSingle(product: Record<string, unknown>) {
  await collectStore.startCollect([
    {
      targetId: product.platform_product_id as string,
      targetType: "note",
      targetUrl: product.target_url as string | undefined,
    },
  ]);
  ElMessage.success("采集任务已提交");
}

async function startBatchCollect() {
  await collectStore.setConcurrency(concurrency.value);
  const targets = productStore.products.map((p) => ({
    targetId: p.platform_product_id,
    targetType: "note" as const,
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
