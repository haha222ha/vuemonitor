<template>
  <div class="monitor-list">
    <div class="page-toolbar">
      <div class="toolbar-left">
        <el-input v-model="search" placeholder="搜索商品..." style="width: 240px" clearable />
        <el-select v-model="platformFilter" placeholder="平台" clearable style="width: 120px">
          <el-option label="小红书" value="xhs" />
          <el-option label="淘宝" value="taobao" />
          <el-option label="京东" value="jd" />
          <el-option label="拼多多" value="pdd" />
          <el-option label="抖音" value="douyin" />
        </el-select>
      </div>
      <el-button type="primary" @click="showAddDialog = true">+ 添加监控</el-button>
    </div>

    <el-table :data="filteredProducts" stripe v-loading="loading" empty-text="暂无监控商品，点击右上角添加">
      <el-table-column prop="name" label="商品名称" min-width="200" />
      <el-table-column prop="platform" label="平台" width="90">
        <template #default="{ row }">
          <el-tag size="small">{{ platformLabel(row.platform) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="price" label="价格" width="100" />
      <el-table-column label="热度变化" width="110">
        <template #default="{ row }">
          <span :class="row.trend > 0 ? 'trend-up' : row.trend < 0 ? 'trend-down' : ''">
            {{ row.trend > 0 ? '↑' : row.trend < 0 ? '↓' : '—' }}{{ Math.abs(row.trend || 0) }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column label="AI评分" width="130">
        <template #default="{ row }">
          <span v-if="auth.userPlan === 'free'" class="ai-locked">升级Pro查看</span>
          <el-rate v-else-if="auth.userPlan === 'pro'" :model-value="Math.round((row.aiScore || 0) / 20)" disabled size="small" />
          <span v-else class="ai-premium">{{ row.aiScore || '—' }}分</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button size="small" @click="viewDetail(row)">详情</el-button>
          <el-button size="small" type="danger" @click="confirmDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showAddDialog" title="添加商品监控" width="500px">
      <el-form :model="addForm" label-width="80px">
        <el-form-item label="商品URL">
          <el-input v-model="addForm.url" placeholder="粘贴商品页面链接" />
        </el-form-item>
        <el-form-item label="平台">
          <el-select v-model="addForm.platform" style="width: 100%">
            <el-option label="小红书" value="xhs" />
            <el-option label="淘宝" value="taobao" />
            <el-option label="京东" value="jd" />
            <el-option label="拼多多" value="pdd" />
            <el-option label="抖音" value="douyin" />
          </el-select>
        </el-form-item>
        <el-form-item label="商品名称">
          <el-input v-model="addForm.name" placeholder="可选，自动从页面提取" />
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

const router = useRouter();
const auth = useAuthStore();
const loading = ref(false);
const adding = ref(false);
const products = ref<any[]>([]);
const search = ref("");
const platformFilter = ref("");
const showAddDialog = ref(false);

const addForm = reactive({ url: "", platform: "xhs", name: "" });

const filteredProducts = computed(() => {
  return products.value.filter((p) => {
    const matchSearch = !search.value || p.name?.includes(search.value);
    const matchPlatform = !platformFilter.value || p.platform === platformFilter.value;
    return matchSearch && matchPlatform;
  });
});

function platformLabel(p: string) {
  const map: Record<string, string> = { xhs: "小红书", taobao: "淘宝", jd: "京东", pdd: "拼多多", douyin: "抖音" };
  return map[p] || p;
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
  if (!addForm.url) {
    ElMessage.warning("请输入商品URL");
    return;
  }
  adding.value = true;
  try {
    await api.post("/products", {
      url: addForm.url,
      platform: addForm.platform,
      name: addForm.name || undefined,
    });
    ElMessage.success("已添加监控");
    showAddDialog.value = false;
    addForm.url = "";
    addForm.name = "";
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

.trend-up { color: #22c55e; font-weight: 600; }
.trend-down { color: #ef4444; font-weight: 600; }
.ai-locked { color: #4a4a5a; font-size: 12px; }
.ai-premium { color: #fbbf24; font-weight: 600; }
</style>
