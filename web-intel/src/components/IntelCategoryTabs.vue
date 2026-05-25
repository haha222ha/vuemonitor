<template>
  <div class="intel-category-tabs" role="tablist">
    <button
      v-for="tab in tabs"
      :key="tab.value"
      type="button"
      role="tab"
      class="tab-pill"
      :class="{ active: modelValue === tab.value }"
      :style="tab.accent && modelValue === tab.value ? { borderColor: tab.accent, color: tab.accent } : undefined"
      @click="$emit('update:modelValue', tab.value)"
    >
      <span v-if="tab.icon" class="tab-icon">{{ tab.icon }}</span>
      <span class="tab-label">{{ tab.label }}</span>
      <span v-if="tab.count !== undefined" class="tab-count">{{ tab.count }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
// AIGC START
export interface CategoryTabItem {
  value: string
  label: string
  count?: number
  icon?: string
  accent?: string
}

defineProps<{
  tabs: CategoryTabItem[]
  modelValue: string
}>()

defineEmits<{
  "update:modelValue": [value: string]
}>()
// AIGC END
</script>

<style scoped>
.intel-category-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}
.tab-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: 1px solid var(--el-border-color, #dcdfe6);
  border-radius: 20px;
  background: var(--el-fill-color-blank, #fff);
  color: var(--el-text-color-regular, #606266);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.tab-pill:hover {
  border-color: var(--el-color-primary, #409eff);
  color: var(--el-color-primary, #409eff);
}
.tab-pill.active {
  background: var(--el-color-primary-light-9, #ecf5ff);
  border-color: var(--el-color-primary, #409eff);
  color: var(--el-color-primary, #409eff);
  font-weight: 600;
}
.tab-count {
  font-size: 11px;
  padding: 0 6px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.06);
  line-height: 18px;
}
.tab-pill.active .tab-count {
  background: rgba(64, 158, 255, 0.2);
}
.tab-icon {
  font-size: 14px;
}
</style>
