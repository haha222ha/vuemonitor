<template>
  <el-alert
    v-if="show"
    :type="alertType"
    :closable="closable"
    show-icon
    class="upgrade-banner"
    @close="dismissed = true"
  >
    <template #title>
      <span>{{ title }}</span>
    </template>
    <div class="upgrade-body">
      <p>{{ hint }}</p>
      <div class="upgrade-actions">
        <el-button v-if="shopUrl" type="primary" size="small" tag="a" :href="shopUrl" target="_blank" rel="noopener">
          前往小红书店铺续费
        </el-button>
        <el-button size="small" @click="$router.push('/activate')">已有新授权码，去激活</el-button>
      </div>
    </div>
  </el-alert>
</template>

<script setup lang="ts">
// AIGC START
import { computed, ref } from "vue"
import { useIntelAuthStore } from "@/stores/auth"
import { upgradeHint, upgradeTarget, XHS_SHOP_URL } from "@/utils/plan"

const props = withDefaults(
  defineProps<{
    force?: boolean
    closable?: boolean
  }>(),
  { force: false, closable: true },
)

const auth = useIntelAuthStore()
const dismissed = ref(false)

const shopUrl = XHS_SHOP_URL

const show = computed(() => {
  if (dismissed.value && !props.force) return false
  if (props.force) return true
  if (auth.daysRemaining <= 0) return true
  if (auth.planName === "weekly" && auth.daysRemaining <= 3) return true
  if (auth.planName === "monthly" && auth.daysRemaining <= 7) return true
  if (auth.planName === "yearly" && auth.daysRemaining <= 14) return true
  return upgradeTarget(auth.planName) !== null && auth.daysRemaining <= 7
})

const alertType = computed(() => (auth.daysRemaining <= 3 ? "error" : "warning"))

const title = computed(() => {
  if (auth.daysRemaining <= 0) return "会员已到期"
  if (auth.daysRemaining <= 7) return `会员剩余 ${auth.daysRemaining} 天`
  return "升级解锁更多情报"
})

const hint = computed(() => {
  if (auth.daysRemaining <= 0) {
    return "请在小红书店铺购买新授权码，登录后点击「激活授权码」即可续期。"
  }
  return upgradeHint(auth.planName)
})
// AIGC END
</script>

<style scoped>
.upgrade-banner {
  margin-bottom: 20px;
  border-radius: var(--radius-md, 8px);
}
.upgrade-body p {
  margin: 0 0 10px;
  font-size: 13px;
  line-height: 1.5;
}
.upgrade-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
