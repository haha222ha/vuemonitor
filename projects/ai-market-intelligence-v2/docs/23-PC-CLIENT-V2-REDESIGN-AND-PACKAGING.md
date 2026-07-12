# PC 端 V2 重设计与打包需求（ProductAnalyzer / XHS365 客户端）

> **版本**：v1.0 · **日期**：2026-07-12  
> **原则**：**Legacy 在期用户行为不变**；V2 新方案 **增量改造 + 权益门控**，不强制升级、不切断 zip 同步  
> **关联**：`09-PC-CLIENT-INTEGRATION.md`（接口细节）、`20-REQUIREMENTS-V2.2-ROLLOUT.md` §14、`19-LEGACY-SUNSET-AND-V2-LAUNCH.md`

---

## 1. 背景与隔离约束（必读）

| 约束 | 说明 |
|------|------|
| **现网会员 URL 不动** | `https://monitor.xhs365.cn/member` 仍是唯一入口 |
| **本月已付费 Legacy 用户** | 必须继续：报告库 zip 下载、PC 拉报告、收藏同步，直至 `expires_at` |
| **不改 Legacy API 契约** | `/api/v1/member/library`、`/download`、`/sync/report-upload` **保留** |
| **V2 新用户** | 默认 **情报只读**（读预生成库），**无** zip 批量导出、**无** plan_b 上传 |
| **发版隔离** | 旧安装包可继续用；新包通过 `profile.entitlements` 显隐菜单，**非**一刀切替换 |

---

## 2. PC 端产品矩阵（两个代码基座）

| 产品 | 代码路径 | 现网角色 | V2 方向 |
|------|----------|----------|---------|
| **ProductAnalyzer**（选品报告工具） | 独立仓库 `xhs_shelf_time/`；安装包 `XHS365-Setup-*.exe` | 拉 zip、本地看 data.js、同步收藏、plan_b 上传 | **主改造对象**：侧栏双轨 + WebView 情报 |
| **XHS365 客户端**（Electron） | `vuemonitor/client/` | SaaS 监控 / 发现 / AI 分析（`server/` API） | 与选品会员 **部分重叠**；情报入口可 WebView 嵌 `/member` 或调 insight API |

**本需求文档以 ProductAnalyzer + 会员中心联动为主**；Electron `client/` 的 V2 菜单改造列为 Phase 4（可选）。

---

## 3. 原有「同步官网选品报告」是否还要改？

**要改，但是「按权益分支」，不是全站下线。**

### 3.1 Legacy 链路（在期老会员 — **保持**）

```
PC ProductAnalyzer
  → GET /api/v1/member/library
  → GET /api/v1/member/reports/{date}/download
  → 本地解压 data.js + HTML 主题
  → POST /api/v1/sync/report-upload（plan_b，可选，维护期保留）
  → POST/GET /api/v1/member/watchlist（收藏，继续）
```

| 需求 ID | 需求 | 验收 |
|---------|------|------|
| REQ-PC-LEG-001 | `legacy_zip_enabled=true` 时 PC **仍显示**「选品数据报告」 | 与 Web 报告库 Tab 一致 |
| REQ-PC-LEG-002 | zip 下载 / 本地打开 **行为与现网一致** | 回归用例 T2 |
| REQ-PC-LEG-003 | plan_b `report-upload` **不删除** | Legacy 维护期可用 |
| REQ-PC-LEG-004 | 旧版 PC **不强制升级** | 最低版本门控仅拦安全漏洞，不拦 Legacy |

### 3.2 V2 链路（新会员 — **新增，替代 zip 为默认**）

```
PC ProductAnalyzer（V2 菜单）
  → GET /api/v1/member/profile（读 entitlements / portal_route）
  → GET /api/v1/member/insight/library
  → WebView / 系统浏览器 → .../insight/{date}/{category}/view?access_token=
  → **禁止**默认暴露「下载 data.js / 导出全量 CSV」
```

| 需求 ID | 需求 | 验收 |
|---------|------|------|
| REQ-PC-V2-001 | `insight_enabled=true` 时默认进入 **AI 市场情报** | 与 Web AI Tab 一致 |
| REQ-PC-V2-002 | `legacy_zip_enabled=false` 时 **隐藏** zip 下载、plan_b 上传入口 | 无 403 误触 |
| REQ-PC-V2-003 | 情报内容 **Cache-First**（读 PG/HTML，非实时 LLM） | 见 `22-INSIGHT-PRECOMPUTE-CACHE-DESIGN.md` |
| REQ-PC-V2-004 | 设备槽 `pc:{machine_id}` 与 Web `web:` 共存规则不变 | 与现网 auth 一致 |
| REQ-PC-V2-005 | 收藏 `/watchlist` **保留**（商品级，与 V2 类目关注并存） | 双轨不互删 |

### 3.3 老会员预览（双 Tab）

| 需求 ID | 需求 | 验收 |
|---------|------|------|
| REQ-PC-RT-001 | `legacy_with_preview`：侧栏 **Legacy + 情报** 双入口 | 同 Web 双 Tab |
| REQ-PC-RT-002 | 预览横幅文案与 Web 一致 | 8 月公告前不误导为已正式开通 |

---

## 4. 打包与发版重设计

### 4.1 安装包策略

| 项 | 现网 | V2 目标 |
|----|------|---------|
| 安装包名 | `XHS365-Setup-latest.exe` | 可增 **`XHS365-Insight-Setup-*.exe`** 或同包双模式 |
| 版本清单 | `deploy/downloads/productanalyzer-version.json` | 增加 `min_version_legacy` / `features: ["insight"]` |
| 会员页下载链 | `member_portal.html` → 安装包 URL | 文案区分「Legacy 全量报告工具」vs「AI 情报客户端」 |
| 自动更新 | electron-updater / 自建 | **Legacy 用户可跳过**；V2 用户提示升级 |

### 4.2 配置项（设置页 / local_sync.env）

```env
# 现网保留
XHS_CLOUD_BASE=https://monitor.xhs365.cn
XHS_CLOUD_REPORT_MODE=plan_b          # 仅 legacy_zip_enabled 时生效

# V2 新增
XHS_INSIGHT_ENABLED=auto              # auto=读 profile；1/0 强制
XHS_LEGACY_ZIP_ENABLED=auto           # auto=读 profile.legacy_zip_enabled
XHS_INSIGHT_WEBVIEW=1                 # 1=内嵌 WebView；0=系统浏览器
```

### 4.3 UI 信息架构（ProductAnalyzer）

```
侧栏
├── AI 市场情报          ← V2 默认（REQ-PC-V2-001）
├── 选品数据报告（Legacy） ← legacy_zip_enabled 时显示
├── 我的收藏             ← 保留
├── 设置 / 会员状态
└── （隐藏）plan_b 上传   ← 仅 Legacy + 维护开关
```

---

## 5. 与云端预生成（降本）的关系

**已写入需求体系**，不是 PC 独有能力：

| 文档 | 内容 |
|------|------|
| **`22-INSIGHT-PRECOMPUTE-CACHE-DESIGN.md`** | L0 夜间批量推理 → PG/HTML；L1 精确键缓存 |
| **`20-REQUIREMENTS-V2.2-ROLLOUT.md`** | REQ-CACHE-001～010 |
| 现网脚本 | `xhs-cloud/cloud_deploy/scripts/cloud_insight_report.py --playbook full` |

PC 端 **只读** 预生成结果，不在客户端触发 LLM 批量调用（除 Pro 配额内「用户自选冷门类目」Phase 3+）。

---

## 6. 开发阶段（PC 专项）

| 阶段 | 内容 | 触 Legacy 用户 | 状态 |
|------|------|----------------|------|
| **PC-0** | 需求与打包方案（本文档） | ❌ | ✅ |
| **PC-1** | `cloud_client` 增 `fetch_insight_library` + `insight_view_url` | ❌ | ⏳ |
| **PC-2** | 侧栏权益门控 + WebView 情报页 | ❌（仅新 entitlements 可见） | ⏳ |
| **PC-3** | 安装包重打包 + version.json + 会员页文案 | ⚠️ 可选下载新包 | ⏳ |
| **PC-4** | 隐藏 V2 用户的 plan_b / zip UI | ❌ 不影响 Legacy | ⏳ |
| **PC-5** | Electron `client/` 情报入口（可选） | ❌ | ⏳ |

---

## 7. 测试清单

| 用例 | 用户 | 期望 |
|------|------|------|
| PC-L1 | Legacy monthly 在期 | zip 下载、本地报告、上传、收藏正常 |
| PC-V1 | insight_pro 新码 | 只见情报列表，无 zip |
| PC-D1 | legacy_preview | 双菜单，Legacy 仍可用 |
| PC-U1 | 旧 PC + 新 V2 码 | 登录成功；若旧 UI 无情报菜单，提示升级（不 403 循环） |
| PC-C1 | 离线 | 情报页提示网络；Legacy 本地缓存报告仍可看 |

---

## 8. 明确不做（隔离期）

- ❌ 删除或改路径 Legacy download API  
- ❌ 强制 Legacy 用户升级 PC 才能续费  
- ❌ 在 PC 端默认开启实时 LLM 生成（违背降本）  
- ❌ 改动 `monitor.xhs365.cn/member` 登录/支付主流程（仅 Tab 显隐）

---

**维护**：PC-1 开工时同步更新 `09-PC-CLIENT-INTEGRATION.md` 代码片段与 `productanalyzer-version.json` 字段说明。
