# 本地 Web 原型（Phase 1～2.2 Lab）

> 验证 V2 架构与上线路由，**不连接现网**。需求见 `docs/20-REQUIREMENTS-V2.2-ROLLOUT.md`。

## 入口

| 页面 | 用途 |
|------|------|
| **`insight_portal.html`** | **新会员默认门户**（无 Legacy Tab） |
| `member-demo.html` | 双轨对照（Legacy + AI 情报） |
| `compare.html` / `timeline.html` / … | 进阶功能 |

## 启动

```bash
cd projects/ai-market-intelligence-v2
python local-web-prototype/server.py
```

浏览器：

- http://127.0.0.1:8765/insight_portal.html
- http://127.0.0.1:8765/member/insight（同门户）
- http://127.0.0.1:8765/member-demo.html（双轨对照）

## 实验室分群（persona）

门户顶栏可切换三种演示账号，对应 `GET /api/v1/member/profile`：

- **新会员 · V2 Pro** → `portal_route: insight_only`
- **老会员 · V2 预览** → `legacy_with_preview` + 预览横幅
- **老会员 · 仅 Legacy** → 访问 V2 门户会跳转双轨对照页

## API 要点

- `GET /api/v1/member/profile` — 路由 + 权益 + LLM 日用量
- `POST /api/v1/lab/persona` — 切换演示分群
- `POST /api/v1/insight/report/generate` — 权益 + 配额 + LLM 预算门控
