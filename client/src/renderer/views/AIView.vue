<template>
  <div>
    <h2>AI分析</h2>
    <el-table :data="analyses" stripe v-loading="loading">
      <el-table-column prop="analysis_type" label="分析类型" width="120" />
      <el-table-column prop="provider" label="Provider" width="100" />
      <el-table-column prop="model" label="模型" width="120" />
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'completed' ? 'success' : 'warning'">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="时间" width="180" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button size="small" @click="viewResult(row)">查看</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showResult" title="分析结果" width="600px">
      <pre style="max-height: 400px; overflow: auto; white-space: pre-wrap">{{ resultText }}</pre>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import api from "../utils/api";

const analyses = ref([]);
const loading = ref(false);
const showResult = ref(false);
const resultText = ref("");

async function fetchAnalyses() {
  loading.value = true;
  try {
    const { data } = await api.get("/ai/analyses");
    analyses.value = data?.data?.items || [];
  } finally {
    loading.value = false;
  }
}

function viewResult(row: any) {
  resultText.value = JSON.stringify(row.result, null, 2);
  showResult.value = true;
}

onMounted(fetchAnalyses);
</script>
