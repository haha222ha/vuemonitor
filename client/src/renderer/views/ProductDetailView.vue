<template>
  <div>
    <el-page-header @back="$router.back()" :content="product?.product_name || '商品详情'" />
    <div v-loading="loading" style="margin-top: 16px">
      <el-descriptions :column="2" border v-if="product">
        <el-descriptions-item label="平台">{{ product.platform }}</el-descriptions-item>
        <el-descriptions-item label="商品ID">{{ product.platform_product_id }}</el-descriptions-item>
        <el-descriptions-item label="店铺">{{ product.shop_name || "-" }}</el-descriptions-item>
        <el-descriptions-item label="最新价格">{{ product.latest_feature?.price ?? "-" }}</el-descriptions-item>
        <el-descriptions-item label="销量">{{ product.latest_feature?.sales_count ?? "-" }}</el-descriptions-item>
        <el-descriptions-item label="评分">{{ product.latest_feature?.rating ?? "-" }}</el-descriptions-item>
      </el-descriptions>
      <el-empty v-else-if="!loading" description="商品信息加载失败" />
    </div>

    <h3 style="margin-top: 24px">AI分析</h3>
    <el-button type="primary" @click="runAnalysis('basic_analysis')" :loading="analysisLoading">基础分析</el-button>
    <el-button @click="runAnalysis('trend_score')" :loading="analysisLoading">趋势评分</el-button>
    <el-button @click="runAnalysis('prediction')" :loading="analysisLoading">爆品预测</el-button>

    <h3 style="margin-top: 24px">历史特征</h3>
    <el-table :data="features" stripe v-loading="featLoading">
      <el-table-column prop="collected_at" label="采集时间" width="180" />
      <el-table-column prop="price" label="价格" width="100" />
      <el-table-column prop="sales_count" label="销量" width="100" />
      <el-table-column prop="rating" label="评分" width="80" />
      <el-table-column prop="source" label="来源" width="80" />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import api from "../utils/api";
import { ElMessage } from "element-plus";

const route = useRoute();
const product = ref<any>(null);
const features = ref([]);
const loading = ref(false);
const featLoading = ref(false);
const analysisLoading = ref(false);

async function fetchProduct() {
  loading.value = true;
  try {
    const { data } = await api.get(`/products/${route.params.id}`);
    product.value = data?.data;
  } catch {
    ElMessage.error("获取商品详情失败");
  } finally {
    loading.value = false;
  }
}

async function fetchFeatures() {
  featLoading.value = true;
  try {
    const { data } = await api.get(`/products/${route.params.id}/features`);
    features.value = data?.data?.items || [];
  } catch {
    ElMessage.error("获取历史特征失败");
  } finally {
    featLoading.value = false;
  }
}

async function runAnalysis(type: string) {
  analysisLoading.value = true;
  try {
    await api.post("/ai/analyze", {
      product_id: route.params.id,
      analysis_type: type,
    });
    ElMessage.success("分析完成");
  } catch {
    ElMessage.error("分析失败，请检查套餐权限");
  } finally {
    analysisLoading.value = false;
  }
}

onMounted(() => {
  fetchProduct();
  fetchFeatures();
});
</script>
