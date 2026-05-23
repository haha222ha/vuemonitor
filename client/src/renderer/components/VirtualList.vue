<template>
  <div ref="containerRef" class="virtual-list" :style="{ height: `${height}px` }">
    <div class="virtual-list__phantom" :style="{ height: `${phantomHeight}px` }" />
    <div class="virtual-list__content" :style="{ transform: `translateY(${offsetY}px)` }">
      <div
        v-for="item in visibleData"
        :key="item[keyField]"
        class="virtual-list__item"
        :style="{ height: `${itemHeight}px` }"
      >
        <slot :item="item" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";

const props = withDefaults(defineProps<{
  data: Record<string, any>[];
  itemHeight: number;
  height: number;
  keyField?: string;
  buffer?: number;
}>(), {
  keyField: "id",
  buffer: 5,
});

const containerRef = ref<HTMLElement>();
const scrollTop = ref(0);
let rafId: number | null = null;

const visibleCount = computed(() => Math.ceil(props.height / props.itemHeight) + 2 + props.buffer * 2);
const phantomHeight = computed(() => props.data.length * props.itemHeight);

const startIndex = computed(() => Math.max(0, Math.floor(scrollTop.value / props.itemHeight) - props.buffer));
const endIndex = computed(() => Math.min(startIndex.value + visibleCount.value, props.data.length));

const visibleData = computed(() => props.data.slice(startIndex.value, endIndex.value));
const offsetY = computed(() => Math.max(0, startIndex.value * props.itemHeight));

function handleScroll() {
  if (rafId !== null) return;
  rafId = requestAnimationFrame(() => {
    if (containerRef.value) {
      scrollTop.value = containerRef.value.scrollTop;
    }
    rafId = null;
  });
}

onMounted(() => {
  containerRef.value?.addEventListener("scroll", handleScroll, { passive: true });
});

onUnmounted(() => {
  containerRef.value?.removeEventListener("scroll", handleScroll);
  if (rafId !== null) {
    cancelAnimationFrame(rafId);
    rafId = null;
  }
});
</script>

<style scoped>
.virtual-list {
  overflow-y: auto;
  position: relative;
}

.virtual-list__phantom {
  position: absolute;
  left: 0;
  top: 0;
  right: 0;
  z-index: -1;
}

.virtual-list__content {
  left: 0;
  right: 0;
  top: 0;
  position: absolute;
}

.virtual-list__item {
  box-sizing: border-box;
  width: 100%;
}
</style>
