<template>
  <div class="category-sidebar">
    <div class="category-sidebar__header">
      <span class="category-sidebar__title">商品分类</span>
      <el-button v-if="!showAddInput" size="small" text @click="openAddDialog">
        <el-icon><Plus /></el-icon>
      </el-button>
    </div>

    <div v-if="showAddInput" class="category-sidebar__add">
      <el-input
        v-model="newCategoryName"
        size="small"
        placeholder="分类名称"
        @keyup.enter="addCategory"
        @keyup.escape="cancelAdd"
      >
        <template #append>
          <el-button :loading="adding" @click="addCategory">确定</el-button>
        </template>
      </el-input>
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
        <span v-if="cat.color" class="category-sidebar__dot" :style="{ background: cat.color }" />
        <el-icon v-else><Folder /></el-icon>
        <span class="category-sidebar__name">{{ cat.name }}</span>
        <span class="category-sidebar__count">{{ cat.product_count || 0 }}</span>
        <el-dropdown trigger="click" @command="(cmd: string) => handleCategoryAction(cmd, cat)" @click.stop>
          <el-icon class="category-sidebar__more" @click.stop><MoreFilled /></el-icon>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="edit">编辑</el-dropdown-item>
              <el-dropdown-item command="delete" style="color: var(--color-danger)">删除</el-dropdown-item>
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
          <el-color-picker v-model="editForm.color" show-alpha :predefine="predefineColors" />
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="editForm.icon" placeholder="图标名称（可选）" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="editForm.sort_order" :min="0" :max="999" />
        </el-form-item>
        <el-form-item label="父分类">
          <el-select v-model="editForm.parent_id" placeholder="无（顶级分类）" clearable>
            <el-option
              v-for="cat in availableParents"
              :key="cat.id"
              :label="cat.name"
              :value="cat.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { Plus, Goods, Folder, MoreFilled } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import api from "../utils/api";

export interface Category {
  id: string;
  name: string;
  icon: string | null;
  color: string | null;
  sort_order: number;
  parent_id: string | null;
  product_count: number;
  created_at: string | null;
}

const props = defineProps<{
  activeCategory: string | null;
  totalCount: number;
}>();

defineEmits<{
  select: [categoryId: string | null, categoryName: string | null];
}>();

const categories = ref<Category[]>([]);
const showAddInput = ref(false);
const newCategoryName = ref("");
const adding = ref(false);

const showEditDialog = ref(false);
const editingCategory = ref<Category | null>(null);
const saving = ref(false);

const editForm = ref({
  name: "",
  color: null as string | null,
  icon: null as string | null,
  sort_order: 0,
  parent_id: null as string | null,
});

const predefineColors = [
  "#409EFF", "#67C23A", "#E6A23C", "#F56C6C", "#909399",
  "#00BFA5", "#7C4DFF", "#FF6D00", "#C62828", "#1565C0",
];

const availableParents = computed(() => {
  return categories.value.filter((c) => c.id !== editingCategory.value?.id);
});

function isElectron(): boolean {
  return !!(window as unknown as { electronAPI?: unknown }).electronAPI;
}

async function invokeIpc(channel: string, ...args: unknown[]): Promise<unknown> {
  const w = window as unknown as { electronAPI?: { invoke: (ch: string, ...a: unknown[]) => Promise<unknown> } };
  if (!w.electronAPI?.invoke) throw new Error("electronAPI not available");
  return w.electronAPI.invoke(channel, ...args);
}

async function fetchCategories() {
  try {
    const { data } = await api.get("/categories");
    if (data.code === 0) {
      categories.value = data.data.categories || [];
      return;
    }
  } catch { /* fallback */ }

  if (isElectron()) {
    try {
      const result = await invokeIpc("category:list") as { code?: number; data?: { categories?: Category[] } };
      if (result?.code === 0 && result?.data) {
        categories.value = result.data.categories || [];
      }
    } catch { /* ignore */ }
  }
}

async function addCategory() {
  const name = newCategoryName.value.trim();
  if (!name) return;
  adding.value = true;
  try {
    try {
      const { data } = await api.post("/categories", { name, sort_order: 0 });
      if (data.code === 0) {
        ElMessage.success("分类已添加");
        newCategoryName.value = "";
        showAddInput.value = false;
        await fetchCategories();
        return;
      }
    } catch { /* fallback */ }

    if (isElectron()) {
      await invokeIpc("category:create", { name, sort_order: 0 });
      ElMessage.success("分类已添加（本地）");
      newCategoryName.value = "";
      showAddInput.value = false;
      await fetchCategories();
    }
  } catch (err) {
    ElMessage.error("添加失败：" + String(err));
  } finally {
    adding.value = false;
  }
}

function cancelAdd() {
  showAddInput.value = false;
  newCategoryName.value = "";
}

function openAddDialog() {
  editingCategory.value = null;
  editForm.value = { name: "", color: null, icon: null, sort_order: 0, parent_id: null };
  showEditDialog.value = true;
}

function handleCategoryAction(cmd: string, cat: Category) {
  if (cmd === "edit") {
    editingCategory.value = cat;
    editForm.value = {
      name: cat.name,
      color: cat.color,
      icon: cat.icon,
      sort_order: cat.sort_order,
      parent_id: cat.parent_id,
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
      try {
        const { data } = await api.put(`/categories/${editingCategory.value.id}`, editForm.value);
        if (data.code === 0) {
          ElMessage.success("已更新");
          showEditDialog.value = false;
          await fetchCategories();
          return;
        }
      } catch { /* fallback */ }

      if (isElectron()) {
        await invokeIpc("category:update", { id: editingCategory.value.id, ...editForm.value });
        ElMessage.success("已更新（本地）");
        showEditDialog.value = false;
        await fetchCategories();
      }
    } else {
      try {
        const { data } = await api.post("/categories", editForm.value);
        if (data.code === 0) {
          ElMessage.success("分类已添加");
          showEditDialog.value = false;
          await fetchCategories();
          return;
        }
      } catch { /* fallback */ }

      if (isElectron()) {
        await invokeIpc("category:create", editForm.value);
        ElMessage.success("分类已添加（本地）");
        showEditDialog.value = false;
        await fetchCategories();
      }
    }
  } catch (err) {
    ElMessage.error("保存失败：" + String(err));
  } finally {
    saving.value = false;
  }
}

async function confirmDelete(cat: Category) {
  try {
    await ElMessageBox.confirm(`确定删除分类「${cat.name}」？商品不会被删除`, "删除分类", { type: "warning" });

    try {
      const { data } = await api.delete(`/categories/${cat.id}`);
      if (data.code === 0) {
        ElMessage.success("已删除");
        await fetchCategories();
        return;
      }
    } catch { /* fallback */ }

    if (isElectron()) {
      await invokeIpc("category:delete", { id: cat.id });
      ElMessage.success("已删除（本地）");
      await fetchCategories();
    }
  } catch { /* user cancelled */ }
}

onMounted(fetchCategories);
</script>

<style scoped>
.category-sidebar {
  width: 200px;
  flex-shrink: 0;
  border-right: 1px solid var(--color-border-light);
  padding: var(--space-base);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.category-sidebar__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.category-sidebar__title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary);
}

.category-sidebar__add {
  margin-bottom: var(--space-xs);
}

.category-sidebar__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
}

.category-sidebar__item {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-base);
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  transition: all var(--duration-instant);
}

.category-sidebar__item:hover {
  background: var(--color-bg-page);
}

.category-sidebar__item--active {
  background: var(--color-primary-light);
  color: var(--color-primary);
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
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  background: var(--color-bg-page);
  padding: 0 6px;
  border-radius: 10px;
}

.category-sidebar__more {
  opacity: 0;
  transition: opacity var(--duration-instant);
  color: var(--color-text-tertiary);
  cursor: pointer;
}

.category-sidebar__item:hover .category-sidebar__more {
  opacity: 1;
}
</style>
