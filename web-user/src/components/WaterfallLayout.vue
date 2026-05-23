<template>
  <div class="waterfall-layout" ref="containerRef">
    <div
      v-for="(column, colIdx) in columns"
      :key="colIdx"
      class="waterfall-layout__column"
    >
      <slot v-for="item in column.items" :key="itemKey(item)" :item="item" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from "vue";

const props = withDefaults(defineProps<{
  items: any[];
  itemKey: (item: any) => string | number;
  columnCount?: number;
  gap?: number;
  estimateHeight?: (item: any) => number;
}>(), {
  columnCount: 3,
  gap: 16,
});

const containerRef = ref<HTMLElement>();
const responsiveCols = ref(props.columnCount);

function updateColumnCount() {
  if (!containerRef.value) return;
  const width = containerRef.value.offsetWidth;
  if (width < 600) responsiveCols.value = 2;
  else if (width < 900) responsiveCols.value = 2;
  else if (width < 1200) responsiveCols.value = 3;
  else responsiveCols.value = props.columnCount;
}

const columns = computed(() => {
  const count = responsiveCols.value;
  const cols: { items: any[]; height: number }[] = Array.from({ length: count }, () => ({ items: [], height: 0 }));

  props.items.forEach((item) => {
    let minIdx = 0;
    for (let i = 1; i < count; i++) {
      if (cols[i].height < cols[minIdx].height) {
        minIdx = i;
      }
    }
    cols[minIdx].items.push(item);
    const estimatedH = props.estimateHeight ? props.estimateHeight(item) : 200;
    cols[minIdx].height += estimatedH + props.gap;
  });

  return cols;
});

let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  updateColumnCount();
  if (containerRef.value) {
    resizeObserver = new ResizeObserver(updateColumnCount);
    resizeObserver.observe(containerRef.value);
  }
});

onUnmounted(() => {
  resizeObserver?.disconnect();
});

watch(() => props.columnCount, updateColumnCount);

watch(() => props.items, () => {
  nextTick(() => updateColumnCount());
}, { deep: true });
</script>

<style scoped>
.waterfall-layout {
  display: flex;
  gap: v-bind(gap + 'px');
  width: 100%;
}

.waterfall-layout__column {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: v-bind(gap + 'px');
}
</style>
