import { ref, reactive, computed, onMounted } from "vue";
import { useLicenseStore } from "../stores/license";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";

export function useLicenseData() {
  const licenseStore = useLicenseStore();
  const formRef = ref<FormInstance>();
  const deviceInfo = ref<{ deviceId: string; fingerprint: string } | null>(null);

  const form = reactive({
    licenseKey: "",
    verifyMode: "online" as "online" | "offline",
    serverUrl: "",
  });

  const rules: FormRules = {
    licenseKey: [{ required: true, message: "请输入授权码", trigger: "blur" }],
    serverUrl: [
      {
        validator: (_rule: any, value: string, callback: any) => {
          if (form.verifyMode === "online" && !value) {
            callback(new Error("在线验证需要填写服务器地址"));
          } else {
            callback();
          }
        },
        trigger: "blur",
      },
    ],
  };

  const planTagType = computed(() => {
    const map: Record<string, string> = { free: "info", pro: "", premium: "warning", enterprise: "danger" };
    return map[licenseStore.plan] || "info";
  });

  const quotaItems = computed(() => {
    const q = licenseStore.quotas;
    return [
      { key: "maxProducts", label: "监控商品数", limit: q.maxProducts ?? 10, current: 0 },
      { key: "maxConcurrency", label: "并发采集数", limit: q.maxConcurrency ?? 2, current: 0 },
      { key: "maxScheduleTasks", label: "定时任务数", limit: q.maxScheduleTasks ?? 0, current: 0 },
      { key: "aiCallsPerDay", label: "AI分析次数/天", limit: q.aiCallsPerDay ?? 5, current: 0 },
      { key: "dailyCollectLimit", label: "日采集上限", limit: q.dailyCollectLimit ?? 50, current: 0 },
    ];
  });

  const planCards = [
    { key: "free", name: "免费版", price: "免费", features: ["10个监控商品", "2并发采集", "50次/日采集", "5次AI分析/天"] },
    { key: "pro", name: "专业版", price: "¥99/月", features: ["100个监控商品", "5并发采集", "500次/日采集", "50次AI分析/天", "趋势评分", "数据导出"] },
    { key: "premium", name: "高级版", price: "¥299/月", features: ["500个监控商品", "8并发采集", "2000次/日采集", "200次AI分析/天", "爆品预测", "风险预警", "团队协作"] },
    { key: "enterprise", name: "企业版", price: "联系销售", features: ["无限监控商品", "10并发采集", "无限日采集", "无限AI分析", "全部高级功能", "专属支持"] },
  ];

  function formatLicenseKey(val: string) {
    const raw = val.replace(/[^A-Za-z0-9]/g, "").toUpperCase();
    const parts: string[] = [];
    for (let i = 0; i < raw.length && i < 24; i += 4) {
      parts.push(raw.substring(i, i + 4));
    }
    form.licenseKey = parts.join("-");
  }

  async function handleActivate() {
    const valid = await formRef.value?.validate().catch(() => false);
    if (!valid) return;
    const serverUrl = form.verifyMode === "online" ? form.serverUrl : undefined;
    const success = await licenseStore.activate(form.licenseKey, serverUrl);
    if (success) {
      ElMessage.success("激活成功！功能已解锁");
      await licenseStore.fetchPlan();
    }
  }

  async function handleDeactivate() {
    try {
      await ElMessageBox.confirm("解除绑定后将恢复为免费版，确定继续？", "确认解绑", {
        confirmButtonText: "确定解绑",
        cancelButtonText: "取消",
        type: "warning",
      });
      await licenseStore.deactivate();
      ElMessage.success("已解除绑定");
    } catch {}
  }

  async function handleRefresh() {
    await licenseStore.fetchLicense();
    await licenseStore.fetchPlan();
    ElMessage.success("状态已刷新");
  }

  async function init() {
    await licenseStore.fetchLicense();
    await licenseStore.fetchPlan();
    deviceInfo.value = await licenseStore.getDeviceInfo();
  }

  return {
    licenseStore, formRef, deviceInfo, form, rules,
    planTagType, quotaItems, planCards,
    formatLicenseKey, handleActivate, handleDeactivate, handleRefresh,
    init,
  };
}
