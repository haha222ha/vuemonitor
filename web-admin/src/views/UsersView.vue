<template>
  <div>
    <h2>用户管理</h2>
    <el-table :data="store.users" stripe v-loading="store.loading">
      <el-table-column prop="email" label="邮箱" />
      <el-table-column prop="nickname" label="昵称" width="120" />
      <el-table-column prop="plan" label="套餐" width="100">
        <template #default="{ row }"><el-tag>{{ row.plan }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'danger'">{{ row.is_active ? "正常" : "禁用" }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="created_at" label="注册时间" width="180" />
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" @click="openChangePlan(row)">改套餐</el-button>
          <el-button size="small" :type="row.is_active ? 'danger' : 'success'" @click="toggleActive(row)">{{ row.is_active ? "禁用" : "启用" }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showChangePlan" title="修改套餐" width="400px">
      <el-form label-width="60px">
        <el-form-item label="用户">{{ currentUser?.email }}</el-form-item>
        <el-form-item label="套餐">
          <el-select v-model="newPlan">
            <el-option label="Free" value="free" />
            <el-option label="Pro" value="pro" />
            <el-option label="Premium" value="premium" />
            <el-option label="Enterprise" value="enterprise" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showChangePlan = false">取消</el-button>
        <el-button type="primary" @click="submitChangePlan">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { useUsersStore } from "../stores/users";

const store = useUsersStore();

const showChangePlan = ref(false);
const currentUser = ref<any>(null);
const newPlan = ref("free");

async function fetchUsers() {
  try {
    await store.fetchUsers();
  } catch {
    ElMessage.error("获取用户列表失败");
  }
}

async function toggleActive(user: any) {
  try {
    await store.updateUser(user.id, { is_active: !user.is_active } as any);
    ElMessage.success("操作成功");
    fetchUsers();
  } catch {
    ElMessage.error("操作失败");
  }
}

function openChangePlan(user: any) {
  currentUser.value = user;
  newPlan.value = user.plan;
  showChangePlan.value = true;
}

async function submitChangePlan() {
  if (!currentUser.value) return;
  try {
    await store.updateUser(currentUser.value.id, { plan: newPlan.value } as any);
    ElMessage.success("套餐修改成功");
    showChangePlan.value = false;
    fetchUsers();
  } catch {
    ElMessage.error("套餐修改失败");
  }
}

onMounted(fetchUsers);
</script>
