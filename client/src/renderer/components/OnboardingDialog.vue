<template>
  <Teleport to="body">
    <transition name="onboarding">
      <div v-if="visible" class="onboarding-overlay">
        <div class="onboarding">
          <button class="onboarding__close" @click="$emit('close')">
            <el-icon :size="18"><Close /></el-icon>
          </button>

          <div class="onboarding__content">
            <div class="onboarding__illustration">
              <div class="onboarding__illustration-icon">
                <el-icon :size="64">
                  <component :is="currentStep.icon" />
                </el-icon>
              </div>
            </div>

            <div class="onboarding__text">
              <h3 class="onboarding__title">{{ currentStep.title }}</h3>
              <p class="onboarding__desc">{{ currentStep.description }}</p>
            </div>

            <div class="onboarding__footer">
              <div class="onboarding__dots">
                <span
                  v-for="(_, i) in steps"
                  :key="i"
                  :class="['onboarding__dot', { 'onboarding__dot--active': current === i }]"
                  @click="current = i"
                />
              </div>
              <div class="onboarding__actions">
                <el-button v-if="current > 0" @click="current--">
                  上一步
                </el-button>
                <el-button
                  v-if="current < steps.length - 1"
                  type="primary"
                  @click="current++"
                >
                  下一步
                </el-button>
                <el-button
                  v-else
                  type="primary"
                  @click="finish"
                >
                  开始使用
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { Close, Search, DataAnalysis, MagicStick } from "@element-plus/icons-vue";

const props = defineProps<{ visible: boolean }>();
const emit = defineEmits<{ close: [] }>();

const router = useRouter();
const current = ref(0);

const steps = [
  {
    icon: Search,
    title: "发现商品",
    description: "通过商品发现功能，搜索你感兴趣的商品或店铺。支持按标题、店铺名称搜索，快速找到目标商品。",
  },
  {
    icon: DataAnalysis,
    title: "监控数据",
    description: "添加商品后，系统会自动采集价格、销量、排名等数据。你可以在工作台实时查看商品动态和趋势变化。",
  },
  {
    icon: MagicStick,
    title: "AI 决策",
    description: "利用 AI 分析商品趋势，获取爆品预测、风险预警等智能洞察，帮助你做出更明智的商业决策。",
  },
];

const currentStep = computed(() => steps[current.value]);

function finish() {
  try {
    localStorage.setItem("onboarding-completed", "true");
  } catch {}
  emit("close");
}
</script>

<style scoped>
.onboarding-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(6px);
}

.onboarding {
  position: relative;
  width: 520px;
  background: var(--color-bg-card);
  border-radius: var(--radius-2xl);
  box-shadow: var(--shadow-xl);
  border: 1px solid var(--color-border-light);
  overflow: hidden;
}

.onboarding__close {
  position: absolute;
  top: var(--space-base);
  right: var(--space-base);
  width: 32px;
  height: 32px;
  border: none;
  background: var(--color-bg-page);
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--color-text-secondary);
  transition: all var(--duration-fast) var(--ease-out);
  z-index: 1;
}

.onboarding__close:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  transform: scale(1.1);
}

.onboarding__content {
  padding: var(--space-3xl) var(--space-xl) var(--space-xl);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.onboarding__illustration {
  margin-bottom: var(--space-xl);
}

.onboarding__illustration-icon {
  width: 120px;
  height: 120px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  border-radius: var(--radius-2xl);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: var(--shadow-lg);
}

.onboarding__text {
  margin-bottom: var(--space-xl);
}

.onboarding__title {
  margin: 0 0 var(--space-sm);
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-text-primary);
}

.onboarding__desc {
  margin: 0;
  font-size: var(--text-base);
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.onboarding__footer {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-base);
}

.onboarding__dots {
  display: flex;
  gap: var(--space-sm);
}

.onboarding__dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--color-border);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.onboarding__dot--active {
  width: 24px;
  background: var(--color-primary);
}

.onboarding__actions {
  display: flex;
  gap: var(--space-sm);
}

.onboarding-enter-active {
  transition: opacity 0.3s ease;
}

.onboarding-leave-active {
  transition: opacity 0.2s ease;
}

.onboarding-enter-from,
.onboarding-leave-to {
  opacity: 0;
}

.onboarding-enter-active .onboarding {
  animation: onboardingIn 0.4s var(--ease-bounce);
}

@keyframes onboardingIn {
  from {
    transform: scale(0.9) translateY(20px);
    opacity: 0;
  }
  to {
    transform: scale(1) translateY(0);
    opacity: 1;
  }
}

@media (max-width: 640px) {
  .onboarding {
    width: calc(100vw - var(--space-xl));
    margin: 0 var(--space-base);
  }

  .onboarding__illustration-icon {
    width: 96px;
    height: 96px;
  }

  .onboarding__title {
    font-size: var(--text-xl);
  }
}
</style>
