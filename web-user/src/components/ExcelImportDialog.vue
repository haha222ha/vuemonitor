<template>
  <el-dialog v-model="visible" title="批量导入商品" width="600px" @close="reset">
    <div class="excel-import">
      <div class="excel-import__upload">
        <el-upload
          drag
          accept=".xlsx,.xls,.csv"
          :auto-upload="false"
          :limit="1"
          :on-change="handleFileChange"
          :on-exceed="() => ElMessage.warning('只能上传一个文件')"
        >
          <el-icon :size="48"><UploadFilled /></el-icon>
          <div class="excel-import__upload-text">拖拽文件到此处，或<em>点击上传</em></div>
          <template #tip>
            <div class="excel-import__upload-tip">
              支持 .xlsx / .xls / .csv 格式，单次最多 100 条
            </div>
          </template>
        </el-upload>
      </div>

      <div class="excel-import__template">
        <el-button link type="primary" @click="downloadTemplate">
          <el-icon><Download /></el-icon>
          下载导入模板
        </el-button>
      </div>

      <div v-if="parsedData.length > 0" class="excel-import__preview">
        <div class="excel-import__preview-header">
          <span>解析结果：共 {{ parsedData.length }} 条</span>
          <el-tag v-if="duplicatedCount > 0" type="warning" size="small">
            {{ duplicatedCount }} 条重复
          </el-tag>
        </div>
        <el-table :data="parsedData.slice(0, 10)" size="small" max-height="200">
          <el-table-column prop="platform_product_id" label="商品ID" width="200" />
          <el-table-column prop="product_name" label="商品名称" min-width="150" />
          <el-table-column prop="category" label="分类" width="100" />
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag v-if="row._duplicate" type="warning" size="small">重复</el-tag>
              <el-tag v-else type="success" size="small">正常</el-tag>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="parsedData.length > 10" class="excel-import__more">
          仅展示前 10 条，共 {{ parsedData.length }} 条
        </div>
      </div>

      <div v-if="importResult" class="excel-import__result">
        <el-result
          :icon="importResult.failed > 0 ? 'warning' : 'success'"
          :title="importResult.failed > 0 ? '部分导入成功' : '导入完成'"
        >
          <template #extra>
            <div class="excel-import__result-stats">
              <span>总计 {{ importResult.total }}</span>
              <span class="excel-import__result-success">成功 {{ importResult.imported }}</span>
              <span class="excel-import__result-dup">重复 {{ importResult.duplicated }}</span>
              <span v-if="importResult.failed > 0" class="excel-import__result-fail">失败 {{ importResult.failed }}</span>
            </div>
          </template>
        </el-result>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button
        type="primary"
        :loading="importing"
        :disabled="parsedData.length === 0 || importResult !== null"
        @click="doImport"
      >
        {{ importing ? '导入中...' : '确认导入' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { UploadFilled, Download } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import api from "../utils/api";

interface ParsedRow {
  platform_product_id: string;
  product_name: string;
  category: string;
  _duplicate: boolean;
}

interface ImportResult {
  total: number;
  imported: number;
  duplicated: number;
  failed: number;
}

const props = defineProps<{ modelValue: boolean }>();
const emit = defineEmits<{ "update:modelValue": [val: boolean] }>();

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val),
});

const parsedData = ref<ParsedRow[]>([]);
const duplicatedCount = ref(0);
const importing = ref(false);
const importResult = ref<ImportResult | null>(null);

async function handleFileChange(file: any) {
  if (!file?.raw) return;
  const ext = file.name.split(".").pop()?.toLowerCase();
  if (!["xlsx", "xls", "csv"].includes(ext || "")) {
    ElMessage.error("仅支持 xlsx/xls/csv 格式");
    return;
  }

  try {
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    const XLSX = await import("xlsx");
    const arrayBuffer = await file.raw.arrayBuffer();
    const workbook = XLSX.read(arrayBuffer, { type: "array" });
    const sheet = workbook.Sheets[workbook.SheetNames[0]];
    const rows = XLSX.utils.sheet_to_json(sheet) as Record<string, unknown>[];

    const parsed: ParsedRow[] = [];
    for (const row of rows) {
      const id = String(row["商品ID"] || row["goods_id"] || row["product_id"] || row["A"] || "").trim();
      if (!id) continue;
      parsed.push({
        platform_product_id: id,
        product_name: String(row["商品名称"] || row["product_name"] || row["B"] || "").trim(),
        category: String(row["分类"] || row["category"] || row["C"] || "").trim(),
        _duplicate: false,
      });
    }

    if (parsed.length === 0) {
      ElMessage.warning("未解析到有效数据，请检查文件格式");
      return;
    }

    if (parsed.length > 100) {
      ElMessage.warning("单次最多导入 100 条，已截取前 100 条");
      parsed.splice(100);
    }

    duplicatedCount.value = 0;
    parsedData.value = parsed;
  } catch (err) {
    ElMessage.error("文件解析失败：" + String(err));
  }
}

async function doImport() {
  const validItems = parsedData.value.filter((r) => !r._duplicate);
  if (validItems.length === 0) {
    ElMessage.warning("没有可导入的数据");
    return;
  }

  importing.value = true;
  try {
    const { data } = await api.post("/products/batch-import", {
      items: validItems.map((r) => ({
        platform: "xhs",
        platform_product_id: r.platform_product_id,
        product_name: r.product_name || null,
        category: r.category || null,
      })),
    });
    if (data?.code === 0 || data?.imported != null) {
      importResult.value = data.data || data;
    }
    ElMessage.success("导入完成");
  } catch (err: any) {
    ElMessage.error("导入失败：" + (err?.response?.data?.message || String(err)));
  } finally {
    importing.value = false;
  }
}

function downloadTemplate() {
  const csv = "商品ID,商品名称,分类\n65a1b2c3d4e5f67890123456,示例商品名称,家居\n";
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "XHS365_导入模板.csv";
  a.click();
  URL.revokeObjectURL(url);
}

function reset() {
  parsedData.value = [];
  duplicatedCount.value = 0;
  importResult.value = null;
  importing.value = false;
}
</script>

<style scoped>
.excel-import__upload {
  margin-bottom: 16px;
}

.excel-import__upload-text {
  color: #6a6a7a;
  font-size: 14px;
}

.excel-import__upload-text em {
  color: #6366f1;
  font-style: normal;
}

.excel-import__upload-tip {
  color: #5a5a6a;
  font-size: 12px;
  margin-top: 4px;
}

.excel-import__template {
  margin-bottom: 16px;
}

.excel-import__preview {
  margin-top: 16px;
}

.excel-import__preview-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #e0e0e6;
}

.excel-import__more {
  text-align: center;
  color: #5a5a6a;
  font-size: 12px;
  padding: 8px;
}

.excel-import__result-stats {
  display: flex;
  gap: 24px;
  justify-content: center;
  font-size: 14px;
  color: #e0e0e6;
}

.excel-import__result-success { color: #22c55e; }
.excel-import__result-dup { color: #eab308; }
.excel-import__result-fail { color: #ef4444; }
</style>
