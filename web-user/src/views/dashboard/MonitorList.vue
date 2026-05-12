<template>
  <div class="monitor-list">
    <div class="page-toolbar">
      <div class="toolbar-left">
        <el-input v-model="search" placeholder="搜索商品..." style="width: 240px" clearable />
        <el-select v-model="platformFilter" placeholder="全部平台" clearable style="width: 120px">
          <el-option label="小红书" value="xhs" />
          <el-option label="淘宝" value="taobao" />
          <el-option label="京东" value="jd" />
          <el-option label="拼多多" value="pdd" />
          <el-option label="抖音" value="douyin" />
        </el-select>
      </div>
      <el-button type="primary" @click="showAddDialog = true">+ 添加监控</el-button>
      <el-dropdown style="margin-left: 8px" @command="handleExport">
        <el-button>导出数据<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="csv">导出 CSV</el-dropdown-item>
            <el-dropdown-item command="json">导出 JSON</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <div v-if="loading" style="text-align: center; padding: 40px;">
      <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      <p style="color: #6a6a7a; margin-top: 8px;">加载中...</p>
    </div>

    <div v-else-if="filteredProducts.length === 0" class="empty-state">
      <div class="empty-icon">📊</div>
      <p>暂无监控商品</p>
      <el-button type="primary" @click="showAddDialog = true">添加第一个商品</el-button>
    </div>

    <div v-else class="product-grid">
      <div v-for="p in filteredProducts" :key="p.id" class="product-card" @click="viewDetail(p)">
        <div class="card-image">
          <img v-if="p.image_url" :src="p.image_url" :alt="p.product_name" />
          <div v-else class="image-placeholder">{{ platformEmoji(p.platform) }}</div>
          <el-tag class="card-platform" size="small">{{ platformLabel(p.platform) }}</el-tag>
        </div>
        <div class="card-body">
          <h4 class="card-title">{{ p.product_name }}</h4>
          <p v-if="p.shop_name" class="card-shop">{{ p.shop_name }}</p>
          <div class="card-stats">
            <div v-if="p.latest_feature?.price" class="stat-item">
              <span class="stat-label">价格</span>
              <span class="stat-value price">¥{{ p.latest_feature.price }}</span>
            </div>
            <div v-if="p.latest_feature?.sales_count != null" class="stat-item">
              <span class="stat-label">销量</span>
              <span class="stat-value">{{ formatNumber(p.latest_feature.sales_count) }}</span>
            </div>
            <div v-if="p.latest_feature?.rating" class="stat-item">
              <span class="stat-label">评分</span>
              <span class="stat-value">{{ p.latest_feature.rating }}</span>
            </div>
          </div>
          <div class="card-footer">
            <span :class="['trend-badge', p.trend > 0 ? 'trend-up' : p.trend < 0 ? 'trend-down' : 'trend-flat']">
              {{ p.trend > 0 ? '↑' : p.trend < 0 ? '↓' : '—' }}{{ Math.abs(p.trend || 0) }}%
            </span>
            <span class="last-collect">
              {{ p.last_collected_at ? timeAgo(p.last_collected_at) : '未采集' }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="showAddDialog" title="添加商品监控" width="520px" :close-on-click-modal="false">
      <el-form :model="addForm" label-width="90px">
        <el-form-item label="商品链接">
          <el-input v-model="addForm.url" placeholder="粘贴小红书/淘宝/京东/拼多多/抖音商品链接" @input="onUrlInput" />
        </el-form-item>
        <el-collapse-transition>
          <div v-if="!addForm.urlParsed">
            <el-form-item label="平台">
              <el-select v-model="addForm.platform" style="width: 100%">
                <el-option label="小红书" value="xhs" />
                <el-option label="淘宝" value="taobao" />
                <el-option label="京东" value="jd" />
                <el-option label="拼多多" value="pdd" />
                <el-option label="抖音" value="douyin" />
              </el-select>
            </el-form-item>
            <el-form-item label="商品ID">
              <el-input v-model="addForm.platform_product_id" placeholder="输入平台商品ID" />
            </el-form-item>
          </div>
          <div v-else class="parse-result">
            <el-tag type="success" size="small">已识别</el-tag>
            <span>平台：{{ platformLabel(addForm.platform) }}，商品ID：{{ addForm.platform_product_id }}</span>
          </div>
        </el-collapse-transition>
        <el-form-item label="商品名称">
          <el-input v-model="addForm.name" placeholder="可选，自动生成" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" :loading="adding" @click="addProduct">添加监控</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../../stores/auth";
import api from "../../utils/api";
import { ElMessage, ElMessageBox } from "element-plus";
import { Loading, ArrowDown } from "@element-plus/icons-vue";

const router = useRouter();
const auth = useAuthStore();
const loading = ref(false);
const adding = ref(false);
const products = ref<any[]>([]);
const search = ref("");
const platformFilter = ref("");
const showAddDialog = ref(false);

const addForm = reactive({
  url: "",
  platform: "xhs",
  platform_product_id: "",
  name: "",
  urlParsed: false,
});

const filteredProducts = computed(() => {
  return products.value.filter((p) => {
    const matchSearch = !search.value || p.product_name?.includes(search.value) || p.shop_name?.includes(search.value);
    const matchPlatform = !platformFilter.value || p.platform === platformFilter.value;
    return matchSearch && matchPlatform;
  });
});

function platformLabel(p: string) {
  const map: Record<string, string> = { xhs: "小红书", taobao: "淘宝", jd: "京东", pdd: "拼多多", douyin: "抖音" };
  return map[p] || p;
}

function platformEmoji(p: string) {
  const map: Record<string, string> = { xhs: "📕", taobao: "🛒", jd: "🏪", pdd: "🛍️", douyin: "🎵" };
  return map[p] || "📦";
}

function formatNumber(n: number) {
  if (n >= 10000) return (n / 10000).toFixed(1) + "万";
  if (n >= 1000) return (n / 1000).toFixed(1) + "k";
  return String(n);
}

function timeAgo(dateStr: string) {
  const now = new Date();
  const d = new Date(dateStr);
  const diff = (now.getTime() - d.getTime()) / 1000;
  if (diff < 60) return "刚刚";
  if (diff < 3600) return Math.floor(diff / 60) + "分钟前";
  if (diff < 86400) return Math.floor(diff / 3600) + "小时前";
  return Math.floor(diff / 86400) + "天前";
}

function onUrlInput() {
  addForm.urlParsed = false;
  const url = addForm.url.trim();
  if (!url) return;

  const xhsMatch = url.match(/xiaohongshu\.com\/(?:explore|discovery\/item)\/([a-f0-9]{24})/i) ||
                    url.match(/xhslink\.com\/(\w+)/i);
  if (xhsMatch) {
    addForm.platform = "xhs";
    addForm.platform_product_id = xhsMatch[1];
    addForm.urlParsed = true;
    return;
  }

  const taobaoMatch = url.match(/(?:taobao|tmall)\.com\/item\.htm.*[?&]id=(\d+)/i) ||
                       url.match(/m\.taobao\.com.*[?&]id=(\d+)/i);
  if (taobaoMatch) {
    addForm.platform = "taobao";
    addForm.platform_product_id = taobaoMatch[1];
    addForm.urlParsed = true;
    return;
  }

  const jdMatch = url.match(/item\.(?:m\.)?jd\.com\/(?:product\/)?(\d+)/i);
  if (jdMatch) {
    addForm.platform = "jd";
    addForm.platform_product_id = jdMatch[1];
    addForm.urlParsed = true;
    return;
  }

  const pddMatch = url.match(/yangkeduo\.com\/goods\.html\?.*goods_id=(\d+)/i) ||
                    url.match(/pinduoduo\.com\/goods\.html\?.*goods_id=(\d+)/i);
  if (pddMatch) {
    addForm.platform = "pdd";
    addForm.platform_product_id = pddMatch[1];
    addForm.urlParsed = true;
    return;
  }

  const douyinMatch = url.match(/(?:ies)?douyin\.com\/(?:share\/)?video\/(\d+)/i);
  if (douyinMatch) {
    addForm.platform = "douyin";
    addForm.platform_product_id = douyinMatch[1];
    addForm.urlParsed = true;
    return;
  }
}

async function fetchProducts() {
  loading.value = true;
  try {
    const { data } = await api.get("/products");
    products.value = data?.data?.items || [];
  } catch {
    ElMessage.error("获取商品列表失败");
  } finally {
    loading.value = false;
  }
}

async function addProduct() {
  const payload: any = {};
  if (addForm.url) {
    payload.url = addForm.url;
  }
  if (addForm.platform) payload.platform = addForm.platform;
  if (addForm.platform_product_id) payload.platform_product_id = addForm.platform_product_id;
  if (addForm.name) payload.product_name = addForm.name;

  if (!payload.url && (!payload.platform || !payload.platform_product_id)) {
    ElMessage.warning("请输入商品链接或手动选择平台和商品ID");
    return;
  }

  adding.value = true;
  try {
    await api.post("/products", payload);
    ElMessage.success("已添加监控");
    showAddDialog.value = false;
    addForm.url = "";
    addForm.name = "";
    addForm.platform_product_id = "";
    addForm.urlParsed = false;
    fetchProducts();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || "添加失败");
  } finally {
    adding.value = false;
  }
}

function viewDetail(row: any) {
  router.push(`/dashboard/monitor/${row.id}`);
}

async function confirmDelete(row: any) {
  try {
    await ElMessageBox.confirm("确定删除该商品监控？", "确认", { type: "warning" });
    await api.delete(`/products/${row.id}`);
    ElMessage.success("已删除");
    fetchProducts();
  } catch {}
}

async function handleExport(format: string) {
  try {
    const resp = await api.get(`/products/export/${format}`, {
      params: { platform: platformFilter.value || undefined },
      responseType: format === "csv" ? "blob" : "json",
    });
    if (format === "csv") {
      const blob = new Blob([resp.data], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `products_export_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } else {
      const blob = new Blob([JSON.stringify(resp.data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `products_export_${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    }
    ElMessage.success("导出成功");
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || "导出失败");
  }
}

onMounted(fetchProducts);
</script>

<style scoped>
.monitor-list {
  padding: 4px;
}

.page-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.toolbar-left {
  display: flex;
  gap: 12px;
}

.empty-state {
  text-align: center;
  padding: 60px 0;
  color: #6a6a7a;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.product-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
}

.product-card:hover {
  border-color: rgba(99, 102, 241, 0.3);
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.card-image {
  height: 140px;
  background: rgba(255, 255, 255, 0.02);
  position: relative;
  overflow: hidden;
}

.card-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(244, 114, 182, 0.08));
}

.card-platform {
  position: absolute;
  top: 8px;
  left: 8px;
}

.card-body {
  padding: 14px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #e0e0e6;
  margin: 0 0 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-shop {
  font-size: 12px;
  color: #6a6a7a;
  margin: 0 0 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-stats {
  display: flex;
  gap: 12px;
  margin-bottom: 10px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font-size: 11px;
  color: #4a4a5a;
}

.stat-value {
  font-size: 14px;
  font-weight: 600;
  color: #e0e0e6;
}

.stat-value.price {
  color: #f472b6;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
}

.trend-badge {
  font-size: 13px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}

.trend-up {
  color: #22c55e;
  background: rgba(34, 197, 94, 0.1);
}

.trend-down {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.trend-flat {
  color: #6a6a7a;
  background: rgba(255, 255, 255, 0.03);
}

.last-collect {
  font-size: 12px;
  color: #4a4a5a;
}

.parse-result {
  padding: 8px 12px;
  background: rgba(34, 197, 94, 0.06);
  border: 1px solid rgba(34, 197, 94, 0.15);
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
  color: #86efac;
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
