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
              placeholder="搜索商品、页面、命令..."
              @keydown.esc="$emit('close')"
              @keydown.up.prevent="moveSelection(-1)"
              @keydown.down.prevent="moveSelection(1)"
              @keydown.enter="selectCurrent"
            >
            <kbd class="global-search__kbd">ESC</kbd>
          </div>

          <div class="global-search__mode-tabs">
            <button
              :class="['global-search__mode-tab', { 'global-search__mode-tab--active': mode === 'search' }]"
              @click="mode = 'search'"
            >
              🔍 搜索
            </button>
            <button
              :class="['global-search__mode-tab', { 'global-search__mode-tab--active': mode === 'command' }]"
              @click="mode = 'command'"
            >
              ⚡ 命令
            </button>
            <button
              :class="['global-search__mode-tab', { 'global-search__mode-tab--active': mode === 'recent' }]"
              @click="mode = 'recent'"
            >
              📋 最近访问
            </button>
          </div>

          <div v-if="mode === 'search'" class="global-search__content">
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
                </div>
              </div>
            </div>
          </div>

          <div v-if="mode === 'command'" class="global-search__content">
            <div class="global-search__group">
              <div class="global-search__group-label">常用命令</div>
              <div
                v-for="(cmd, i) in commandItems"
                :key="cmd.key"
                :class="['global-search__item', { 'global-search__item--active': selectedIndex === i }]"
                @click="executeCommand(cmd)"
                @mouseenter="selectedIndex = i"
              >
                <el-icon class="global-search__item-icon"><component :is="cmd.icon" /></el-icon>
                <div class="global-search__item-info">
                  <span class="global-search__item-label">{{ cmd.label }}</span>
                  <span class="global-search__item-desc">{{ cmd.desc }}</span>
                </div>
              </div>
            </div>
          </div>

          <div v-if="mode === 'recent'" class="global-search__content">
            <div v-if="recentItems.length > 0" class="global-search__group">
              <div class="global-search__group-label">最近访问</div>
              <div
                v-for="(item, i) in recentItems"
                :key="item.key"
                :class="['global-search__item', { 'global-search__item--active': selectedIndex === i }]"
                @click="selectItem(item)"
                @mouseenter="selectedIndex = i"
              >
                <el-icon class="global-search__item-icon"><component :is="item.icon" /></el-icon>
                <div class="global-search__item-info">
                  <span class="global-search__item-label">{{ item.label }}</span>
                  <span class="global-search__item-desc">{{ item.time }}</span>
                </div>
              </div>
            </div>
            <div v-else class="global-search__empty">
              <p>暂无最近访问记录</p>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from "vue";
import { useRouter } from "vue-router";
import {
  Search, Opportunity, Goods, MagicStick, Timer, Warning,
  Setting, Key, ChatDotRound, DataAnalysis, Document, Cpu, Bell,
  Plus, VideoPlay, Moon, Sunny
} from "@element-plus/icons-vue";
import { useTheme } from "../composables/useTheme";

interface SearchItem {
  key: string;
  label: string;
  desc?: string;
  icon: any;
  action: string;
  shortcut?: string;
  time?: string;
}

interface CommandItem {
  key: string;
  label: string;
  desc: string;
  icon: any;
  execute: () => void;
}

const props = defineProps<{ visible: boolean }>();
const emit = defineEmits<{ close: [] }>();

const router = useRouter();
const { isDark, toggle: toggleTheme } = useTheme();
const query = ref("");
const inputRef = ref<HTMLInputElement>();
const selectedIndex = ref(0);
const mode = ref<"search" | "command" | "recent">("search");
const recentItems = ref<SearchItem[]>([]);

const allItems: SearchItem[] = [
  { key: "nav-dashboard", label: "工作台", desc: "数据概览与快速操作", icon: Opportunity, action: "/dashboard" },
  { key: "nav-products", label: "我的商品", desc: "商品列表与详情", icon: Goods, action: "/products" },
  { key: "nav-discovery", label: "商品发现", desc: "搜索商品和店铺", icon: DataAnalysis, action: "/discovery" },
  { key: "nav-category", label: "品类洞察", desc: "品类热力图与趋势", icon: DataAnalysis, action: "/category-insight" },
  { key: "nav-ai", label: "AI决策", desc: "智能分析与推荐", icon: MagicStick, action: "/ai" },
  { key: "nav-scheduler", label: "采集调度", desc: "任务队列与进度", icon: Timer, action: "/scheduler" },
  { key: "nav-monitor", label: "告警中心", desc: "告警规则与事件", icon: Warning, action: "/monitor" },
  { key: "nav-notifications", label: "通知中心", desc: "消息与提醒", icon: ChatDotRound, action: "/notifications" },
  { key: "nav-compare", label: "竞品对比", desc: "多商品横向对比", icon: DataAnalysis, action: "/compare" },
  { key: "nav-settings", label: "设置", desc: "账户、同步、隐私", icon: Setting, action: "/settings" },
  { key: "nav-license", label: "授权管理", desc: "套餐与激活", icon: Key, action: "/license" },
];

const quickNavItems = computed(() => allItems.slice(0, 8));

const commandItems = computed<CommandItem[]>(() => [
  { key: "cmd-add-product", label: "添加商品", desc: "打开添加商品对话框", icon: Plus, execute: () => { router.push({ path: "/products", query: { add: "1" } }); emit("close"); } },
  { key: "cmd-collect", label: "开始采集", desc: "启动数据采集任务", icon: VideoPlay, execute: () => { window.electronAPI?.invoke("collect:start").catch(() => {}); emit("close"); } },
  { key: "cmd-ai", label: "AI分析", desc: "打开AI决策面板", icon: MagicStick, execute: () => { router.push("/ai"); emit("close"); } },
  { key: "cmd-reports", label: "查看报告", desc: "打开通知和报告列表", icon: Document, execute: () => { router.push("/notifications"); emit("close"); } },
  { key: "cmd-theme", label: "切换主题", desc: isDark.value ? "切换到浅色模式" : "切换到深色模式", icon: isDark.value ? Sunny : Moon, execute: () => { toggleTheme(); emit("close"); } },
]);

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
  const groups: { label: string; items: SearchItem[] }[] = [];
  if (filteredResults.value.length > 0) groups.push({ label: "页面导航", items: filteredResults.value });
  return groups;
});

function flatIndex(gi: number, ii: number): number {
  let idx = 0;
  const groups = groupedResults.value;
  for (let g = 0; g < gi; g++) idx += groups[g].items.length;
  return idx + ii;
}

function moveSelection(delta: number) {
  let total = 0;
  if (mode.value === "search") {
    total = query.value ? filteredResults.value.length : quickNavItems.value.length;
  } else if (mode.value === "command") {
    total = commandItems.value.length;
  } else {
    total = recentItems.value.length;
  }
  if (total === 0) return;
  selectedIndex.value = (selectedIndex.value + delta + total) % total;
}

function selectCurrent() {
  let items: SearchItem[] = [];
  if (mode.value === "search") {
    items = query.value ? filteredResults.value : quickNavItems.value;
  } else if (mode.value === "recent") {
    items = recentItems.value;
  }
  if (items[selectedIndex.value]) {
    selectItem(items[selectedIndex.value]);
  }
}

function selectItem(item: SearchItem) {
  if (item.action && !item.action.startsWith("action:")) {
    router.push(item.action);
    addRecent(item);
  }
  emit("close");
}

function executeCommand(cmd: CommandItem) {
  cmd.execute();
}

function addRecent(item: SearchItem) {
  const now = new Date();
  const timeStr = `${now.getHours()}:${String(now.getMinutes()).padStart(2, "0")}`;
  const recent = { ...item, time: timeStr };
  recentItems.value = [recent, ...recentItems.value.filter((r) => r.key !== item.key)].slice(0, 10);
  try {
    localStorage.setItem("recent-visits", JSON.stringify(recentItems.value));
  } catch {}
}

function loadRecent() {
  try {
    const saved = localStorage.getItem("recent-visits");
    if (saved) recentItems.value = JSON.parse(saved);
  } catch {}
}

watch(
  () => props.visible,
  (v) => {
    if (v) {
      query.value = "";
      selectedIndex.value = 0;
      mode.value = "search";
      loadRecent();
      nextTick(() => inputRef.value?.focus());
    }
  }
);

watch(query, () => {
  selectedIndex.value = 0;
});

onMounted(() => {
  loadRecent();
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
  padding-top: 10vh;
  backdrop-filter: blur(4px);
}

.global-search {
  width: 600px;
  max-height: 520px;
  background: var(--color-bg-card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  border: 1px solid var(--color-border-light);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.global-search__header {
  display: flex;
  align-items: center;
  gap: var(--space-base);
  padding: var(--space-base) var(--space-lg);
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
  padding: var(--space-2xs) var(--space-sm);
  border-radius: var(--radius-xs);
  background: var(--color-bg-page);
  border: 1px solid var(--color-border);
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

.global-search__mode-tabs {
  display: flex;
  gap: var(--space-xs);
  padding: var(--space-sm) var(--space-lg) 0;
  border-bottom: 1px solid var(--color-border-light);
}

.global-search__mode-tab {
  padding: var(--space-sm) var(--space-base);
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  border-radius: var(--radius-base) var(--radius-base) 0 0;
  transition: all var(--duration-fast) var(--ease-out);
}

.global-search__mode-tab:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.global-search__mode-tab--active {
  background: var(--color-bg-page);
  color: var(--color-primary);
  border-bottom: 2px solid var(--color-primary);
}

.global-search__content {
  overflow-y: auto;
  padding: var(--space-sm) 0;
  flex: 1;
}

.global-search__results {
  overflow-y: auto;
  padding: var(--space-sm) 0;
  flex: 1;
}

.global-search__group {
  margin-bottom: var(--space-xs);
}

.global-search__group-label {
  padding: var(--space-sm) var(--space-lg) var(--space-xs);
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.global-search__item {
  display: flex;
  align-items: center;
  gap: var(--space-base);
  padding: var(--space-sm) var(--space-lg);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
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
  margin-left: var(--space-sm);
}

.global-search__item-shortcut {
  font-family: var(--font-sans);
  font-size: 11px;
  padding: var(--space-2xs) var(--space-xs);
  border-radius: var(--radius-xs);
  background: var(--color-bg-page);
  border: 1px solid var(--color-border-light);
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

.global-search__empty {
  padding: var(--space-2xl) var(--space-lg);
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
    width: calc(100vw - var(--space-xl));
    margin: 0 var(--space-base);
  }
}
</style>
