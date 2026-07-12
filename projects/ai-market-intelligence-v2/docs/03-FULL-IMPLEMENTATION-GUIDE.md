# 完整实施指南：框架 · 代码 · 远程升级 · PC 对接

> **版本** v0.2 | **路径** `projects/ai-market-intelligence-v2/docs/03-FULL-IMPLEMENTATION-GUIDE.md`

---

## 一、总览：三端一体

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户触达面                                 │
├──────────────────────┬──────────────────────┬───────────────────┤
│ 会员 Web 报告中心     │  PC ProductAnalyzer   │  Admin 后台        │
│ monitor.xhs365.cn    │  xhs_shelf_time       │  admin.xhs365.cn  │
└──────────┬───────────┴──────────┬───────────┴─────────┬─────────┘
           │                      │                     │
           └──────────────────────┼─────────────────────┘
                                  ▼
                    ┌─────────────────────────┐
                    │  xhs-cloud FastAPI :8080 │
                    │  /opt/xhs-cloud          │
                    └────────────┬────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
  V1 Legacy 管道          V2 Insight 管道           共享 PG
  cloud_gen_report        cloud_insight_report      xhs_monitor.*
  member_daily_zip        insight_daily_html
```

**实验室**（现在）：`projects/ai-market-intelligence-v2/` 全部在此验证。  
**生产**（Phase 2+）：把验证通过的模块 **复制合并** 进 `xhs-cloud/cloud_deploy/`。

---

## 二、六层 → 代码模块映射

| 层 | 职责 | 实验室代码 | 合并到 xhs-cloud 目标 |
|----|------|------------|----------------------|
| L1 采集 | 用户授权浏览公开页 | —（PC 现有） | 不改采集逻辑 |
| L2 原材料 | PG 快照 | `07-DATABASE-SCHEMA-V2.sql` | `database_pg.py` 只读内部 |
| L3 标准化 | 原始→指标 | `services/metric_engine.py` | `reporting/insight_metrics.py` |
| L4 指数 | 热度/蓝海等 | 同上 | 同上 |
| L5 AI | 多 Agent | `services/ai_orchestrator.py` | `reporting/insight_ai.py` |
| L6 报告 | HTML 情报 | `services/report_builder.py` | `assets/insight_report.html` |

---

## 三、实验室已有可运行代码

### 3.1 命令行管道

```powershell
cd E:\vuemonitor\projects\ai-market-intelligence-v2
pip install -r requirements-lab.txt
python scripts/run_insight_pipeline.py --date 2026-07-12
# 输出: output/情报20260712_小学教辅/index.html
```

### 3.2 本地 Web + API

```powershell
cd E:\vuemonitor\projects\ai-market-intelligence-v2\local-web-prototype
python server.py
# 浏览器 http://127.0.0.1:8765
```

流程：选类目 → 生成 AI 情报 → iframe 预览（无 goods_id）。

### 3.3 目录清单

```
ai-market-intelligence-v2/
├── services/           # 核心算法（合并源）
├── scripts/            # CLI 管道
├── local-web-prototype/# Web 验证
├── cloud-stubs/        # 合并 xhs-cloud 的参考补丁
├── samples/            # JSON 样例
└── docs/               # 全套设计文档
```

---

## 四、远程会员报告中心升级（分阶段）

详见 `08-REMOTE-UPGRADE-RUNBOOK.md`。摘要：

| Phase | 动作 | 用户可见 |
|-------|------|----------|
| 2a | PG 执行 `07-DATABASE-SCHEMA-V2.sql` | 无 |
| 2b | 新增 `cloud_insight_report.py` timer（Shadow，不发布） | 无 |
| 2c | `main.py` 增加 `/api/v1/member/insight/*` | 无（未挂 UI） |
| 3 | `member_portal.html` 增加「AI 情报」Tab；Legacy Tab 保留 | 双轨 |
| 4 | 新 SKU 只卖 V2；Legacy 到期下线 zip | V2 为主 |

**关键**：`_MEMBER_ARCHIVE_TYPES` 增加 `insight_daily_html`；**不删除** `member_daily_zip`。

---

## 五、PC 端对接

详见 `09-PC-CLIENT-INTEGRATION.md`。摘要：

| 功能 | V1 | V2 |
|------|----|----|
| 登录 | 同 API，`pc:` device_id | 不变 |
| 报告列表 | `/member/library` daily | + `/member/insight/library` |
| 打开报告 | 下载 zip / 本地解压 | WebView 打开 `insight/.../view` |
| 上传本地报告 | plan_b `report-upload` | **逐步废弃**（仅 Legacy 维护期） |
| 定位 | 监控助手 | **AI 市场研究助手** |

PC 改动在 **`xhs_shelf_time`** 仓库，Phase 3 与云端 API 同步发版。

---

## 六、双轨会员权益

```json
{
  "plan_code": "legacy_daily_zip",
  "allowed_archive_types": ["member_daily_zip", "member_weekly_zip"],
  "report_download_limited": false
}
```

```json
{
  "plan_code": "insight_pro",
  "allowed_archive_types": ["insight_daily_html"],
  "report_download_limited": true,
  "insight_pdf": true
}
```

实现位置：`auth_codes.note` JSON + `get_member_entitlements()` + `member_can_download_report()`。

---

## 七、合并 xhs-cloud 的文件清单（Phase 2 参考）

| 新增/修改 | 源（实验室） | 目标（生产） |
|-----------|--------------|--------------|
| 指标引擎 | `services/metric_engine.py` | `cloud_deploy/reporting/insight_metrics.py` |
| AI 编排 | `services/ai_orchestrator.py` | `cloud_deploy/reporting/insight_ai.py` |
| HTML 渲染 | `services/report_builder.py` | `cloud_deploy/reporting/insight_builder.py` |
| 日报生成 | `cloud-stubs/cloud_insight_report.py` | `cloud_deploy/scripts/cloud_insight_report.py` |
| API 路由 | `cloud-stubs/insight_routes.py` | 合并进 `cloud_api/main.py` |
| 常量 | `cloud-stubs/insight_constants.py` | `reporting/constants.py` 追加 |
| 会员 UI | `cloud-stubs/member_insight_panel.html` | 合并进 `member_portal.html` |
| systemd | `cloud-stubs/xhs-insight-report.service` | `cloud_deploy/systemd/` |

---

## 八、验收标准（上线前）

- [ ] 情报 HTML View Source 无 `goods_id` / `store_name` / `REPORT_DATA`
- [ ] Legacy 买家仍可下载 V1 zip
- [ ] V2 买家只能看情报 Tab
- [ ] PC WebView 可打开情报 URL
- [ ] Shadow 管道 7 天对照 V1 类目趋势一致性
- [ ] AI Prompt 审计通过（无禁用字段）

---

## 九、推荐阅读顺序

1. `00-MASTER-SPEC.md` — 战略与合规  
2. **本文** — 实施总览  
3. `06-API-SPEC-V2.md` — 接口  
4. `07-DATABASE-SCHEMA-V2.sql` — 库表  
5. `08-REMOTE-UPGRADE-RUNBOOK.md` — 云主机步骤  
6. `09-PC-CLIENT-INTEGRATION.md` — PC 改造  
7. 运行本地 `server.py` 亲手点一遍  

---

## 十、下一步建议（按优先级）

1. **本周**：本地跑通实验室 Web + pipeline  
2. **下周**：Shadow `cloud_insight_report` 在服务器生成但不发布  
3. **在期买家减少后**：会员页双 Tab + 新 SKU  
4. **PC**：只读情报 WebView，隐藏 zip 批量下载（V2 用户）
