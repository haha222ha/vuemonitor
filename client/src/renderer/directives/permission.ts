import { Directive, DirectiveBinding } from "vue";
import { usePermissionStore } from "../stores/permission";
import { ElMessageBox } from "element-plus";
import router from "../router";

const PLAN_LABELS: Record<string, string> = {
  free: "免费版",
  pro: "Pro",
  premium: "Premium",
  enterprise: "Enterprise",
};

const GATE_HINTS: Record<string, string> = {
  "gate:monitor:add": "添加更多商品",
  "gate:monitor:auto_refresh": "定时自动采集",
  "gate:monitor:export": "导出商品数据",
  "gate:monitor:category": "分类管理",
  "gate:monitor:compare": "商品对比",
  "gate:ai:trend_score": "AI趋势评分",
  "gate:ai:prediction": "AI爆品预测",
  "gate:ai:risk_warning": "AI风险预警",
  "gate:ai:basic_analysis": "AI分析",
  "gate:collect:cloud": "云端采集",
  "gate:discovery:search": "商品搜索",
  "gate:discovery:burst": "爆品洞察",
  "gate:discovery:advanced_filter": "高级筛选",
};

function getGateLabel(gateKey: string): string {
  return GATE_HINTS[gateKey] || "此功能";
}

function getRequiredPlan(gateKey: string): string {
  const permissionStore = usePermissionStore();
  const gate = permissionStore.gateList.find((g) => g.key === gateKey);
  return gate ? PLAN_LABELS[gate.requiredPlan] || gate.requiredPlan : "Pro";
}

function showUpgradeDialog(gateKey: string) {
  const featureLabel = getGateLabel(gateKey);
  const requiredPlan = getRequiredPlan(gateKey);
  ElMessageBox.alert(
    `${featureLabel}为${requiredPlan}及以上会员专属功能，升级即可解锁完整能力`,
    `升级解锁${featureLabel}`,
    {
      confirmButtonText: `了解${requiredPlan}套餐`,
      cancelButtonText: "暂不升级",
      showCancelButton: true,
      type: "info",
      customClass: "upgrade-prompt-dialog",
    }
  ).then(() => {
    router.push("/license");
  }).catch(() => {});
}

export const vPermission: Directive = {
  mounted(el: HTMLElement, binding: DirectiveBinding<string>) {
    const gateKey = binding.value;
    if (!gateKey) return;

    const permissionStore = usePermissionStore();
    const allowed = permissionStore.gates[gateKey];

    if (!allowed) {
      if (binding.modifiers.disable) {
        el.setAttribute("disabled", "disabled");
        el.classList.add("is-disabled", "permission-disabled");
        el.style.opacity = "0.5";
        el.style.cursor = "not-allowed";

        if (binding.modifiers.tooltip) {
          el.title = `${getGateLabel(gateKey)}需要${getRequiredPlan(gateKey)}及以上版本`;
          el.addEventListener("click", (e: Event) => {
            e.preventDefault();
            e.stopPropagation();
            showUpgradeDialog(gateKey);
          }, true);
        }
      } else {
        el.style.display = "none";
      }
    }
  },

  updated(el: HTMLElement, binding: DirectiveBinding<string>) {
    const gateKey = binding.value;
    if (!gateKey) return;

    const permissionStore = usePermissionStore();
    const allowed = permissionStore.gates[gateKey];

    if (!allowed) {
      if (binding.modifiers.disable) {
        el.setAttribute("disabled", "disabled");
        el.classList.add("is-disabled", "permission-disabled");
        el.style.opacity = "0.5";
        el.style.cursor = "not-allowed";
        el.style.display = "";

        if (binding.modifiers.tooltip) {
          el.title = `${getGateLabel(gateKey)}需要${getRequiredPlan(gateKey)}及以上版本`;
        }
      } else {
        el.style.display = "none";
      }
    } else {
      el.removeAttribute("disabled");
      el.classList.remove("is-disabled", "permission-disabled");
      el.style.opacity = "";
      el.style.cursor = "";
      el.style.display = "";
      el.title = "";
    }
  },
};

export function usePermission() {
  const permissionStore = usePermissionStore();

  function can(gateKey: string): boolean {
    return permissionStore.gates[gateKey] ?? false;
  }

  function cannot(gateKey: string): boolean {
    return !can(gateKey);
  }

  function canAny(...gateKeys: string[]): boolean {
    return gateKeys.some((key) => can(key));
  }

  function canAll(...gateKeys: string[]): boolean {
    return gateKeys.every((key) => can(key));
  }

  function getUpgradeHint(gateKey: string): string | null {
    if (can(gateKey)) return null;
    const gate = permissionStore.gateList.find((g) => g.key === gateKey);
    if (!gate) return null;
    return `此功能需要${gate.requiredPlan}及以上版本`;
  }

  return {
    can,
    cannot,
    canAny,
    canAll,
    getUpgradeHint,
    plan: permissionStore.plan,
    gates: permissionStore.gates,
  };
}

export function useUpgradePrompt() {
  function promptUpgrade(gateKey: string) {
    showUpgradeDialog(gateKey);
  }

  function promptUpgradeForField(field: "price" | "sales" | "keyword" | "store" | "shelf_time" | "filter_tag") {
    const fieldGateMap: Record<string, string> = {
      price: "gate:discovery:search",
      sales: "gate:discovery:search",
      keyword: "gate:discovery:burst",
      store: "gate:discovery:search",
      shelf_time: "gate:discovery:burst",
      filter_tag: "gate:discovery:burst",
    };
    const fieldLabelMap: Record<string, string> = {
      price: "价格",
      sales: "销量",
      keyword: "关键词",
      store: "店铺信息",
      shelf_time: "上架时间",
      filter_tag: "商品标签",
    };
    const gateKey = fieldGateMap[field] || "gate:discovery:search";
    const requiredPlan = getRequiredPlan(gateKey);
    const fieldLabel = fieldLabelMap[field] || field;

    ElMessageBox.alert(
      `升级${requiredPlan}即可查看完整${fieldLabel}信息，还可享受更多搜索次数和高级筛选功能`,
      `${fieldLabel}数据已隐藏`,
      {
        confirmButtonText: `了解${requiredPlan}套餐`,
        cancelButtonText: "暂不升级",
        showCancelButton: true,
        type: "info",
        customClass: "upgrade-prompt-dialog",
      }
    ).then(() => {
      router.push("/license");
    }).catch(() => {});
  }

  return {
    promptUpgrade,
    promptUpgradeForField,
  };
}
