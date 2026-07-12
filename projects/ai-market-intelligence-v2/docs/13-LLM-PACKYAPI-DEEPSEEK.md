# PackyAPI + DeepSeek V4 Flash 接入指南

> **版本**：v1.0  
> **适用**：V2 实验室 `services/llm_client.py`、主仓库 `server/app/ai/providers.py`  
> **官方文档**：[DS接入CC | PackyAPI](https://docs.packyapi.com/docs/advanced/DeepSeekClaudeCode.html)

---

## 1. 为什么选择这套组合

| 项 | 说明 |
|----|------|
| 模型 | **deepseek-v4-flash** — 低延迟、适合多 Agent 并行 JSON 任务 |
| 中继 | **PackyAPI** — 与现网 `DeepSeekProvider` 一致，OpenAI 兼容 |
| 合规 | 类目级指标脱敏后出站；仍须在隐私政策中披露 LLM 供应商 |

---

## 2. PackyAPI 令牌创建

1. 登录 [PackyAPI](https://www.packyapi.com)
2. 创建 API 令牌
3. **名称**：如 `deepseek-officially`
4. **令牌分组**：必须选 **`deepseek-officially`**
5. 复制 Key → 写入 `.env`

---

## 3. 实验室 `.env` 配置

```bash
INSIGHT_LLM_PROVIDER=packy_deepseek
INSIGHT_LLM_API_KEY=sk-xxx
INSIGHT_LLM_BASE_URL=https://www.packyapi.com/v1
INSIGHT_LLM_MODEL=deepseek-v4-flash
INSIGHT_LLM_THINKING=disabled
INSIGHT_LLM_FALLBACK_MOCK=1
```

与主仓库对齐时，也可只设 `DEEPSEEK_API_KEY`（`llm_client` 会自动读取）。

---

## 4. 模型选型建议（5 Agent）

| Agent | 推荐模型 | 说明 |
|-------|----------|------|
| market / data / risk | `deepseek-v4-flash` | 并行 3 路，追求吞吐 |
| ops | `deepseek-v4-flash` | 结构化 action_plan |
| ceo | `deepseek-v4-flash` 或 `deepseek-v4-pro` | 摘要质量要求高时用 pro |

在 `config/llm_profiles.yaml` 或环境变量中配置：

```bash
INSIGHT_LLM_MODEL_CEO=deepseek-v4-pro
```

### 1M 上下文（一般不需要）

PackyAPI 文档：仅在需要 1m 上下文时使用 `[1m]` 后缀：

- `deepseek-v4-flash[1m]`
- `deepseek-v4-pro[1m]`

V2 输入仅为类目 JSON（<2KB），**无需** 1m 后缀。

---

## 5. DeepSeek V4 thinking 模式

V4 默认 **thinking 开启**。多 Agent JSON 输出建议 **关闭** 以降低成本和延迟：

```bash
INSIGHT_LLM_THINKING=disabled
```

代码会在 payload 中注入 `"thinking": {"type": "disabled"}`。

---

## 6. 验证连通性

```powershell
cd E:\vuemonitor\projects\ai-market-intelligence-v2
copy .env.example .env
# 编辑 .env 填入 Key
python scripts/test_llm_connection.py
```

成功输出示例：

```json
{"status": "ok", "model_working": true}
```

---

## 7. 与 Claude Code 配置的区别

| 场景 | Base URL | API 格式 | 模型 |
|------|----------|----------|------|
| Claude Code（Packy 文档） | `https://www.packyapi.com` | Anthropic Messages | deepseek-v4-flash |
| **V2 实验室 / FastAPI** | `https://www.packyapi.com/v1` | **OpenAI Chat Completions** | deepseek-v4-flash |

V2 使用 OpenAI 兼容端点 `/v1/chat/completions`，与主仓库 `DeepSeekProvider` 一致，**不要**混用 Anthropic 格式。

---

## 8. 故障排查

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| HTTP 401 | Key 错误或分组不对 | 确认 `deepseek-officially` 分组 |
| HTTP 404 model | 模型名拼写 | 使用 `deepseek-v4-flash` |
| 返回非 JSON | thinking 或格式问题 | 设 `INSIGHT_LLM_THINKING=disabled` |
| SSL / 网络 | 本地网络 | 检查防火墙；PackyAPI 状态 |
| 自动 mock | 无 Key 或 FALLBACK=1 | 检查 `.env` 是否加载 |

---

## 9. 成本估算（参考）

单次报告 5 Agent × ~500 token ≈ 2500 token 级。flash 单价低，适合日更。生产建议：

- 记录 `llm_usage`（已在 `agent_graph` 状态机中）
- 设日预算熔断（Phase 2：`REQ-AI-003`）

---

## 10. 合规提示

- 隐私政策模板中填写：**PackyAPI / DeepSeek** 为推理供应商
- 仅发送 **类目级脱敏指标**，禁止 goods_id / store_name
- 第三方中继可用性须在运维 SLA 中评估（主仓库需求文档 Q-7）

---

**关联代码**：`services/llm_client.py`、`config/llm_profiles.yaml`、`server/app/ai/providers.py`
