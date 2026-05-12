<template>
  <div>
    <h2>基准测试</h2>
    <el-row :gutter="12" style="margin-bottom: 16px">
      <el-col :span="5">
        <el-select v-model="filters.platform" placeholder="平台" clearable style="width:100%">
          <el-option label="小红书" value="xhs" />
          <el-option label="抖音" value="douyin" />
          <el-option label="淘宝" value="taobao" />
          <el-option label="京东" value="jd" />
          <el-option label="拼多多" value="pdd" />
        </el-select>
      </el-col>
      <el-col :span="5">
        <el-select v-model="filters.category" placeholder="类目" clearable filterable style="width:100%">
          <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
        </el-select>
      </el-col>
      <el-col :span="5">
        <el-select v-model="filters.metric" placeholder="对比指标" style="width:100%">
          <el-option label="价格分布" value="price" />
          <el-option label="销量分布" value="sales" />
          <el-option label="评分分布" value="rating" />
          <el-option label="评论数分布" value="review_count" />
        </el-select>
      </el-col>
      <el-col :span="3"><el-button type="primary" @click="fetchBenchmark">查询</el-button></el-col>
      <el-col :span="3"><el-button @click="exportBenchmark">导出</el-button></el-col>
    </el-row>

    <el-row :gutter="16" style="margin-bottom: 24px">
      <el-col :span="6">
        <el-card shadow="hover"><el-statistic title="类目均价" :value="store.summary.avgPrice" :precision="2" prefix="¥" /></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><el-statistic title="类目均销量" :value="store.summary.avgSales" /></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><el-statistic title="类目均评分" :value="store.summary.avgRating" :precision="1" /></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><el-statistic title="商品样本数" :value="store.summary.sampleCount" /></el-card>
      </el-col>
    </el-row>

    <h3>分布图</h3>
    <el-card shadow="hover" style="margin-bottom:24px">
      <div class="bar-chart">
        <div v-for="(bar, idx) in store.distribution" :key="idx" class="bar-row">
          <span class="bar-label">{{ bar.label }}</span>
          <div class="bar-track">
            <div class="bar-fill" :style="{ width: bar.percentage + '%', background: barColor(idx) }"></div>
          </div>
          <span class="bar-value">{{ bar.count }} ({{ bar.percentage }}%)</span>
        </div>
      </div>
      <div v-if="store.distribution.length === 0" style="text-align:center;color:#909399;padding:32px">选择平台和类目后查询以查看分布</div>
    </el-card>

    <h3>基准数据明细</h3>
    <el-table :data="store.benchmarks" stripe v-loading="store.loading" row-key="id">
      <el-table-column prop="category" label="类目" width="140" />
      <el-table-column prop="platform" label="平台" width="100">
        <template #default="{ row }">{{ platformLabel(row.platform) }}</template>
      </el-table-column>
      <el-table-column prop="sample_count" label="样本数" width="100" />
      <el-table-column prop="avg_price" label="均价" width="120">
        <template #default="{ row }">¥{{ row.avg_price?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="median_price" label="中位价" width="120">
        <template #default="{ row }">¥{{ row.median_price?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="avg_sales" label="均销量" width="100" />
      <el-table-column prop="avg_rating" label="均评分" width="100">
        <template #default="{ row }">{{ row.avg_rating?.toFixed(1) }}</template>
      </el-table-column>
      <el-table-column prop="p25_price" label="P25价格" width="120">
        <template #default="{ row }">¥{{ row.p25_price?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="p75_price" label="P75价格" width="120">
        <template #default="{ row }">¥{{ row.p75_price?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="updated_at" label="更新时间" width="180" />
    </el-table>

    <el-pagination
      v-model:current-page="page"
      :page-size="20"
      :total="store.total"
      layout="prev, pager, next"
      style="margin-top:16px;justify-content:flex-end"
      @current-change="fetchBenchmark"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { useBenchmarkStore } from "../stores/benchmark";

const store = useBenchmarkStore();

const page = ref(1);

const categories = [
  "女装", "男装", "美妆", "食品", "母婴", "家居", "数码", "运动", "鞋靴", "箱包",
  "饰品", "图书", "家电", "宠物", "汽车用品",
];

const filters = reactive({
  platform: "" as string,
  category: "" as string,
  metric: "price" as string,
});

function platformLabel(p: string): string {
  const map: Record<string, string> = { xhs: "小红书", douyin: "抖音", taobao: "淘宝", jd: "京东", pdd: "拼多多" };
  return map[p] || p;
}

function barColor(idx: number): string {
  const colors = ["#409eff", "#67c23a", "#e6a23c", "#f56c6c", "#909399", "#9b59b6", "#1abc9c", "#e74c3c"];
  return colors[idx % colors.length];
}

async function fetchBenchmark() {
  try {
    await store.fetchBenchmarks(page.value, 20, filters.platform || undefined, filters.category || undefined);

    if (filters.platform && filters.category) {
      await store.fetchDistribution(filters.platform, filters.category, filters.metric);
    } else {
      store.distribution.length = 0;
    }
  } catch { ElMessage.error("获取基准数据失败"); }
}

async function exportBenchmark() {
  try {
    const params: Record<string, unknown> = {};
    if (filters.platform) params.platform = filters.platform;
    if (filters.category) params.category = filters.category;
    const blob = await store.exportBenchmark(params);
    const url = window.URL.createObjectURL(new Blob([blob as BlobPart]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "benchmarks.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch { ElMessage.error("导出失败"); }
}

onMounted(fetchBenchmark);
</script>

<style scoped>
.bar-chart {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.bar-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.bar-label {
  width: 120px;
  font-size: 13px;
  color: #606266;
  text-align: right;
  flex-shrink: 0;
}
.bar-track {
  flex: 1;
  height: 20px;
  background: #f0f2f5;
  border-radius: 4px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}
.bar-value {
  width: 100px;
  font-size: 13px;
  color: #909399;
  flex-shrink: 0;
}
</style>
