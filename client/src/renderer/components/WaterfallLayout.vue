<template>
  <div ref="containerRef" class="waterfall-layout" :style="{ gap: `${gap}px` }">
    <div v-for="(col, i) in columns" :key="i" class="waterfall-layout__column" :style="{ gap: `${gap}px` }">
      <div v-for="item in col.items" :key="itemKey(item)" class="waterfall-layout__item">
        <slot :item="item" :index="items.indexOf(item)" />
      </div>
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
  minColumnWidth?: number;
  estimateHeight?: (item: any) => number;
}>(), {
  columnCount: 3,
  gap: 16,
  minColumnWidth: 260,
});

const containerRef = ref<HTMLElement>();
const responsiveColumns = ref(props.columnCount);
const columnHeights = ref<number[]>([]);

const effectiveColumns = computed(() => responsiveColumns.value);

const columns = computed(() => {
  const count = effectiveColumns.value;
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

function updateColumnCount() {
  if (!containerRef.value) return;
  const width = containerRef.value.offsetWidth;
  const maxCols = Math.floor((width + props.gap) / (props.minColumnWidth + props.gap));
  responsiveColumns.value = Math.max(1, Math.min(maxCols || props.columnCount, props.columnCount));
}

function recalculateHeights() {
  if (!containerRef.value) return;
  const colElements = containerRef.value.querySelectorAll(".waterfall-layout__column");
  const newHeights: number[] = [];
  colElements.forEach((col) => {
    newHeights.push((col as HTMLElement).offsetHeight);
  });
  columnHeights.value = newHeights;
}

const resizeObserver = new ResizeObserver(() => updateColumnCount());

onMounted(() => {
  if (containerRef.value) {
    resizeObserver.observe(containerRef.value);
    updateColumnCount();
  }
});

onUnmounted(() => {
  resizeObserver.disconnect();
});

watch(() => props.columnCount, (val) => {
  responsiveColumns.value = val;
  updateColumnCount();
});

watch(() => props.items, () => {
  nextTick(() => recalculateHeights());
}, { deep: true });
</script>

<style scoped>
.waterfall-layout {
  display: flex;
  width: 100%;
}

.waterfall-layout__column {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.waterfall-layout__item {
  break-inside: avoid;
}
</style>
