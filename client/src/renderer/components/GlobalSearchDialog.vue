<template>
  <Teleport to="body">
    <transition name="global-search">
      <div v-if="visible" class="global-search-overlay" @click.self="$emit('close')">
        <div class="global-search">
          <div class="global-search__header">
            <el-icon class="global-search__icon"><Search /></el-icon>
            <input
              ref="inputRef"
              v-model="query"
              class="global-search__input"
              placeholder="搜索商品、规则、页面、设置..."
              @keydown.esc="$emit('close')"
              @keydown.up.prevent="moveSelection(-1)"
              @keydown.down.prevent="moveSelection(1)"
              @keydown.enter="selectCurrent"
            />
            <kbd class="global-search__kbd">ESC</kbd>
          </div>

          <div v-if="query && filteredResults.length > 0" class="global-search__results">
            <div
              v-for="(group, gi) in groupedResults"
              :key="group.label"
              class="global-search__group"
            >
              <div class="global-search__group-label">{{ group.label }}</div>
              <div
                v-for="(item, ii) in group.items"
                :key="item.key"
                :class="['global-search__item', { 'global-search__item--active': selectedIndex === flatIndex(gi, ii) }]"
                @click="selectItem(item)"
                @mouseenter="selectedIndex = flatIndex(gi, ii)"
              >
                <el-icon class="global-search__item-icon"><component :is="item.icon" /></el-icon>
                <div class="global-search__item-info">
                  <span class="global-search__item-label">{{ item.label }}</span>
                  <span v-if="item.desc" class="global-search__item-desc">{{ item.desc }}</span>
                </div>
                <span v-if="item.shortcut" class="global-search__item-shortcut">{{ item.shortcut }}</span>
              </div>
            </div>
          </div>

          <div v-else-if="query && filteredResults.length === 0" class="global-search__empty">
            <p>未找到「{{ query }}」相关结果</p>
          </div>

          <div v-else class="global-search__hints">
            <div class="global-search__group">
              <div class="global-search__group-label">快速导航</div>
              <div
                v-for="(item, i) in quickNavItems"
                :key="item.key"
                :class="['global-search__item', { 'global-search__item--active': selectedIndex === i }]"
                @click="selectItem(item)"
                @mouseenter="selectedIndex = i"
              >
                <el-icon class="global-search__item-icon"><component :is="item.icon" /></el-icon>
                <div class="global-search__item-info">
                  <span class="global-search__item-label">{{ item.label }}</span>
                  <span v-if="item.desc" class="global-search__item-desc">{{ item.desc }}</span>
                </div>
                <span v-if="item.shortcut" class="global-search__item-shortcut">{{ item.shortcut }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from "vue";
import { useRouter } from "vue-router";
import {
  Search, Opportunity, Goods, MagicStick, Timer, Warning,
  Setting, Key, ChatDotRound, DataAnalysis, Document, Cpu, Bell
} from "@element-plus/icons-vue";

interface SearchItem {
  key: string;
  label: string;
  desc?: string;
  icon: any;
  action: string;
  shortcut?: string;
}

const props = defineProps<{ visible: boolean }>();
const emit = defineEmits<{ close: []; navigate: [path: string] }>();

const router = useRouter();
const query = ref("");
const inputRef = ref<HTMLInputElement>();
const selectedIndex = ref(0);

const allItems: SearchItem[] = [
  { key: "nav-dashboard", label: "机会雷达", desc: "发现商机，洞察异动", icon: Opportunity, action: "/dashboard" },
  { key: "nav-products", label: "我的商品", desc: "商品列表与详情", icon: Goods, action: "/products" },
  { key: "nav-category", label: "品类洞察", desc: "品类热力图与趋势", icon: DataAnalysis, action: "/category-insight" },
  { key: "nav-ai", label: "AI决策", desc: "智能分析与推荐", icon: MagicStick, action: "/ai" },
  { key: "nav-scheduler", label: "采集调度", desc: "任务队列与进度", icon: Timer, action: "/scheduler" },
  { key: "nav-monitor", label: "告警中心", desc: "告警规则与事件", icon: Warning, action: "/monitor" },
  { key: "nav-notifications", label: "通知中心", desc: "消息与提醒", icon: ChatDotRound, action: "/notifications" },
  { key: "nav-compare", label: "竞品对比", desc: "多商品横向对比", icon: DataAnalysis, action: "/compare" },
  { key: "nav-settings", label: "设置", desc: "账户、同步、隐私", icon: Setting, action: "/settings" },
  { key: "nav-license", label: "授权管理", desc: "套餐与激活", icon: Key, action: "/license" },
  { key: "action-sync", label: "立即同步", desc: "同步数据到云端", icon: Cpu, action: "action:sync" },
  { key: "action-collect", label: "开始采集", desc: "启动数据采集任务", icon: Timer, action: "action:collect" },
  { key: "action-ai-analyze", label: "AI快捷分析", desc: "对商品执行AI分析", icon: MagicStick, action: "/ai" },
  { key: "action-alert-rules", label: "告警规则管理", desc: "创建和编辑告警规则", icon: Warning, action: "/monitor" },
  { key: "action-export", label: "导出数据", desc: "导出本地数据为JSON", icon: Document, action: "action:export" },
  { key: "action-settings-team", label: "团队管理", desc: "创建团队、邀请成员", icon: Setting, action: "/settings" },
  { key: "action-settings-audit", label: "操作审计", desc: "查看操作日志", icon: Document, action: "/settings" },
  { key: "action-settings-security", label: "安全审计", desc: "查看安全日志", icon: Bell, action: "/settings" },
];

const quickNavItems = computed(() => allItems.slice(0, 10));

const filteredResults = computed(() => {
  if (!query.value.trim()) return [];
  const q = query.value.toLowerCase();
  return allItems.filter(
    (item) =>
      item.label.toLowerCase().includes(q) ||
      (item.desc && item.desc.toLowerCase().includes(q)) ||
      item.key.toLowerCase().includes(q)
  );
});

const groupedResults = computed(() => {
  const navItems = filteredResults.value.filter((i) => !i.action.startsWith("action:"));
  const actionItems = filteredResults.value.filter((i) => i.action.startsWith("action:"));
  const groups: { label: string; items: SearchItem[] }[] = [];
  if (navItems.length > 0) groups.push({ label: "页面导航", items: navItems });
  if (actionItems.length > 0) groups.push({ label: "快捷操作", items: actionItems });
  return groups;
});

function flatIndex(gi: number, ii: number): number {
  let idx = 0;
  const groups = groupedResults.value;
  for (let g = 0; g < gi; g++) idx += groups[g].items.length;
  return idx + ii;
}

function moveSelection(delta: number) {
  const total = query.value ? filteredResults.value.length : quickNavItems.value.length;
  if (total === 0) return;
  selectedIndex.value = (selectedIndex.value + delta + total) % total;
}

function selectCurrent() {
  const items = query.value ? filteredResults.value : quickNavItems.value;
  if (items[selectedIndex.value]) {
    selectItem(items[selectedIndex.value]);
  }
}

function selectItem(item: SearchItem) {
  if (item.action.startsWith("action:")) {
    const action = item.action.replace("action:", "");
    if (action === "sync") {
      window.electronAPI?.invoke("sync:now").catch(() => {});
    } else if (action === "collect") {
      window.electronAPI?.invoke("collect:start").catch(() => {});
    } else if (action === "export") {
      window.electronAPI?.invoke("storage:export-all").catch(() => {});
    }
  } else {
    router.push(item.action);
  }
  emit("close");
}

watch(
  () => props.visible,
  (v) => {
    if (v) {
      query.value = "";
      selectedIndex.value = 0;
      nextTick(() => inputRef.value?.focus());
    }
  }
);

watch(query, () => {
  selectedIndex.value = 0;
});
</script>

<style scoped>
.global-search-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 9999;
  display: flex;
  justify-content: center;
  padding-top: 15vh;
  backdrop-filter: blur(4px);
}

.global-search {
  width: 560px;
  max-height: 480px;
  background: var(--color-bg-card);
  border-radius: var(--radius-xl);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  border: 1px solid var(--color-border-light);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.global-search__header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border-light);
}

.global-search__icon {
  color: var(--color-text-tertiary);
  font-size: 20px;
  flex-shrink: 0;
}

.global-search__input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: var(--text-lg);
  color: var(--color-text-primary);
  font-family: var(--font-sans);
}

.global-search__input::placeholder {
  color: var(--color-text-tertiary);
}

.global-search__kbd {
  font-family: var(--font-sans);
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border);
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

.global-search__results,
.global-search__hints {
  overflow-y: auto;
  padding: 8px 0;
  flex: 1;
}

.global-search__group {
  margin-bottom: 4px;
}

.global-search__group-label {
  padding: 8px 20px 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.global-search__item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 20px;
  cursor: pointer;
  transition: background 0.15s;
}

.global-search__item:hover,
.global-search__item--active {
  background: var(--color-bg-hover);
}

.global-search__item-icon {
  color: var(--color-text-secondary);
  font-size: 18px;
  flex-shrink: 0;
}

.global-search__item-info {
  flex: 1;
  min-width: 0;
}

.global-search__item-label {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-primary);
}

.global-search__item-desc {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-left: 8px;
}

.global-search__item-shortcut {
  font-family: var(--font-sans);
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border-light);
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

.global-search__empty {
  padding: 32px 20px;
  text-align: center;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.global-search-enter-active {
  transition: opacity 0.15s ease;
}

.global-search-leave-active {
  transition: opacity 0.1s ease;
}

.global-search-enter-from,
.global-search-leave-to {
  opacity: 0;
}

.global-search-enter-active .global-search {
  animation: searchSlideIn 0.2s ease;
}

@keyframes searchSlideIn {
  from {
    transform: translateY(-10px) scale(0.98);
    opacity: 0;
  }
  to {
    transform: translateY(0) scale(1);
    opacity: 1;
  }
}

@media (max-width: 768px) {
  .global-search {
    width: calc(100vw - 32px);
    margin: 0 16px;
  }
}
</style>
