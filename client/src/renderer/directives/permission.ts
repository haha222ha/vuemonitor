import { Directive, DirectiveBinding } from "vue";
import { usePermissionStore } from "../stores/permission";

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
      } else {
        el.style.display = "none";
      }
    } else {
      el.removeAttribute("disabled");
      el.classList.remove("is-disabled", "permission-disabled");
      el.style.opacity = "";
      el.style.cursor = "";
      el.style.display = "";
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
