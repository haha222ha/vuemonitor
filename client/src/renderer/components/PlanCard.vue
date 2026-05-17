<template>
  <div class="plan-card" @click="$emit('click')">
    <div class="plan-card__header">
      <span class="plan-card__name">{{ planLabel }}</span>
      <el-tag v-if="expiresAt" size="small" :type="isExpiringSoon ? 'warning' : 'success'" effect="dark">
        {{ isExpiringSoon ? '即将到期' : '有效' }}
      </el-tag>
    </div>
    <div v-if="expiresAt" class="plan-card__expires">
      到期：{{ expiresAt }}
    </div>
    <div class="plan-card__action">
      <span>管理授权</span>
      <el-icon :size="14"><ArrowRight /></el-icon>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { ArrowRight } from "@element-plus/icons-vue";

const props = defineProps<{
  plan: string;
  expiresAt?: string;
}>();

defineEmits<{
  click: [];
}>();

const planLabels: Record<string, string> = {
  free: "免费版",
  pro: "专业版",
  premium: "高级版",
  enterprise: "企业版",
};

const planLabel = computed(() => planLabels[props.plan] || props.plan);

const isExpiringSoon = computed(() => {
  if (!props.expiresAt || props.expiresAt === "永久") return false;
  const d = new Date(props.expiresAt);
  const now = new Date();
  return d.getTime() - now.getTime() < 7 * 24 * 60 * 60 * 1000;
});
</script>

<style scoped>
.plan-card {
  margin: 12px;
  padding: 16px;
  background: rgba(79, 70, 229, 0.15);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(79, 70, 229, 0.2);
  cursor: pointer;
  transition: all 0.2s;
}

.plan-card:hover {
  background: rgba(79, 70, 229, 0.25);
}

.plan-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.plan-card__name {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text-inverse);
}

.plan-card__expires {
  font-size: var(--text-xs);
  color: #A5B4FC;
  margin-bottom: 12px;
}

.plan-card__action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--text-sm);
  color: #C7D2FE;
}
</style>
