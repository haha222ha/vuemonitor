<template>
  <el-dialog
    v-model="dialogVisible"
    title="批量导入商品ID"
    width="520px"
    :before-close="handleClose"
    :close-on-click-modal="false"
  >
    <div class="import-dialog">
      <div
        class="drop-zone"
        :class="{ 'drop-zone--active': isDragging, 'drop-zone--success': hasFile }"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="handleDrop"
      >
        <input
          ref="fileInput"
          type="file"
          accept=".xlsx,.xls,.csv"
          class="file-input"
          @change="handleFileSelect"
        >
        <div class="drop-zone__content">
          <el-icon v-if="!hasFile" size="48" class="drop-zone__icon">
            <Upload />
          </el-icon>
          <div v-else class="drop-zone__preview">
            <el-icon size="32">
              <Document />
            </el-icon>
            <span>{{ fileName }}</span>
          </div>
          <p v-if="!hasFile" class="drop-zone__text">
            拖拽文件到此处，或点击选择文件
          </p>
          <p class="drop-zone__hint">支持 .xlsx .xls .csv 格式</p>
          <el-button link type="primary" class="drop-zone__template" @click.stop="downloadTemplate">
            <el-icon><Download /></el-icon>
            下载导入模板
          </el-button>
        </div>
      </div>

      <div v-if="parsedData.length > 0" class="import-dialog__preview">
        <div class="preview-header">
          <span>解析结果预览</span>
          <span class="preview-count">共 {{ parsedData.length }} 条</span>
        </div>
        <div class="preview-content">
          <div
            v-for="(item, index) in displayData"
            :key="index"
            :class="['preview-item', { 'preview-item--invalid': !item.valid }]"
          >
            <span class="preview-item__index">{{ index + 1 }}</span>
            <span class="preview-item__value">{{ item.value }}</span>
            <span v-if="!item.valid" class="preview-item__error">格式无效</span>
          </div>
          <div v-if="parsedData.length > 10" class="preview-more">
            还有 {{ parsedData.length - 10 }} 条...
          </div>
        </div>
      </div>

      <div v-if="importStatus === 'importing'" class="import-dialog__progress">
        <el-progress :percentage="importProgress" :status="importProgressStatus" />
        <p class="progress-text">{{ importMessage }}</p>
      </div>

      <div v-if="importStatus === 'completed'" class="import-dialog__result">
        <div class="result-stats">
          <div class="result-stat result-stat--success">
            <span class="result-stat__icon">✅</span>
            <span class="result-stat__count">{{ importResult.success }}</span>
            <span class="result-stat__label">成功导入</span>
          </div>
          <div class="result-stat result-stat--duplicate">
            <span class="result-stat__icon">⚠️</span>
            <span class="result-stat__count">{{ importResult.duplicate }}</span>
            <span class="result-stat__label">已存在</span>
          </div>
          <div class="result-stat result-stat--failed">
            <span class="result-stat__icon">❌</span>
            <span class="result-stat__count">{{ importResult.failed }}</span>
            <span class="result-stat__label">导入失败</span>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button
        v-if="!hasFile"
        type="primary"
        :disabled="!hasFile"
        @click="triggerFileInput"
      >
        选择文件
      </el-button>
      <el-button
        v-else-if="importStatus !== 'importing'"
        type="primary"
        @click="startImport"
      >
        {{ importStatus === 'completed' ? '导入更多' : '开始导入' }}
      </el-button>
      <el-button
        v-else
        type="primary"
        loading
      >
        导入中...
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { Upload, Document, Download } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import * as XLSX from "xlsx";

interface ParsedItem {
  value: string;
  valid: boolean;
  product_name?: string;
  category?: string;
}

interface ImportResult {
  success: number;
  duplicate: number;
  failed: number;
}

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "import-complete", result: ImportResult): void;
}>();

const dialogVisible = computed({
  get: () => props.visible,
  set: (val: boolean) => emit("update:visible", val),
});

const fileInput = ref<HTMLInputElement | null>(null);
const isDragging = ref(false);
const hasFile = ref(false);
const fileName = ref("");
const parsedData = ref<ParsedItem[]>([]);
const importStatus = ref<"idle" | "parsing" | "importing" | "completed">("idle");
const importProgress = ref(0);
const importMessage = ref("");
const importResult = ref<ImportResult>({
  success: 0,
  duplicate: 0,
  failed: 0,
});

const displayData = computed(() => parsedData.value.slice(0, 10));

const importProgressStatus = computed(() => {
  if (importResult.value.failed > 0 && importResult.value.success === 0) return "exception";
  if (importProgress.value < 100) return "active";
  return "success";
});

function triggerFileInput() {
  fileInput.value?.click();
}

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (file) {
    processFile(file);
  }
}

function handleDrop(event: DragEvent) {
  isDragging.value = false;
  const file = event.dataTransfer?.files?.[0];
  if (file && (file.type.includes("spreadsheet") || file.type.includes("csv") || file.name.match(/\.(xlsx|xls|csv)$/))) {
    processFile(file);
  }
}

function processFile(file: File) {
  fileName.value = file.name;
  hasFile.value = true;
  importStatus.value = "parsing";

  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const data = new Uint8Array(e.target?.result as ArrayBuffer);
      const workbook = XLSX.read(data, { type: "array" });
      const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
      const jsonData = XLSX.utils.sheet_to_json(firstSheet, { header: 1 }) as string[][];
      parseProductIds(jsonData);
      importStatus.value = "idle";
    } catch (error) {
      console.error("解析文件失败:", error);
      ElMessage.error("文件解析失败，请确保文件格式正确");
      importStatus.value = "idle";
    }
  };
  reader.readAsArrayBuffer(file);
}

function parseProductIds(data: string[][]) {
  const ids: ParsedItem[] = [];
  const seen = new Set<string>();

  if (data.length > 1) {
    const header = data[0].map((h) => String(h || "").trim());
    const idColIdx = header.findIndex((h) =>
      ["商品ID", "goods_id", "product_id", "商品id", "ID"].includes(h)
    );
    const nameColIdx = header.findIndex((h) =>
      ["商品名称", "product_name", "名称", "商品名"].includes(h)
    );
    const catColIdx = header.findIndex((h) =>
      ["分类", "category", "类目"].includes(h)
    );

    if (idColIdx >= 0) {
      for (let i = 1; i < data.length; i++) {
        const row = data[i];
        const cell = row[idColIdx];
        if (cell !== null && cell !== undefined && cell !== "") {
          const value = String(cell).trim();
          if (!seen.has(value)) {
            seen.add(value);
            ids.push({
              value,
              valid: isValidProductId(value),
              product_name: nameColIdx >= 0 && row[nameColIdx] ? String(row[nameColIdx]).trim() : undefined,
              category: catColIdx >= 0 && row[catColIdx] ? String(row[catColIdx]).trim() : undefined,
            });
          }
        }
      }
      if (ids.length > 0) {
        parsedData.value = ids;
        return;
      }
    }
  }

  for (const row of data) {
    for (const cell of row) {
      if (cell !== null && cell !== undefined && cell !== "") {
        const value = String(cell).trim();
        if (!seen.has(value)) {
          seen.add(value);
          ids.push({
            value,
            valid: isValidProductId(value),
          });
        }
      }
    }
  }
  parsedData.value = ids;
}

function isValidProductId(id: string): boolean {
  return id.length >= 8 && id.length <= 20 && /^[a-zA-Z0-9_-]+$/.test(id);
}

async function startImport() {
  const validItems = parsedData.value.filter((item) => item.valid);
  if (validItems.length === 0) {
    ElMessage.warning("没有有效的商品ID");
    return;
  }

  importStatus.value = "importing";
  importProgress.value = 0;
  importMessage.value = "正在导入...";
  importResult.value = { success: 0, duplicate: 0, failed: 0 };

  try {
    const products = validItems.map((item) => ({
      platform: "xhs",
      platform_product_id: item.value,
      product_name: item.product_name || `小红书商品${item.value.slice(0, 8)}`,
      category: item.category || null,
    }));

    const batchSize = 50;
    let totalImported = 0;
    let totalDuplicated = 0;
    let totalFailed = 0;

    for (let i = 0; i < products.length; i += batchSize) {
      const batch = products.slice(i, i + batchSize);
      const response = (await window.electronAPI?.invoke?.(
        "storage:batch-insert-products",
        batch
      )) as { imported: number; duplicated: number; failed: number } | undefined;

      totalImported += response?.imported || 0;
      totalDuplicated += response?.duplicated || 0;
      totalFailed += response?.failed || 0;

      importProgress.value = Math.min(100, Math.round(((i + batch.length) / products.length) * 100));
      importMessage.value = `已处理 ${Math.min(i + batch.length, products.length)} / ${products.length}`;
    }

    importResult.value = {
      success: totalImported,
      duplicate: totalDuplicated,
      failed: totalFailed,
    };
    importProgress.value = 100;
    importMessage.value = "导入完成";
    importStatus.value = "completed";
    emit("import-complete", importResult.value);

    if (totalImported > 0) {
      ElMessage.success(`成功导入 ${totalImported} 个商品`);
    }
  } catch (error) {
    console.error("导入失败:", error);
    ElMessage.error("导入失败，请重试");
    importStatus.value = "idle";
  }
}

function downloadTemplate() {
  const csv = "商品ID,商品名称,分类\n65a1b2c3d4e5f67890123456,示例商品名称,家居\n7b2c3d4e5f6a78901234567,示例商品2,美妆\n";
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "XHS365_导入模板.csv";
  a.click();
  URL.revokeObjectURL(url);
}

function handleClose() {
  resetState();
  emit("update:visible", false);
}

function resetState() {
  hasFile.value = false;
  fileName.value = "";
  parsedData.value = [];
  importStatus.value = "idle";
  importProgress.value = 0;
  importMessage.value = "";
  if (fileInput.value) {
    fileInput.value.value = "";
  }
}
</script>

<style lang="scss" scoped>
.import-dialog {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.drop-zone {
  border: 2px dashed #d9d9d9;
  border-radius: 12px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;

  &--active {
    border-color: #409eff;
    background: #ecf5ff;
  }

  &--success {
    border-color: #67c23a;
    background: #f0fdf4;
  }
}

.file-input {
  display: none;
}

.drop-zone__content {
  pointer-events: none;
}

.drop-zone__icon {
  color: #409eff;
  margin-bottom: 12px;
}

.drop-zone__text {
  font-size: 16px;
  color: #666;
  margin-bottom: 8px;
}

.drop-zone__hint {
  font-size: 12px;
  color: #999;
}

.drop-zone__template {
  margin-top: 8px;
  pointer-events: auto;
}

.drop-zone__preview {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #67c23a;
}

.import-dialog__preview {
  background: #fafafa;
  border-radius: 8px;
  padding: 12px;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
}

.preview-count {
  font-weight: normal;
  color: #999;
}

.preview-content {
  max-height: 200px;
  overflow-y: auto;
}

.preview-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 0;
  border-bottom: 1px solid #eee;
  font-family: monospace;

  &--invalid {
    color: #dc2626;
  }
}

.preview-item__index {
  width: 28px;
  text-align: right;
  color: #999;
  font-size: 12px;
}

.preview-item__value {
  flex: 1;
}

.preview-item__error {
  font-size: 11px;
  color: #dc2626;
}

.preview-more {
  text-align: center;
  padding: 8px;
  color: #999;
  font-size: 12px;
}

.import-dialog__progress {
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
}

.progress-text {
  text-align: center;
  margin-top: 8px;
  font-size: 14px;
  color: #666;
}

.import-dialog__result {
  padding: 16px;
}

.result-stats {
  display: flex;
  justify-content: center;
  gap: 32px;
}

.result-stat {
  text-align: center;
  padding: 16px;
  border-radius: 8px;

  &--success {
    background: #f0fdf4;
    color: #16a34a;
  }

  &--duplicate {
    background: #fefce8;
    color: #ca8a04;
  }

  &--failed {
    background: #fef2f2;
    color: #dc2626;
  }
}

.result-stat__icon {
  font-size: 24px;
  display: block;
  margin-bottom: 8px;
}

.result-stat__count {
  font-size: 24px;
  font-weight: 600;
  display: block;
}

.result-stat__label {
  font-size: 12px;
}
</style>