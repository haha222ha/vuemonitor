<template>
  <div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 16px">
      <h2>商品监控</h2>
      <el-button type="primary" @click="showAdd = true">添加商品</el-button>
    </div>
    <el-table :data="products" v-loading="loading" stripe>
      <el-table-column prop="platform" label="平台" width="100" />
      <el-table-column prop="product_name" label="商品名称" min-width="200" />
      <el-table-column prop="shop_name" label="店铺" width="150" />
      <el-table-column label="最新价格" width="120">
        <template #default="{ row }">{{ row.latest_feature?.price ?? "-" }}</template>
      </el-table-column>
      <el-table-column label="销量" width="100">
        <template #default="{ row }">{{ row.latest_feature?.sales_count ?? "-" }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" @click="$router.push(`/products/${row.id}`)">详情</el-button>
          <el-button size="small" type="danger" @click="confirmDelete(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showAdd" title="添加监控商品" width="500px">
      <el-form :model="addForm" :rules="addRules" ref="addFormRef" label-width="80px">
        <el-form-item label="平台" prop="platform">
          <el-select v-model="addForm.platform">
            <el-option label="小红书" value="xhs" />
            <el-option label="抖音" value="douyin" />
            <el-option label="淘宝" value="taobao" />
            <el-option label="京东" value="jd" />
            <el-option label="拼多多" value="pdd" />
          </el-select>
        </el-form-item>
        <el-form-item label="商品ID" prop="platform_product_id">
          <el-input v-model="addForm.platform_product_id" />
        </el-form-item>
        <el-form-item label="商品名称" prop="product_name">
          <el-input v-model="addForm.product_name" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" @click="addProduct">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import api from "../utils/api";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";

const products = ref([]);
const loading = ref(false);
const showAdd = ref(false);
const addFormRef = ref<FormInstance>();
const addForm = ref({ platform: "xhs", platform_product_id: "", product_name: "" });

const addRules: FormRules = {
  platform: [{ required: true, message: "请选择平台", trigger: "change" }],
  platform_product_id: [{ required: true, message: "请输入商品ID", trigger: "blur" }],
  product_name: [{ required: true, message: "请输入商品名称", trigger: "blur" }],
};

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
  const valid = await addFormRef.value?.validate().catch(() => false);
  if (!valid) return;

  try {
    await api.post("/products", addForm.value);
    ElMessage.success("添加成功");
    showAdd.value = false;
    addForm.value = { platform: "xhs", platform_product_id: "", product_name: "" };
    fetchProducts();
  } catch {
    ElMessage.error("添加失败");
  }
}

async function confirmDelete(id: string) {
  try {
    await ElMessageBox.confirm("确定要删除该商品吗？删除后不可恢复。", "确认删除", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
    });
    await deleteProduct(id);
  } catch {}
}

async function deleteProduct(id: string) {
  try {
    await api.delete(`/products/${id}`);
    ElMessage.success("删除成功");
    fetchProducts();
  } catch {
    ElMessage.error("删除失败");
  }
}

onMounted(fetchProducts);
</script>
