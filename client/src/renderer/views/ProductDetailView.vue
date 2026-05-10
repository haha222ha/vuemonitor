<template>
  <div>
    <el-page-header @back="$router.back()" :content="productStore.currentProduct?.product_name || '商品详情'" />

    <div v-loading="productStore.loading" style="margin-top: 16px">
      <el-descriptions :column="3" border v-if="productStore.currentProduct">
        <el-descriptions-item label="平台">小红书</el-descriptions-item>
        <el-descriptions-item label="商品ID">{{ productStore.currentProduct.platform_product_id }}</el-descriptions-item>
        <el-descriptions-item label="作者">{{ productStore.currentProduct.shop_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="最新采集">{{ productStore.currentProduct.last_collected_at ? formatDate(productStore.currentProduct.last_collected_at) : '未采集' }}</el-descriptions-item>
        <el-descriptions-item label="商品链接">
          <el-link v-if="productStore.currentProduct.product_url" :href="productStore.currentProduct.product_url" target="_blank" type="primary">查看</el-link>
          <span v-else>-</span>
        </el-descriptions-item>
      </el-descriptions>
      <el-empty v-else-if="!productStore.loading" description="商品信息加载失败" />
    </div>

    <div style="margin-top: 24px; display: flex; gap: 12px; flex-wrap: wrap">
      <el-button type="primary" @click="collectNow">立即采集</el-button>
      <el-button v-permission="'gate:ai:basic_analysis'" @click="runAnalysis('basic_analysis')" :loading="aiStore.isAnalyzing">基础分析</el-button>
      <el-button v-permission="'gate:ai:trend_score'" @click="runAnalysis('trend_score')" :loading="aiStore.isAnalyzing">趋势评分</el-button>
      <el-button v-permission="'gate:ai:prediction'" @click="runAnalysis('prediction')" :loading="aiStore.isAnalyzing">爆品预测</el-button>
      <el-button v-permission="'gate:ai:risk_warning'" @click="runAnalysis('risk_warning')" :loading="aiStore.isAnalyzing">风险预警</el-button>
      <el-button v-permission="'gate:monitor:export'" @click="exportData">导出数据</el-button>
    </div>

    <div v-if="aiStore.currentAnalysis" style="margin-top: 20px">
      <el-card>
        <template #header><span>AI分析结果</span></template>
        <div style="white-space: pre-wrap; line-height: 1.8">{{ formatAIResult(aiStore.currentAnalysis) }}</div>
      </el-card>
    </div>

    <h3 style="margin-top: 24px">数据趋势</h3>
    <div style="background: #fff; padding: 16px; border-radius: 8px; border: 1px solid #ebeef5">
      <MultiMetricChart
        v-if="chartData.length > 0"
        :data="chartData"
        :metrics="selectedMetrics"
        :height="350"
      />
      <el-empty v-else description="暂无趋势数据，请先采集" />
    </div>

    <div style="margin-top: 12px; display: flex; gap: 12px; align-items: center">
      <span style="font-size: 13px; color: #909399">显示指标：</span>
      <el-checkbox v-model="metricVisible.price" @change="updateMetrics">价格</el-checkbox>
      <el-checkbox v-model="metricVisible.sales" @change="updateMetrics">销量</el-checkbox>
      <el-checkbox v-model="metricVisible.rating" @change="updateMetrics">评分</el-checkbox>
      <el-checkbox v-model="metricVisible.review_count" @change="updateMetrics">评论数</el-checkbox>
      <el-checkbox v-model="metricVisible.favorite_count" @change="updateMetrics">收藏数</el-checkbox>
    </div>

    <h3 style="margin-top: 24px">历史特征</h3>
    <el-table :data="productStore.features" stripe v-loading="productStore.loading" max-height="400">
      <el-table-column prop="collected_at" label="采集时间" width="180">
        <template #default="{ row }">{{ formatDate(row.collected_at) }}</template>
      </el-table-column>
      <el-table-column prop="price" label="价格" width="100">
        <template #default="{ row }">{{ row.price != null ? `¥${row.price}` : '-' }}</template>
      </el-table-column>
      <el-table-column prop="sales_count" label="销量" width="100" />
      <el-table-column prop="rating" label="评分" width="80" />
      <el-table-column prop="review_count" label="评论" width="80" />
      <el-table-column prop="favorite_count" label="收藏" width="80" />
      <el-table-column prop="source" label="来源" width="80" />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from "vue";
import { useRoute } from "vue-router";
import { useProductStore } from "../stores/product";
import { useCollectStore } from "../stores/collect";
import { useAIStore } from "../stores/ai";
import { usePermissionStore } from "../stores/permission";
import { ElMessage } from "element-plus";
import MultiMetricChart from "../components/MultiMetricChart.vue";
import type { MultiMetricDataPoint } from "../components/MultiMetricChart.vue";

const route = useRoute();
const productStore = useProductStore();
const collectStore = useCollectStore();
const aiStore = useAIStore();
const permissionStore = usePermissionStore();

const metricVisible = reactive({
  price: true,
  sales: true,
  rating: false,
  review_count: false,
  favorite_count: false,
});

const selectedMetrics = computed(() => {
  return Object.entries(metricVisible)
    .filter(([, visible]) => visible)
    .map(([key]) => key);
});

function updateMetrics() {}

const chartData = computed<MultiMetricDataPoint[]>(() => {
  return productStore.features
    .slice()
    .reverse()
    .map((f) => ({
      date: f.collected_at ? formatDate(f.collected_at) : "",
      price: f.price,
      sales: f.sales_count,
      rating: f.rating,
      review_count: f.review_count,
      favorite_count: f.favorite_count,
    }));
});

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function formatAIResult(result: Record<string, unknown>): string {
  if (typeof result === "string") return result;
  if (result.result) return String(result.result);
  if (result.analysis) return String(result.analysis);
  return JSON.stringify(result, null, 2);
}

async function collectNow() {
  const p = productStore.currentProduct;
  if (!p) return;
  await collectStore.startCollect([
    { targetId: p.platform_product_id, targetType: "note" },
  ]);
  ElMessage.success("采集任务已提交");
}

async function runAnalysis(type: string) {
  const productId = route.params.id as string;
  const result = await aiStore.analyzeProduct(productId, type);
  if (result) {
    ElMessage.success("分析完成");
  }
}

async function exportData() {
  try {
    const productId = route.params.id as string;
    const features = productStore.features;
    const csvHeader = "采集时间,价格,销量,评分,评论数,收藏数,来源\n";
    const csvRows = features
      .map((f) => `${f.collected_at},${f.price ?? ""},${f.sales_count ?? ""},${f.rating ?? ""},${f.review_count ?? ""},${f.favorite_count ?? ""},${f.source}`)
      .join("\n");
    const blob = new Blob([csvHeader + csvRows], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `product_${productId}_features.csv`;
    a.click();
    URL.revokeObjectURL(url);
    ElMessage.success("导出成功");
  } catch {
    ElMessage.error("导出失败");
  }
}

onMounted(() => {
  const productId = route.params.id as string;
  productStore.fetchProductDetail(productId);
  productStore.fetchFeatures(productId);
  permissionStore.fetchPermissions();
});
</script>
