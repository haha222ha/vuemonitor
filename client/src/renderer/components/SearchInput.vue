<template>
  <div class="search-input" :class="{ 'search-input--focused': focused }">
    <el-icon class="search-input__icon" :size="16"><Search /></el-icon>
    <input
      ref="inputRef"
      v-model="query"
      :placeholder="placeholder"
      class="search-input__field"
      @focus="focused = true"
      @blur="focused = false"
      @keydown.enter="$emit('search', query)"
      @keydown.esc="query = ''; $emit('search', '')"
    />
    <kbd v-if="shortcut" class="search-input__shortcut">{{ shortcut }}</kbd>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { Search } from "@element-plus/icons-vue";

defineProps<{
  placeholder?: string;
  shortcut?: string;
}>();

defineEmits<{
  search: [query: string];
}>();

const query = ref("");
const focused = ref(false);
const inputRef = ref<HTMLInputElement>();

function focus() {
  inputRef.value?.focus();
}

defineExpose({ focus });
</script>

<style scoped>
.search-input {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  height: 36px;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-base);
  transition: all 0.2s;
  max-width: 320px;
  width: 100%;
}

.search-input--focused {
  border-color: var(--color-primary-light);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
  background: var(--color-bg-card);
}

.search-input__icon {
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

.search-input__field {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  font-family: var(--font-sans);
}

.search-input__field::placeholder {
  color: var(--color-text-tertiary);
}

.search-input__shortcut {
  font-family: var(--font-sans);
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}
</style>
