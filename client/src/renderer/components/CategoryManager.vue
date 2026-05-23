<template>
  <div class="category-manager">
    <div class="category-manager__header">
      <h3 class="manager-title">商品分类管理</h3>
      <el-button type="primary" size="small" @click="showAddModal = true">
        <Plus />
        添加分类
      </el-button>
    </div>

    <div class="category-manager__tree">
      <el-tree
        ref="treeRef"
        :data="categories"
        :props="treeProps"
        :default-expand-all="true"
        node-key="id"
        :highlight-current="true"
        @node-click="handleNodeClick"
      >
        <template #default="{ data }">
          <span class="tree-node">
            <el-icon :size="16" class="node-icon">
              <Folder v-if="data.children?.length" />
              <FolderOpened v-else />
            </el-icon>
            <span>{{ data.name }}</span>
            <span v-if="data.count !== undefined" class="node-count">
              {{ data.count }}
            </span>
          </span>
        </template>
        <template #expand-icon="{ expanded }">
          <el-icon :size="16"><ArrowDown v-if="expanded" /><ArrowRight v-else /></el-icon>
        </template>
      </el-tree>
    </div>

    <div v-if="selectedCategory" class="category-manager__detail">
      <div class="detail-header">
        <span class="detail-title">{{ selectedCategory.name }}</span>
        <div class="detail-actions">
          <el-button size="small" @click="showEditModal = true">
            <Edit />
            编辑
          </el-button>
          <el-button size="small" type="danger" @click="confirmDelete">
            <Delete />
            删除
          </el-button>
        </div>
      </div>
      <div class="detail-content">
        <div class="detail-row">
          <span class="detail-label">分类ID</span>
          <span class="detail-value">{{ selectedCategory.id }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">父级分类</span>
          <span class="detail-value">{{ parentName || '无' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">商品数量</span>
          <span class="detail-value">{{ selectedCategory.count || 0 }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">创建时间</span>
          <span class="detail-value">{{ formatDate(selectedCategory.createdAt) }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">排序</span>
          <span class="detail-value">{{ selectedCategory.sortOrder || 0 }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">状态</span>
          <span :class="['detail-value', selectedCategory.enabled ? 'status-active' : 'status-disabled']">
            {{ selectedCategory.enabled ? '启用' : '禁用' }}
          </span>
        </div>
      </div>
    </div>

    <el-dialog
      v-model="showAddModal"
      :title="isEditing ? '编辑分类' : '添加分类'"
      width="400px"
    >
      <form ref="formRef" class="category-form">
        <el-form-item label="分类名称" prop="name">
          <el-input
            v-model="formData.name"
            placeholder="请输入分类名称"
            class="form-input"
          />
        </el-form-item>
        <el-form-item label="父级分类" prop="parentId">
          <el-select
            v-model="formData.parentId"
            placeholder="请选择父级分类"
            class="form-input"
          >
            <el-option label="无（顶级分类）" value="" />
            <el-option
              v-for="cat in availableParents"
              :key="cat.id"
              :label="cat.name"
              :value="cat.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="排序" prop="sortOrder">
          <el-input-number
            v-model="formData.sortOrder"
            :min="0"
            :max="999"
            class="form-input"
          />
        </el-form-item>
        <el-form-item>
          <el-switch
            v-model="formData.enabled"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>
      </form>
      <template #footer>
        <el-button @click="closeModal">取消</el-button>
        <el-button type="primary" @click="saveCategory">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from "vue";
import {
  Plus,
  Edit,
  Delete,
  Folder,
  FolderOpened,
  ArrowRight,
  ArrowDown,
} from "@element-plus/icons-vue";

interface Category {
  id: string;
  name: string;
  parentId?: string;
  children?: Category[];
  count?: number;
  createdAt?: string;
  sortOrder?: number;
  enabled?: boolean;
}

const props = defineProps<{
  categories: Category[];
}>();

const emit = defineEmits<{
  (e: "select", category: Category): void;
  (e: "add", category: Omit<Category, "id" | "createdAt" | "count">): void;
  (e: "update", category: Category): void;
  (e: "delete", id: string): void;
}>();

const treeRef = ref();
const showAddModal = ref(false);
const showEditModal = ref(false);
const selectedCategory = ref<Category | null>(null);
const isEditing = ref(false);

const treeProps = {
  label: "name",
  children: "children",
};

const formData = reactive({
  name: "",
  parentId: "",
  sortOrder: 0,
  enabled: true,
});

const availableParents = computed(() => {
  const flatCategories: Category[] = [];
  const flatten = (cats: Category[], parentId?: string) => {
    cats.forEach((cat) => {
      if (cat.id !== selectedCategory.value?.id) {
        flatCategories.push({ ...cat, parentId });
      }
      if (cat.children) {
        flatten(cat.children, cat.id);
      }
    });
  };
  flatten(props.categories);
  return flatCategories;
});

const parentName = computed(() => {
  if (!selectedCategory.value?.parentId) return "";
  const findParent = (cats: Category[]): string => {
    for (const cat of cats) {
      if (cat.id === selectedCategory.value?.parentId) {
        return cat.name;
      }
      if (cat.children) {
        const found = findParent(cat.children);
        if (found) return found;
      }
    }
    return "";
  };
  return findParent(props.categories);
});

function handleNodeClick(data: Category) {
  selectedCategory.value = data;
  emit("select", data);
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleString("zh-CN");
}

function closeModal() {
  showAddModal.value = false;
  showEditModal.value = false;
  isEditing.value = false;
  resetForm();
}

function resetForm() {
  formData.name = "";
  formData.parentId = "";
  formData.sortOrder = 0;
  formData.enabled = true;
}

function openAddModal() {
  resetForm();
  isEditing.value = false;
  showAddModal.value = true;
}

function openEditModal() {
  if (!selectedCategory.value) return;
  formData.name = selectedCategory.value.name;
  formData.parentId = selectedCategory.value.parentId || "";
  formData.sortOrder = selectedCategory.value.sortOrder || 0;
  formData.enabled = selectedCategory.value.enabled ?? true;
  isEditing.value = true;
  showEditModal.value = true;
}

function saveCategory() {
  if (!formData.name.trim()) {
    console.warn("请输入分类名称");
    return;
  }

  if (isEditing.value && selectedCategory.value) {
    emit("update", {
      ...selectedCategory.value,
      name: formData.name,
      parentId: formData.parentId || undefined,
      sortOrder: formData.sortOrder,
      enabled: formData.enabled,
    });
  } else {
    emit("add", {
      name: formData.name,
      parentId: formData.parentId || undefined,
      sortOrder: formData.sortOrder,
      enabled: formData.enabled,
    });
  }

  closeModal();
}

function confirmDelete() {
  if (!selectedCategory.value) return;
  if (selectedCategory.value.count && selectedCategory.value.count > 0) {
    console.warn("该分类下存在商品，无法删除");
    return;
  }
  emit("delete", selectedCategory.value.id);
  selectedCategory.value = null;
}

defineExpose({
  openAddModal,
  openEditModal,
});
</script>

<style lang="scss" scoped>
.category-manager {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.category-manager__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #eee;
}

.manager-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

.category-manager__tree {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
}

.node-icon {
  color: #e6a23c;
}

.node-count {
  margin-left: auto;
  font-size: 12px;
  color: #999;
  background: #f5f5f5;
  padding: 2px 8px;
  border-radius: 10px;
}

.category-manager__detail {
  padding: 16px;
  border-top: 1px solid #eee;
  background: #fafafa;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.detail-title {
  font-size: 16px;
  font-weight: 600;
}

.detail-actions {
  display: flex;
  gap: 8px;
}

.detail-content {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;

  &:last-child {
    border-bottom: none;
  }
}

.detail-label {
  color: #999;
  font-size: 14px;
}

.detail-value {
  font-size: 14px;
  font-weight: 500;

  &.status-active {
    color: #67c23a;
  }

  &.status-disabled {
    color: #999;
  }
}

.category-form {
  padding: 8px;
}

.form-input {
  width: 100%;
}
</style>