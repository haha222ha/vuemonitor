<template>
  <div>
    <div style="display:flex;justify-content:space-between;margin-bottom:16px">
      <h2>代理池管理</h2>
      <el-button type="primary" @click="showAdd = true">添加代理</el-button>
    </div>
    <el-table :data="store.proxies" stripe v-loading="store.loading">
      <el-table-column prop="ip" label="IP" />
      <el-table-column prop="port" label="端口" width="80" />
      <el-table-column prop="protocol" label="协议" width="80" />
      <el-table-column prop="health_score" label="健康分" width="100">
        <template #default="{ row }"><el-progress :percentage="row.health_score" :stroke-width="6" :color="row.health_score > 60 ? '#67c23a' : '#f56c6c'" /></template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }"><el-tag :type="row.status === 'available' ? 'success' : 'danger'">{{ row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="fail_count" label="失败次数" width="100" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }"><el-button size="small" type="danger" @click="deleteProxy(row.id)">删除</el-button></template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showAdd" title="添加代理" width="400px">
      <el-form :model="form" :rules="addRules" ref="formRef" label-width="60px">
        <el-form-item label="IP" prop="ip"><el-input v-model="form.ip" placeholder="例如: 1.2.3.4" /></el-form-item>
        <el-form-item label="端口" prop="port"><el-input-number v-model="form.port" :min="1" :max="65535" /></el-form-item>
        <el-form-item label="协议" prop="protocol"><el-select v-model="form.protocol"><el-option label="HTTP" value="http" /><el-option label="HTTPS" value="https" /><el-option label="SOCKS5" value="socks5" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="showAdd = false">取消</el-button><el-button type="primary" @click="addProxy">添加</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { useProxiesStore } from "../stores/proxies";

const store = useProxiesStore();

const showAdd = ref(false);
const formRef = ref<FormInstance>();
const form = reactive({ ip: "", port: 8080, protocol: "http" });

const addRules: FormRules = {
  ip: [
    { required: true, message: "请输入IP地址", trigger: "blur" },
    { pattern: /^(\d{1,3}\.){3}\d{1,3}$/, message: "请输入有效的IP地址", trigger: "blur" },
  ],
  port: [{ required: true, message: "请输入端口号", trigger: "blur" }],
  protocol: [{ required: true, message: "请选择协议", trigger: "change" }],
};

async function fetchProxies() {
  try {
    await store.fetchProxies();
  } catch {
    ElMessage.error("获取代理列表失败");
  }
}

async function addProxy() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;

  try {
    await store.addProxy({ ip: form.ip, port: form.port, protocol: form.protocol });
    ElMessage.success("添加成功");
    showAdd.value = false;
    form.ip = "";
    form.port = 8080;
    form.protocol = "http";
    fetchProxies();
  } catch {
    ElMessage.error("添加失败");
  }
}

async function deleteProxy(id: string) {
  try {
    await store.deleteProxy(Number(id));
    ElMessage.success("删除成功");
    fetchProxies();
  } catch {
    ElMessage.error("删除失败");
  }
}

onMounted(fetchProxies);
</script>
