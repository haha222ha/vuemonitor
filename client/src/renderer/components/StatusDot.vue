<template>
  <span :class="['status-dot', `status-dot--${status}`]" />
</template>

<script setup lang="ts">
defineProps<{
  status: "online" | "offline" | "busy" | "idle";
}>();
</script>

<style scoped>
.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot--online {
  background: var(--color-success);
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);
}

.status-dot--busy {
  background: var(--color-warning);
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.2);
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.status-dot--offline {
  background: var(--color-text-tertiary);
}

.status-dot--idle {
  background: var(--color-info);
  box-shadow: 0 0 0 3px rgba(107, 114, 128, 0.2);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
