# XHS365 客户端UI重构 - Phase 1 实现指南 (v2.0)

> 基于 `docs/产品设计重构方案.md` V2.0
> **状态: Phase 1 核心组件已完成开发**

---

## 已完成的组件

### ✅ Phase 1 核心组件 (已创建并通过类型检查)

| 组件 | 文件位置 | 状态 |
|------|----------|------|
| OpportunityRadarStats | [OpportunityRadarStats.vue](file:///d:/vuemonitor/web-user/src/components/OpportunityRadarStats.vue) | ✅ 完成 |
| OpportunityCard | [OpportunityCard.vue](file:///d:/vuemonitor/web-user/src/components/OpportunityCard.vue) | ✅ 完成 |
| AlertEventCard | [AlertEventCard.vue](file:///d:/vuemonitor/web-user/src/components/AlertEventCard.vue) | ✅ 完成 |
| CategoryHeatmap | [CategoryHeatmap.vue](file:///d:/vuemonitor/web-user/src/components/CategoryHeatmap.vue) | ✅ 完成 |
| DashboardHome 集成 | [DashboardHome.vue](file:///d:/vuemonitor/web-user/src/views/dashboard/DashboardHome.vue) | ✅ 完成 |
| 离线降级逻辑 | [useDashboardData.ts](file:///d:/vuemonitor/web-user/src/composables/useDashboardData.ts) | ✅ 完成 |

---

## 组件功能概览

### 1. OpportunityRadarStats - 商业指标统计卡片

**功能:**
- 机会商品数（排名前30%）
- 今日趋势（上涨/下跌数量）
- 异动提醒（待确认数量）
- AI洞察（今日分析次数）

**交互:**
- 点击卡片可导航到对应页面
- 数字动画效果
- 悬停状态反馈

### 2. OpportunityCard - 今日机会榜

**功能:**
- 显示排名前30%的商品
- 商品排名徽章（前3名金色）
- 趋势方向指示（↑/↓）
- 生命周期阶段标签
- 商品缩略图和平台标识

**交互:**
- 点击商品卡片跳转商品详情
- 悬停高亮效果
- 空状态友好提示

### 3. AlertEventCard - 异动监控

**功能:**
- 按严重程度分级显示
- 确认/未确认状态区分
- 时间相对显示（分钟前/小时前）
- 加载更多分页

**交互:**
- 点击确认按钮标记已处理
- 点击商品卡片跳转详情
- 严重程度颜色编码

### 4. CategoryHeatmap - 品类热力图

**功能:**
- 三种视图：热力图 / 趋势曲线 / 行为模式
- 热度颜色渐变（绿→黄→红）
- 品类选择高亮
- 模拟数据降级

**交互:**
- 点击品类查看详情
- Tab切换不同视图
- 悬停显示更多信息

### 5. useDashboardData - 离线降级逻辑

**功能:**
- 检测网络在线/离线状态
- LocalStorage缓存
- API调用失败时使用本地数据
- 自动降级策略

---

## API 调用清单

| API | 用途 | 组件 |
|-----|------|------|
| `GET /dashboard/stats` | 仪表盘统计 | DashboardHome |
| `GET /feature/product-rankings` | 机会商品排名 | OpportunityCard, DashboardHome |
| `GET /alert-rules/events/all` | 异动告警列表 | AlertEventCard, DashboardHome |
| `GET /feature/crowd/category-heatmap` | 品类热力图 | CategoryHeatmap |
| `GET /feature/crowd/trend-timeseries` | 趋势时间序列 | CategoryHeatmap |
| `GET /feature/crowd/behavior-patterns` | 行为模式 | CategoryHeatmap |

---

## 验证结果

```
✅ npx vue-tsc --noEmit: All checks passed!
✅ TypeScript 类型检查全部通过
✅ 组件成功导入和使用
```

---

## 实施检查清单

- [x] 创建 `OpportunityRadarStats.vue` 组件
- [x] 创建 `OpportunityCard.vue` 组件
- [x] 创建 `AlertEventCard.vue` 组件
- [x] 创建 `CategoryHeatmap.vue` 组件
- [x] 更新 `DashboardHome.vue` 使用新组件
- [x] 添加离线降级逻辑
- [x] 类型检查通过

---

## 下一步开发建议

### Phase 2: 导航重构
- 重命名侧边栏菜单项
- 添加图标和徽章
- 实现路由守卫

### Phase 3: 商品页增强
- 添加排名百分位展示
- 实现竞品对比功能
- 添加AI分析入口

### Phase 4: AI页优化
- 快速分析工具
- 分析报告生成
- 选品建议推荐

### Phase 5: 通知中心
- 实时通知推送
- 通知分组和筛选
- 通知设置管理

---

## 组件复用指南

### 在其他页面使用新组件

```vue
<template>
  <div>
    <OpportunityCard />
    <AlertEventCard style="margin-top: 20px;" />
  </div>
</template>

<script setup lang="ts">
import OpportunityCard from '@/components/OpportunityCard.vue'
import AlertEventCard from '@/components/AlertEventCard.vue'
</script>
```

### 使用离线降级逻辑

```vue
<script setup lang="ts">
import { useDashboardData } from '@/composables/useDashboardData'

const { isOnline, loadOpportunityRankings, loadAlertEvents } = useDashboardData()

const opportunities = await loadOpportunityRankings()
const alerts = await loadAlertEvents()
</script>
```
