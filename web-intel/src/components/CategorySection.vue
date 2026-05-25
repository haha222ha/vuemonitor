<template>
  <section class="category-section">
    <div class="section-head">
      <h3 class="section-title">
        <span class="section-dot" :style="{ background: accent }"></span>
        {{ title }}
      </h3>
      <span class="section-count">{{ count }} 项</span>
    </div>
    <slot />
  </section>
</template>

<script setup lang="ts">
// AIGC START
withDefaults(
  defineProps<{
    title: string
    count: number
    accent?: string
  }>(),
  { accent: "#409eff" },
)
// AIGC END
</script>

<style scoped>
.category-section {
  margin-bottom: 28px;
}
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--intel-border, #ebeef5);
}
.section-title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--intel-text, #303133);
  display: flex;
  align-items: center;
  gap: 8px;
}
.section-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.section-count {
  font-size: 12px;
  color: #909399;
}
</style>
