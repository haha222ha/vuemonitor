<template>
  <LegalDoc title="服务条款" :sections="sections" />
</template>

<script setup lang="ts">
import LegalDoc from "../components/LegalDoc.vue";

const sections = [
  {
    title: "1. 服务说明",
    body: "XHS365（以下简称「本服务」）提供小红书相关商品监控、数据分析与 AI 辅助决策工具。使用本服务即表示您同意本条款。",
  },
  {
    title: "2. 账户与授权",
    body: "您应使用真实信息注册并妥善保管账户。付费套餐通过授权码激活；授权码一经使用，除法律规定或客服协商外不予退换。",
  },
  {
    title: "3. 合规使用",
    body: "您应遵守小红书平台规则及适用法律法规。不得将本服务用于爬取未授权数据、骚扰、欺诈或其他违法用途。",
  },
  {
    title: "4. 数据与隐私",
    body: "我们如何处理数据见《隐私政策》。您对自己导入或采集的数据负有合法来源责任。",
  },
  {
    title: "5. 免责声明",
    body: "AI 分析结果仅供参考，不构成投资或经营承诺。因平台规则变化、网络中断等导致的损失，我们在法律允许范围内不承担责任。",
  },
  {
    title: "6. 联系",
    body: "如有疑问，请通过网站 QQ 客服与我们联系。",
  },
];
</script>
