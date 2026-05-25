<template>
  <LegalDoc title="隐私政策" :sections="sections" />
</template>

<script setup lang="ts">
import LegalDoc from "../components/LegalDoc.vue";

const sections = [
  {
    title: "1. 收集的信息",
    body: "我们可能收集：账户信息（用户名、可选邮箱）、您添加的商品与监控配置、使用日志及设备信息（用于安全与排错）。",
  },
  {
    title: "2. 使用目的",
    body: "用于提供与改进服务、授权校验、客户支持及安全防护。我们不会出售您的个人信息。",
  },
  {
    title: "3. 存储与安全",
    body: "数据存储在受控服务器，采用访问控制与加密传输（HTTPS）。您可在设置中管理账户并申请停用。",
  },
  {
    title: "4. 第三方",
    body: "AI 能力可能调用第三方 API（如 DeepSeek），仅传输分析所需的最小数据。",
  },
  {
    title: "5. 您的权利",
    body: "您可申请导出或删除账户相关数据（见产品内 GDPR 功能或联系客服）。",
  },
  {
    title: "6. 更新",
    body: "我们可能更新本政策，重大变更将在网站公示。继续使用即视为接受更新后的政策。",
  },
];
</script>
