<template>
  <el-dialog
    v-model="visible"
    title="欢迎使用副业财富情报"
    width="480px"
    :close-on-click-modal="false"
    class="onboarding-dialog"
    @closed="markDone"
  >
    <div class="onboarding-steps">
      <div class="step" :class="{ active: step === 0 }">
        <span class="step-num">1</span>
        <div>
          <strong>授权码已生效</strong>
          <p>当前套餐：<el-tag size="small">{{ currentPlanLabel }}</el-tag>，剩余 {{ daysRemaining }} 天</p>
        </div>
      </div>
      <div class="step" :class="{ active: step === 1 }">
        <span class="step-num">2</span>
        <div>
          <strong>先看今日简报</strong>
          <p>仪表盘顶部汇总今日最强信号、风险与行动建议</p>
        </div>
      </div>
      <div class="step" :class="{ active: step === 2 }">
        <span class="step-num">3</span>
        <div>
          <strong>打开决策报告</strong>
          <p>在「决策报告」查看本周完整 HTML 周报（7天精选含最新 1 份）</p>
        </div>
      </div>
    </div>
    <template #footer>
      <el-button v-if="step > 0" @click="step--">上一步</el-button>
      <el-button v-if="step < 2" type="primary" @click="step++">下一步</el-button>
      <el-button v-else type="primary" @click="finish">开始查看</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
// AIGC START
import { ref, onMounted } from "vue"
import { useRouter } from "vue-router"
import { useIntelAuthStore } from "@/stores/auth"
import { planLabel as getPlanLabel } from "@/utils/plan"

const ONBOARDING_KEY = "intel_onboarding_v1_done"

const router = useRouter()
const auth = useIntelAuthStore()
const visible = ref(false)
const step = ref(0)

const currentPlanLabel = getPlanLabel(auth.planName)
const daysRemaining = auth.daysRemaining

onMounted(async () => {
  if (localStorage.getItem(ONBOARDING_KEY)) return
  if (!auth.membership) await auth.fetchMembership()
  if (auth.hasMembership) visible.value = true
})

function markDone() {
  localStorage.setItem(ONBOARDING_KEY, "1")
}

function finish() {
  visible.value = false
  markDone()
  router.push("/dashboard")
}
// AIGC END
</script>

<style scoped>
.onboarding-steps {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.step {
  display: flex;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  background: #f8f9fa;
  opacity: 0.65;
  transition: opacity 0.2s;
}
.step.active {
  opacity: 1;
  background: #ecf5ff;
  border: 1px solid #d9ecff;
}
.step-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  flex-shrink: 0;
}
.step p {
  margin: 4px 0 0;
  font-size: 13px;
  color: #606266;
}
</style>
