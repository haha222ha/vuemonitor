<template>
  <div class="category-sidebar">
    <div class="category-sidebar__header">
      <span class="category-sidebar__title">商品分类</span>
      <el-button size="small" text @click="openAddDialog">
        <el-icon><Plus /></el-icon>
      </el-button>
    </div>

    <div class="category-sidebar__list">
      <div
        :class="['category-sidebar__item', { 'category-sidebar__item--active': activeCategory === null }]"
        @click="$emit('select', null, null)"
      >
        <el-icon><Goods /></el-icon>
        <span>全部商品</span>
        <span class="category-sidebar__count">{{ totalCount }}</span>
      </div>

      <div
        v-for="cat in categories"
        :key="cat.id"
        :class="['category-sidebar__item', { 'category-sidebar__item--active': activeCategory === cat.id }]"
        @click="$emit('select', cat.id, cat.name)"
      >
        <span v-if="cat.color" class="category-sidebar__dot" :style="{ background: cat.color }"></span>
        <el-icon v-else><Folder /></el-icon>
        <span class="category-sidebar__name">{{ cat.name }}</span>
        <span class="category-sidebar__count">{{ cat.product_count || 0 }}</span>
        <el-dropdown trigger="click" @command="(cmd: string) => handleCategoryAction(cmd, cat)" @click.stop>
          <el-icon class="category-sidebar__more" @click.stop><MoreFilled /></el-icon>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="edit">编辑</el-dropdown-item>
              <el-dropdown-item command="delete" style="color: var(--el-color-danger)">删除</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <el-dialog v-model="showEditDialog" :title="editingCategory ? '编辑分类' : '添加分类'" width="380px" append-to-body>
      <el-form label-width="70px" size="small">
        <el-form-item label="名称">
          <el-input v-model="editForm.name" placeholder="分类名称" />
        </el-form-item>
        <el-form-item label="颜色">
          <el-color-picker v-model="editForm.color" :predefine="predefineColors" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="editForm.sort_order" :min="0" :max="999" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="saveEdit" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Plus, Goods, Folder, MoreFilled } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import api from "../utils/api";

export interface Category {
  id: string;
  name: string;
  color: string | null;
  sort_order: number;
  product_count: number;
}

const props = defineProps<{
  activeCategory: string | null;
  totalCount: number;
}>();

defineEmits<{
  select: [categoryId: string | null, categoryName: string | null];
}>();

const categories = ref<Category[]>([]);
const showEditDialog = ref(false);
const editingCategory = ref<Category | null>(null);
const saving = ref(false);

const editForm = ref({
  name: "",
  color: null as string | null,
  sort_order: 0,
});

const predefineColors = [
  "#409EFF", "#67C23A", "#E6A23C", "#F56C6C", "#909399",
  "#00BFA5", "#7C4DFF", "#FF6D00", "#C62828", "#1565C0",
];

async function fetchCategories() {
  try {
    const { data } = await api.get("/categories");
    if (data.code === 0) {
      categories.value = data.data?.categories || data.data || [];
    }
  } catch { /* ignore */ }
}

function openAddDialog() {
  editingCategory.value = null;
  editForm.value = { name: "", color: null, sort_order: 0 };
  showEditDialog.value = true;
}

function handleCategoryAction(cmd: string, cat: Category) {
  if (cmd === "edit") {
    editingCategory.value = cat;
    editForm.value = {
      name: cat.name,
      color: cat.color,
      sort_order: cat.sort_order,
    };
    showEditDialog.value = true;
  } else if (cmd === "delete") {
    confirmDelete(cat);
  }
}

async function saveEdit() {
  if (!editForm.value.name.trim()) {
    ElMessage.warning("请输入分类名称");
    return;
  }
  saving.value = true;
  try {
    if (editingCategory.value) {
      await api.put(`/categories/${editingCategory.value.id}`, editForm.value);
      ElMessage.success("已更新");
    } else {
      await api.post("/categories", editForm.value);
      ElMessage.success("分类已添加");
    }
    showEditDialog.value = false;
    await fetchCategories();
  } catch (err: any) {
    ElMessage.error("保存失败：" + (err?.response?.data?.message || String(err)));
  } finally {
    saving.value = false;
  }
}

async function confirmDelete(cat: Category) {
  try {
    await ElMessageBox.confirm(`确定删除分类「${cat.name}」？商品不会被删除`, "删除分类", { type: "warning" });
    await api.delete(`/categories/${cat.id}`);
    ElMessage.success("已删除");
    await fetchCategories();
  } catch { /* user cancelled */ }
}

onMounted(fetchCategories);
</script>

<style scoped>
.category-sidebar {
  width: 200px;
  flex-shrink: 0;
  border-right: 1px solid var(--el-border-color-lighter);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.category-sidebar__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.category-sidebar__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.category-sidebar__list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.category-sidebar__item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: var(--el-text-color-regular);
  transition: all 0.15s;
}
.category-sidebar__item:hover {
  background: var(--el-fill-color-light);
}
.category-sidebar__item--active {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-weight: 500;
}
.category-sidebar__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.category-sidebar__name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.category-sidebar__count {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  background: var(--el-fill-color);
  padding: 0 6px;
  border-radius: 10px;
}
.category-sidebar__more {
  opacity: 0;
  transition: opacity 0.15s;
  color: var(--el-text-color-placeholder);
  cursor: pointer;
}
.category-sidebar__item:hover .category-sidebar__more {
  opacity: 1;
}
</style>
