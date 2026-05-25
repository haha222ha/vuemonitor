<template>
  <div v-if="show" class="score-badge" :class="sizeClass" :style="ringStyle">
    <span class="score-num" :style="{ color: textColor }">{{ displayNum }}</span>
    <span v-if="showUnit" class="score-unit">分</span>
    <span v-if="label" class="score-tier">{{ label }}</span>
  </div>
</template>

<script setup lang="ts">
// AIGC START
import { computed } from "vue"
import {
  isDisplayableScore,
  getOpportunityScoreColor,
  getTrendScoreColor,
  opportunityScoreLabel,
} from "@/utils/score"

const props = withDefaults(
  defineProps<{
    score: unknown
    kind?: "opportunity" | "trend"
    size?: "sm" | "md" | "lg"
    showUnit?: boolean
    showTier?: boolean
  }>(),
  { kind: "opportunity", size: "md", showUnit: true, showTier: false },
)

const show = computed(() => isDisplayableScore(props.score))

const displayNum = computed(() => Math.round(Number(props.score)))

const textColor = computed(() =>
  props.kind === "trend"
    ? getTrendScoreColor(Number(props.score))
    : getOpportunityScoreColor(Number(props.score)),
)

const label = computed(() =>
  props.showTier && props.kind === "opportunity" ? opportunityScoreLabel(props.score) : "",
)

const ringStyle = computed(() => ({
  borderColor: textColor.value,
  boxShadow: `0 0 0 2px ${textColor.value}22`,
}))

const sizeClass = computed(() => `score-badge--${props.size}`)
// AIGC END
</script>

<style scoped>
.score-badge {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 2px solid;
  border-radius: 50%;
  background: #fff;
  flex-shrink: 0;
}
.score-badge--sm {
  width: 40px;
  height: 40px;
}
.score-badge--md {
  width: 52px;
  height: 52px;
}
.score-badge--lg {
  width: 64px;
  height: 64px;
}
.score-num {
  font-weight: 800;
  line-height: 1;
}
.score-badge--sm .score-num {
  font-size: 14px;
}
.score-badge--md .score-num {
  font-size: 18px;
}
.score-badge--lg .score-num {
  font-size: 22px;
}
.score-unit {
  font-size: 10px;
  color: #909399;
}
.score-tier {
  font-size: 9px;
  color: #606266;
  margin-top: 2px;
  white-space: nowrap;
}
</style>
