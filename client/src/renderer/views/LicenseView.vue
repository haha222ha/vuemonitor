<template>
  <div style="max-width: 560px; margin: 60px auto; padding: 0 20px">
    <div style="text-align: center; margin-bottom: 32px">
      <h2>小红书AI选品</h2>
      <p style="color: #909399; margin-top: 8px">激活授权码以解锁完整功能</p>
    </div>

    <el-card v-if="licenseStore.isActivated" shadow="hover">
      <div style="text-align: center; padding: 20px 0">
        <el-icon style="font-size: 48px; color: #67c23a"><CircleCheckFilled /></el-icon>
        <h3 style="margin-top: 12px">已激活</h3>
        <div style="margin-top: 16px">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="当前套餐">
              <el-tag type="success">{{ licenseStore.planLabel }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="到期时间">{{ licenseStore.expiresAtFormatted }}</el-descriptions-item>
            <el-descriptions-item label="设备ID">
              <span style="font-family: monospace; font-size: 12px">{{ licenseStore.license?.deviceId }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="激活时间">
              {{ licenseStore.license?.activatedAt ? new Date(licenseStore.license.activatedAt).toLocaleString("zh-CN") : '-' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
        <div style="margin-top: 20px">
          <el-button type="danger" @click="handleDeactivate">解除绑定</el-button>
        </div>
      </div>
    </el-card>

    <el-card v-else shadow="hover">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="授权码" prop="licenseKey">
          <el-input
            v-model="form.licenseKey"
            placeholder="XXXX-XXXX-XXXX-XXXX"
            maxlength="19"
            @input="formatLicenseKey"
            style="font-family: monospace; letter-spacing: 2px"
          />
        </el-form-item>
        <el-form-item label="验证方式">
          <el-radio-group v-model="form.verifyMode">
            <el-radio value="online">在线验证</el-radio>
            <el-radio value="offline">离线验证</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.verifyMode === 'online'" label="服务器" prop="serverUrl">
          <el-input v-model="form.serverUrl" placeholder="https://api.example.com" />
        </el-form-item>
      </el-form>

      <div v-if="licenseStore.error" style="margin: 12px 0">
        <el-alert :title="licenseStore.error" type="error" show-icon :closable="false" />
      </div>

      <div style="text-align: center; margin-top: 20px">
        <el-button
          type="primary"
          size="large"
          :loading="licenseStore.loading"
          @click="handleActivate"
          style="width: 100%"
        >
          激活
        </el-button>
      </div>

      <el-divider>设备信息</el-divider>
      <div style="font-size: 12px; color: #909399; text-align: center">
        <p>设备ID: {{ deviceInfo?.deviceId || '获取中...' }}</p>
        <p>指纹: {{ deviceInfo?.fingerprint?.substring(0, 16) || '...' }}...</p>
      </div>
    </el-card>

    <div style="margin-top: 24px">
      <el-card shadow="never">
        <template #header><span>套餐对比</span></template>
        <el-table :data="planData" stripe size="small">
          <el-table-column prop="feature" label="功能" width="140" />
          <el-table-column prop="free" label="免费版" width="80" align="center" />
          <el-table-column prop="pro" label="专业版" width="80" align="center" />
          <el-table-column prop="premium" label="高级版" width="80" align="center" />
          <el-table-column prop="enterprise" label="企业版" width="80" align="center" />
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { useLicenseStore } from "../stores/license";
import { ElMessage, ElMessageBox } from "element-plus";
import { CircleCheckFilled } from "@element-plus/icons-vue";
import type { FormInstance, FormRules } from "element-plus";

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
      validator: (_rule, value, callback) => {
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

const planData = [
  { feature: "监控商品数", free: "10", pro: "100", premium: "500", enterprise: "无限" },
  { feature: "并发采集", free: "2", pro: "5", premium: "8", enterprise: "10" },
  { feature: "定时采集", free: "-", pro: "20", premium: "100", enterprise: "无限" },
  { feature: "AI分析/天", free: "5", pro: "50", premium: "200", enterprise: "无限" },
  { feature: "趋势评分", free: "-", pro: "✓", premium: "✓", enterprise: "✓" },
  { feature: "爆品预测", free: "-", pro: "-", premium: "✓", enterprise: "✓" },
  { feature: "风险预警", free: "-", pro: "-", premium: "✓", enterprise: "✓" },
  { feature: "数据导出", free: "-", pro: "✓", premium: "✓", enterprise: "✓" },
];

function formatLicenseKey(val: string) {
  const raw = val.replace(/[^A-Za-z0-9]/g, "").toUpperCase();
  const parts = [];
  for (let i = 0; i < raw.length && i < 16; i += 4) {
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

onMounted(async () => {
  await licenseStore.fetchLicense();
  deviceInfo.value = await licenseStore.getDeviceInfo();
});
</script>
