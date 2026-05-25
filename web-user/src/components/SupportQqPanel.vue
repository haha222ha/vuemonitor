<template>
  <div class="support-qq" :class="{ compact }">
    <p v-if="!compact" class="support-title">{{ info.title || "QQ 客服" }}</p>
    <p class="support-hint">{{ info.hint }}</p>
    <div v-if="info.qq_qr_url" class="qr-wrap">
      <div class="qr-hover" tabindex="0" aria-label="悬停查看 QQ 二维码大图">
        <img
          :src="info.qq_qr_url"
          alt="QQ 客服"
          loading="lazy"
          class="qr-thumb"
        />
        <div class="qr-pop">
          <img :src="info.qq_qr_url" alt="QQ 客服二维码 — 扫一扫加好友" class="qr-pop-img" />
          <span class="qr-pop-tip">扫一扫加我为好友</span>
        </div>
      </div>
      <p class="qr-hover-hint">悬停查看大图</p>
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
  padding: 8px 10px;
}
.support-qq.compact .support-hint {
  margin-bottom: 6px;
  font-size: 12px;
}
.support-qq.compact .qr-hover-hint {
  font-size: 10px;
}
.support-qq.compact .qq-row {
  margin-top: 6px;
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
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.qr-hover-hint {
  margin: 0;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.45);
}
.qr-hover {
  position: relative;
  display: inline-block;
  cursor: pointer;
  outline: none;
}
.qr-thumb {
  display: block;
  width: 36px;
  height: auto;
  border-radius: 6px;
  background: #fff;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.1);
  transition: transform 0.15s ease;
}
.support-qq.compact .qr-thumb {
  width: 28px;
}
.qr-hover:hover .qr-thumb,
.qr-hover:focus-visible .qr-thumb {
  transform: scale(1.03);
}
.qr-pop {
  pointer-events: none;
  position: absolute;
  z-index: 100;
  bottom: calc(100% + 10px);
  left: 50%;
  transform: translateX(-50%) scale(0.96);
  padding: 10px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.28);
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.2s ease, visibility 0.2s ease, transform 0.2s ease;
}
.qr-pop::after {
  content: "";
  position: absolute;
  top: 100%;
  left: 50%;
  margin-left: -6px;
  border: 6px solid transparent;
  border-top-color: #fff;
}
.qr-pop-img {
  display: block;
  width: 160px;
  max-width: min(160px, 65vw);
  height: auto;
  border-radius: 6px;
}
.qr-pop-tip {
  display: block;
  margin-top: 8px;
  font-size: 12px;
  color: #666;
  text-align: center;
}
.qr-hover:hover .qr-pop,
.qr-hover:focus-visible .qr-pop,
.qr-hover:focus-within .qr-pop {
  opacity: 1;
  visibility: visible;
  transform: translateX(-50%) scale(1);
}
.support-qq.compact .qr-pop {
  bottom: auto;
  top: calc(100% + 10px);
}
.support-qq.compact .qr-pop::after {
  top: auto;
  bottom: 100%;
  border-top-color: transparent;
  border-bottom-color: #fff;
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
