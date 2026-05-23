﻿﻿﻿﻿﻿import { ref, computed } from "vue";
import api from "../utils/api";
import { usePermissionStore } from "../stores/permission";
import { ElMessage } from "element-plus";

export interface DiscoveryGoodsItem {
  ref: string;
  title: string;
  store_name: string;
  keyword: string;
  deal_price: number | null;
  deal_price_masked?: boolean;
  sold_num: number | null;
  sold_num_masked?: boolean;
  sold_num_approx?: string;
}

export interface DiscoveryStoreItem {
  ref: string;
  store_name: string;
  product_count: number;
  total_sold?: number | null;
  total_sold_masked?: boolean;
  avg_price?: number | null;
  avg_price_masked?: boolean;
}

export interface DiscoveryKeywordItem {
  keyword: string;
  item_count: number;
}

export interface DiscoveryFilters {
  minPrice: number | undefined;
  maxPrice: number | undefined;
  minSold: number | undefined;
  sortBy: string;
}

const DAILY_LIMITS: Record<string, number> = {
  free: 5,
  pro: 50,
  premium: 200,
  enterprise: Infinity,
};

function isElectron(): boolean {
  return !!(window as unknown as { electronAPI?: unknown }).electronAPI;
}

async function invokeIpc(channel: string, ...args: unknown[]): Promise<unknown> {
  const w = window as unknown as { electronAPI?: { invoke: (ch: string, ...a: unknown[]) => Promise<unknown> } };
  if (!w.electronAPI?.invoke) throw new Error("electronAPI not available");
  return w.electronAPI.invoke(channel, ...args);
}

function extractIpcItems(result: unknown): { items: unknown[]; total: number } {
  const r = result as { code?: number; data?: { items?: unknown[]; total?: number } } | null;
  if (r?.code === 0 && r?.data) {
    return { items: r.data.items || [], total: r.data.total || 0 };
  }
  return { items: [], total: 0 };
}

export function useDiscoveryData() {
  const permissionStore = usePermissionStore();

  const searchKeyword = ref("");
  const searchMode = ref<"goods" | "stores">("goods");
  const activeTab = ref("goods");
  const currentPage = ref(1);
  const pageSize = ref(20);
  const hasSearched = ref(false);
  const searchLoading = ref(false);
  const storeGoodsLoading = ref(false);

  const goodsResults = ref<DiscoveryGoodsItem[]>([]);
  const storeResults = ref<DiscoveryStoreItem[]>([]);
  const storeGoods = ref<DiscoveryGoodsItem[]>([]);
  const hotGoods = ref<DiscoveryGoodsItem[]>([]);
  const risingGoods = ref<DiscoveryGoodsItem[]>([]);
  const newGoods = ref<DiscoveryGoodsItem[]>([]);
  const burstLoading = ref(false);
  const burstTotal = ref(0);
  const burstPage = ref(1);
  const burstCategory = ref("");
  const keywords = ref<DiscoveryKeywordItem[]>([]);
  const totalItems = ref(0);
  const usedToday = ref(0);
  const dbStats = ref<{ total_goods: number; total_stores: number; total_keywords: number } | null>(null);

  const plan = computed(() => permissionStore.plan || "free");
  const dailyLimit = computed(() => DAILY_LIMITS[plan.value] ?? 5);
  const remainingSearch = computed(() => Math.max(0, dailyLimit.value - usedToday.value));
  const totalPages = computed(() => Math.ceil(totalItems.value / pageSize.value));

  const selectedStore = ref<DiscoveryStoreItem | null>(null);
  const showStoreGoods = ref(false);

  async function fetchQuota() {
    try {
      const { data } = await api.get("/discovery/quota");
      if (data.code === 0) {
        usedToday.value = data.data.used_today;
        if (data.data.db_stats) {
          dbStats.value = data.data.db_stats;
        }
      }
    } catch {
      if (isElectron()) {
        try {
          const result = await invokeIpc("discovery:quota") as { code?: number; data?: { used_today?: number; remaining?: number; db_stats?: { total_goods: number; total_stores: number; total_keywords: number } } };
          if (result?.code === 0 && result?.data) {
            usedToday.value = result.data.used_today || 0;
            if (result.data.db_stats) dbStats.value = result.data.db_stats;
          }
        } catch { /* ignore */ }
      }
    }
  }

  async function handleSearch(filters?: DiscoveryFilters) {
    if (!searchKeyword.value.trim()) return;
    hasSearched.value = true;
    searchLoading.value = true;
    currentPage.value = 1;

    try {
      if (searchMode.value === "goods") {
        const payload: Record<string, unknown> = {
          keyword: searchKeyword.value,
          page: 1,
          page_size: pageSize.value,
          sort_by: filters?.sortBy || "relevance",
        };
        if (filters?.minPrice != null) payload.min_price = filters.minPrice;
        if (filters?.maxPrice != null) payload.max_price = filters.maxPrice;
        if (filters?.minSold != null) payload.min_sold = filters.minSold;

        try {
          const { data } = await api.post("/discovery/search", payload);
          if (data.code === 0) {
            goodsResults.value = data.data.items;
            totalItems.value = data.data.total;
          }
        } catch {
          if (isElectron()) {
            const result = await invokeIpc("discovery:search", payload);
            const extracted = extractIpcItems(result);
            goodsResults.value = extracted.items as DiscoveryGoodsItem[];
            totalItems.value = extracted.total;
          }
        }
      } else {
        const storePayload = {
          keyword: searchKeyword.value,
          page: 1,
          page_size: pageSize.value,
        };
        try {
          const { data } = await api.post("/discovery/stores", storePayload);
          if (data.code === 0) {
            storeResults.value = data.data.items;
            totalItems.value = data.data.total;
          }
        } catch {
          if (isElectron()) {
            const result = await invokeIpc("discovery:stores", storePayload);
            const extracted = extractIpcItems(result);
            storeResults.value = extracted.items as DiscoveryStoreItem[];
            totalItems.value = extracted.total;
          }
        }
      }
      usedToday.value++;
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { code?: number; message?: string } } };
      if (axiosErr?.response?.data?.code === 42021) {
        usedToday.value = dailyLimit.value;
        ElMessage.warning(axiosErr.response.data.message || "搜索配额已用完");
      }
    } finally {
      searchLoading.value = false;
    }
  }

  async function handlePageChange(page: number, filters?: DiscoveryFilters) {
    currentPage.value = page;
    searchLoading.value = true;
    try {
      if (searchMode.value === "goods") {
        const payload: Record<string, unknown> = {
          keyword: searchKeyword.value,
          page,
          page_size: pageSize.value,
          sort_by: filters?.sortBy || "relevance",
        };
        if (filters?.minPrice != null) payload.min_price = filters.minPrice;
        if (filters?.maxPrice != null) payload.max_price = filters.maxPrice;
        if (filters?.minSold != null) payload.min_sold = filters.minSold;

        try {
          const { data } = await api.post("/discovery/search", payload);
          if (data.code === 0) {
            goodsResults.value = data.data.items;
            totalItems.value = data.data.total;
          }
        } catch {
          if (isElectron()) {
            const result = await invokeIpc("discovery:search", payload);
            const extracted = extractIpcItems(result);
            goodsResults.value = extracted.items as DiscoveryGoodsItem[];
            totalItems.value = extracted.total;
          }
        }
      } else {
        const storePayload = {
          keyword: searchKeyword.value,
          page,
          page_size: pageSize.value,
        };
        try {
          const { data } = await api.post("/discovery/stores", storePayload);
          if (data.code === 0) {
            storeResults.value = data.data.items;
            totalItems.value = data.data.total;
          }
        } catch {
          if (isElectron()) {
            const result = await invokeIpc("discovery:stores", storePayload);
            const extracted = extractIpcItems(result);
            storeResults.value = extracted.items as DiscoveryStoreItem[];
            totalItems.value = extracted.total;
          }
        }
      }
    } finally {
      searchLoading.value = false;
    }
  }

  function handleTabChange(tab: string) {
    if (tab === "keywords" && keywords.value.length === 0) fetchKeywords();
    if (tab === "hot" && hotGoods.value.length === 0) fetchHotGoods();
    if (tab === "burst") fetchBurstData("rising", 1);
  }

  async function fetchKeywords() {
    try {
      const { data } = await api.get("/discovery/keywords", { params: { page: 1, page_size: 100 } });
      if (data.code === 0) keywords.value = data.data.items;
    } catch {
      if (isElectron()) {
        try {
          const result = await invokeIpc("discovery:keywords", { page: 1, page_size: 100 });
          const extracted = extractIpcItems(result);
          keywords.value = extracted.items as DiscoveryKeywordItem[];
        } catch { /* ignore */ }
      }
    }
  }

  async function fetchHotGoods(category?: string) {
    try {
      const params: Record<string, unknown> = { page: 1, page_size: 20 };
      if (category) params.category = category;
      const { data } = await api.get("/discovery/hot-goods", { params });
      if (data.code === 0) hotGoods.value = data.data.items;
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { code?: number; message?: string } } };
      if (axiosErr?.response?.data?.code === 42023) {
        ElMessage.warning(axiosErr.response.data.message || "已达上限");
        return;
      }
      if (isElectron()) {
        try {
          const ipcParams: Record<string, unknown> = { page: 1, page_size: 20 };
          if (category) ipcParams.category = category;
          const result = await invokeIpc("discovery:hot-goods", ipcParams);
          const extracted = extractIpcItems(result);
          hotGoods.value = extracted.items as DiscoveryGoodsItem[];
        } catch { /* ignore */ }
      }
    }
  }

  async function viewStoreGoods(store: DiscoveryStoreItem) {
    selectedStore.value = store;
    showStoreGoods.value = true;
    storeGoodsLoading.value = true;
    try {
      const { data } = await api.get(`/discovery/stores/${store.ref}/goods`, {
        params: { page: 1, page_size: 50 },
      });
      if (data.code === 0) storeGoods.value = data.data.items;
    } catch {
      if (isElectron()) {
        try {
          const result = await invokeIpc("discovery:store-goods", store.ref, 1, 50);
          const extracted = extractIpcItems(result);
          storeGoods.value = extracted.items as DiscoveryGoodsItem[];
        } catch { /* ignore */ }
      }
    } finally {
      storeGoodsLoading.value = false;
    }
  }

  async function fetchBurstData(
    type: "rising" | "hot" | "new" = "rising",
    page = 1,
    category?: string,
  ) {
    burstLoading.value = true;
    burstPage.value = page;
    if (category !== undefined) burstCategory.value = category;

    const apiMap: Record<string, string> = {
      rising: "/discovery/rising-goods",
      hot: "/discovery/hot-goods",
      new: "/discovery/new-goods",
    };

    const params: Record<string, unknown> = { page, page_size: 20 };
    if (burstCategory.value) params.category = burstCategory.value;

    try {
      const { data } = await api.get(apiMap[type], { params });
      if (data.code === 0) {
        const target = type === "rising" ? risingGoods : type === "hot" ? hotGoods : newGoods;
        target.value = data.data.items;
        burstTotal.value = data.data.total;
      }
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { code?: number; message?: string } } };
      if (axiosErr?.response?.data?.code === 42023) {
        ElMessage.warning(axiosErr.response.data.message || "已达上限");
        return;
      }
      if (isElectron()) {
        try {
          const ipcChannel = `discovery:${type}-goods`;
          const result = await invokeIpc(ipcChannel, params);
          const extracted = extractIpcItems(result);
          const target = type === "rising" ? risingGoods : type === "hot" ? hotGoods : newGoods;
          target.value = extracted.items as DiscoveryGoodsItem[];
          burstTotal.value = extracted.total;
        } catch { /* ignore */ }
      }
    } finally {
      burstLoading.value = false;
    }
  }

  function quickSearch(keyword: string) {
    searchKeyword.value = keyword;
    searchMode.value = "goods";
    activeTab.value = "goods";
    handleSearch();
  }

  let debounceTimer: ReturnType<typeof setTimeout> | null = null;
  const DEBOUNCE_MS = 400;

  function debouncedSearch(filters?: DiscoveryFilters) {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      handleSearch(filters);
    }, DEBOUNCE_MS);
  }

  function cancelDebouncedSearch() {
    if (debounceTimer) {
      clearTimeout(debounceTimer);
      debounceTimer = null;
    }
  }

  return {
    searchKeyword,
    searchMode,
    activeTab,
    currentPage,
    pageSize,
    hasSearched,
    searchLoading,
    storeGoodsLoading,
    goodsResults,
    storeResults,
    storeGoods,
    hotGoods,
    risingGoods,
    newGoods,
    burstLoading,
    burstTotal,
    burstPage,
    burstCategory,
    keywords,
    totalItems,
    totalPages,
    remainingSearch,
    usedToday,
    dbStats,
    selectedStore,
    showStoreGoods,
    handleSearch,
    handleTabChange,
    handlePageChange,
    viewStoreGoods,
    fetchKeywords,
    fetchHotGoods,
    fetchBurstData,
    fetchQuota,
    quickSearch,
    debouncedSearch,
    cancelDebouncedSearch,
  };
}
