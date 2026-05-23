<template>
  <el-dialog v-model="visible" title="导出商品数据" width="520px" append-to-body @close="$emit('close')">
    <div class="export-dialog__section">
      <h4 class="export-dialog__subtitle">选择导出格式</h4>
      <el-radio-group v-model="format">
        <el-radio-button value="xlsx">Excel (.xlsx)</el-radio-button>
        <el-radio-button value="csv">CSV (.csv)</el-radio-button>
      </el-radio-group>
    </div>

    <div class="export-dialog__section">
      <h4 class="export-dialog__subtitle">选择导出字段</h4>
      <el-checkbox v-model="selectAll" :indeterminate="isIndeterminate" @change="handleSelectAll">
        全选
      </el-checkbox>
      <el-divider style="margin: 8px 0" />
      <el-checkbox-group v-model="selectedFields">
        <el-checkbox v-for="field in availableFields" :key="field.key" :value="field.key">
          {{ field.label }}
        </el-checkbox>
      </el-checkbox-group>
    </div>

    <div class="export-dialog__section">
      <h4 class="export-dialog__subtitle">导出范围</h4>
      <el-radio-group v-model="scope">
        <el-radio value="all">全部商品 ({{ totalCount }})</el-radio>
        <el-radio value="filtered">当前筛选 ({{ filteredCount }})</el-radio>
      </el-radio-group>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="handleExport" :loading="exporting" :disabled="selectedFields.length === 0">
        导出
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { ElMessage } from "element-plus";
import * as XLSX from "xlsx";

interface ProductRow {
  [key: string]: unknown;
}

const props = defineProps<{
  modelValue: boolean;
  products: ProductRow[];
  totalCount: number;
  filteredCount: number;
}>();

const emit = defineEmits<{
  "update:modelValue": [val: boolean];
  close: [];
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});

const format = ref<"xlsx" | "csv">("xlsx");
const scope = ref<"all" | "filtered">("filtered");
const exporting = ref(false);

const availableFields = [
  { key: "product_name", label: "商品名称" },
  { key: "platform", label: "平台" },
  { key: "platform_product_id", label: "平台ID" },
  { key: "shop_name", label: "店铺名称" },
  { key: "category", label: "分类" },
  { key: "price", label: "价格" },
  { key: "original_price", label: "原价" },
  { key: "sales_count", label: "销量" },
  { key: "monthly_sales", label: "月销量" },
  { key: "rating", label: "评分" },
  { key: "review_count", label: "评论数" },
  { key: "favorite_count", label: "收藏数" },
  { key: "stock_status", label: "库存状态" },
  { key: "is_active", label: "状态" },
  { key: "last_collected_at", label: "最后采集时间" },
  { key: "created_at", label: "创建时间" },
  { key: "growth_24h_sales_pct", label: "24h销量增长%" },
  { key: "growth_24h_price_pct", label: "24h价格变化%" },
  { key: "trend", label: "趋势" },
  { key: "last_collect_status", label: "采集状态" },
];

const selectedFields = ref<string[]>([
  "product_name", "platform", "shop_name", "category",
  "price", "sales_count", "rating", "review_count",
]);

const selectAll = ref(false);
const isIndeterminate = computed(() => {
  const total = availableFields.length;
  return selectedFields.value.length > 0 && selectedFields.value.length < total;
});

watch(selectedFields, (val) => {
  selectAll.value = val.length === availableFields.length;
});

function handleSelectAll(val: boolean | string | number) {
  if (val) {
    selectedFields.value = availableFields.map((f) => f.key);
  } else {
    selectedFields.value = [];
  }
}

async function handleExport() {
  if (selectedFields.value.length === 0) {
    ElMessage.warning("请至少选择一个导出字段");
    return;
  }

  exporting.value = true;
  try {
    const data = props.products;
    if (!data || data.length === 0) {
      ElMessage.warning("没有可导出的数据");
      return;
    }

    const fieldLabels: Record<string, string> = {};
    for (const f of availableFields) {
      fieldLabels[f.key] = f.label;
    }

    const headers = selectedFields.value.map((key) => fieldLabels[key] || key);
    const rows = data.map((row) => {
      const item: Record<string, unknown> = {};
      for (const key of selectedFields.value) {
        let val = row[key];
        if (key === "is_active") val = val ? "启用" : "禁用";
        if (key === "growth_24h_sales_pct" && row.growth_24h) val = (row.growth_24h as Record<string, unknown>).sales_pct ?? "";
        if (key === "growth_24h_price_pct" && row.growth_24h) val = (row.growth_24h as Record<string, unknown>).price_pct ?? "";
        if ((key === "price" || key === "original_price" || key === "rating") && val != null) {
          val = Number(val);
        }
        if (key === "last_collect_status") {
          const statusMap: Record<string, string> = { pending: "等待中", success: "成功", failed: "失败" };
          val = statusMap[String(val)] || val || "";
        }
        item[fieldLabels[key] || key] = val ?? "";
      }
      return item;
    });

    const ws = XLSX.utils.json_to_sheet(rows, { header: headers });
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "商品数据");

    const timestamp = new Date().toISOString().slice(0, 10);
    const filename = `商品数据_${timestamp}`;

    if (format.value === "xlsx") {
      XLSX.writeFile(wb, `${filename}.xlsx`);
    } else {
      XLSX.writeFile(wb, `${filename}.csv`);
    }

    ElMessage.success(`已导出 ${rows.length} 条数据`);
    visible.value = false;
  } catch (err) {
    ElMessage.error("导出失败：" + String(err));
  } finally {
    exporting.value = false;
  }
}
</script>

<style scoped>
.export-dialog__section { margin-bottom: 20px; }
.export-dialog__subtitle { font-size: 14px; font-weight: 600; color: #e0e0ea; margin: 0 0 12px; }
</style>
