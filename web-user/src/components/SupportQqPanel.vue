<template>
  <div class="support-qq" :class="{ compact }">
    <p v-if="!compact" class="support-title">{{ info.title || "QQ 客服" }}</p>
    <p class="support-hint">{{ info.hint }}</p>
    <div v-if="info.qq_qr_url" class="qr-wrap">
      <img :src="info.qq_qr_url" alt="QQ 客服二维码 — 扫一扫加好友" width="200" height="auto" loading="lazy" class="qr-img" />
    </div>
    <div v-if="info.qq" class="qq-row">
      <span class="qq-label">QQ号</span>
      <code class="qq-num">{{ info.qq }}</code>
      <el-button size="small" text type="primary" @click="copyQq">复制</el-button>
    </div>
    <a
      v-if="info.qq_chat_url"
      :href="info.qq_chat_url"
      target="_blank"
      rel="noopener noreferrer"
      class="chat-link"
    >
      打开 QQ 会话
    </a>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive } from "vue";
import { ElMessage } from "element-plus";
import api from "../utils/api";

defineProps<{ compact?: boolean }>();

const info = reactive({
  qq: import.meta.env.VITE_SUPPORT_QQ || "898382699",
  qq_chat_url: "",
  qq_qr_url: "",
  title: "QQ 客服",
  hint: "注册、授权码、套餐问题请联系 QQ 客服",
});

const DEFAULT_QR = "/support-qq.png";

function resolveQrUrl(url: string): string {
  if (!url) return DEFAULT_QR;
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return url.startsWith("/") ? url : `/${url}`;
}

function buildFallback() {
  const qq = info.qq;
  info.qq_chat_url = `https://wpa.qq.com/msgrd?v=3&uin=${qq}&site=qq&menu=yes`;
  info.qq_qr_url = resolveQrUrl(import.meta.env.VITE_SUPPORT_QQ_QR_URL || DEFAULT_QR);
}

async function load() {
  try {
    const res = await api.get("/public/support");
    const d = res.data?.data;
    if (d?.qq) {
      Object.assign(info, d);
      if (d.qq_qr_url) info.qq_qr_url = resolveQrUrl(d.qq_qr_url);
    } else {
      buildFallback();
    }
  } catch {
    buildFallback();
  }
}

async function copyQq() {
  try {
    await navigator.clipboard.writeText(info.qq);
    ElMessage.success("QQ 号已复制");
  } catch {
    ElMessage.info(`QQ：${info.qq}`);
  }
}

onMounted(load);
</script>

<style scoped>
.support-qq {
  text-align: center;
  padding: 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.support-qq.compact {
  padding: 12px;
}
.support-title {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}
.support-hint {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.65);
}
.qr-wrap {
  display: flex;
  justify-content: center;
}
.qr-img {
  max-width: 200px;
  width: 100%;
  height: auto;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}
.qq-row {
  margin-top: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}
.qq-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
}
.qq-num {
  font-size: 15px;
  color: #a5b4fc;
}
.chat-link {
  display: inline-block;
  margin-top: 10px;
  font-size: 13px;
  color: #818cf8;
  text-decoration: none;
}
.chat-link:hover {
  text-decoration: underline;
}
</style>
