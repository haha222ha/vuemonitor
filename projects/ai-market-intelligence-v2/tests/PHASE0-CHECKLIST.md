# Phase 0～1 验收清单

## 文档

- [ ] `00-MASTER-SPEC.md` 已交付大模型阅读
- [ ] 15 份子文档索引清晰（`01-DOCUMENT-INDEX.md`）
- [ ] V1/V2 差异文档完整（`02-V1-V2-DIFF.md`）

## 合规（V2 报告）

- [ ] 样例 JSON 无 `goods_id` / `store_id` / 商品标题 / 店铺名
- [ ] 样例报告无商品链接、图片 URL
- [ ] 含固定 disclaimer 文案

## 隔离

- [ ] 未修改 `xhs-cloud/` 现网代码
- [ ] 未修改 PC ProductAnalyzer 源码
- [ ] 未向 `/opt/xhs-cloud` 部署实验代码

## 本地原型（Phase 1）

- [ ] 可打开本地 HTML 渲染 6 页情报报告
- [ ] 输入为 `samples/metrics-sample.json`
- [ ] 输出结构对齐 `samples/ai-report-sample.json`
- [ ] 与 V1 zip 报告并排对比截图存档

## 双轨

- [ ] 在期 V1 买家服务策略已写入 Master Spec §3
- [ ] 新 SKU 命名与权益已定义（§10）
