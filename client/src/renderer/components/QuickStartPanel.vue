<template>
  <div class="quick-start-panel">
    <div class="quick-start-panel__title">快速操作</div>
    <div class="quick-start-panel__grid">
      <div
        v-for="action in actions"
        :key="action.key"
        :class="['quick-start-panel__action', `quick-start-panel__action--${action.variant}`]"
        @click="action.onClick"
      >
        <el-icon :size="24" class="quick-start-panel__action-icon">
          <component :is="action.icon" />
        </el-icon>
        <span class="quick-start-panel__action-label">{{ action.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import { Plus, VideoPlay, MagicStick, Document } from "@element-plus/icons-vue";

const props = defineProps<{
  showAddProduct?: () => void;
  showAiPanel?: () => void;
  showReports?: () => void;
}>();

const router = useRouter();

const actions = computed(() => [
  { key: "add", icon: Plus, label: "添加商品", variant: "primary", onClick: () => props.showAddProduct?.() },
  { key: "collect", icon: VideoPlay, label: "开始采集", variant: "success", onClick: () => router.push("/products") },
  { key: "ai", icon: MagicStick, label: "AI分析", variant: "purple", onClick: () => props.showAiPanel?.() },
  { key: "report", icon: Document, label: "查看报告", variant: "info", onClick: () => props.showReports?.() },
]);
</script>

<style scoped>
.quick-start-panel {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-sm);
}

.quick-start-panel__title {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--space-base);
}

.quick-start-panel__grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md);
}

.quick-start-panel__action {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-lg);
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-out);
  border: 1px solid var(--color-border-light);
}

.quick-start-panel__action:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.quick-start-panel__action--primary {
  background: var(--color-primary-lightest);
  color: var(--color-primary);
}

.quick-start-panel__action--primary:hover {
  background: var(--color-primary-lighter);
}

.quick-start-panel__action--success {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.quick-start-panel__action--success:hover {
  background: var(--color-success-100);
}

.quick-start-panel__action--purple {
  background: #F3E8FF;
  color: #7C3AED;
}

.quick-start-panel__action--purple:hover {
  background: #E9D5FF;
}

.quick-start-panel__action--info {
  background: var(--color-info-50);
  color: var(--color-info-600);
}

.quick-start-panel__action--info:hover {
  background: var(--color-info-100);
}

.quick-start-panel__action-icon {
  transition: transform var(--duration-fast) var(--ease-bounce);
}

.quick-start-panel__action:hover .quick-start-panel__action-icon {
  transform: scale(1.1);
}

.quick-start-panel__action-label {
  font-size: var(--text-sm);
  font-weight: 500;
}

[data-theme="dark"] .quick-start-panel__action--primary {
  background: rgba(79, 70, 229, 0.15);
}

[data-theme="dark"] .quick-start-panel__action--primary:hover {
  background: rgba(79, 70, 229, 0.25);
}

[data-theme="dark"] .quick-start-panel__action--success {
  background: rgba(16, 185, 129, 0.15);
}

[data-theme="dark"] .quick-start-panel__action--success:hover {
  background: rgba(16, 185, 129, 0.25);
}

[data-theme="dark"] .quick-start-panel__action--purple {
  background: rgba(124, 58, 237, 0.15);
}

[data-theme="dark"] .quick-start-panel__action--purple:hover {
  background: rgba(124, 58, 237, 0.25);
}

[data-theme="dark"] .quick-start-panel__action--info {
  background: rgba(100, 116, 139, 0.15);
}

[data-theme="dark"] .quick-start-panel__action--info:hover {
  background: rgba(100, 116, 139, 0.25);
}

@media (max-width: 768px) {
  .quick-start-panel__grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
