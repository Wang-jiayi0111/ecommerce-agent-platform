# API 指南

基地址为 `/api/v1`，OpenAPI 文档为 `/docs`。

## 核心接口

- `POST /agent/tasks`：创建市场评估、商品策略、Listing 或运营诊断任务。
- `GET /agent/tasks/{id}`：查询状态、结果、审批和错误。
- `GET /agent/tasks/{id}/events`：SSE 事件流，客户端使用事件序号恢复游标。
- `POST /agent/tasks/{id}/cancel`：取消可中断任务。
- `POST /approvals/{id}/approve|reject`：处理人工审批。
- `GET /products`：商品查询契约。
- `GET /analytics/market|operations`：市场与经营指标契约。
- `POST /knowledge/search`：带引用的知识检索契约。

## 创建任务示例

```json
{
  "tenant_id": "tenant_001",
  "user_id": "operator_001",
  "user_query": "分析便携咖啡机在 US 市场是否值得进入",
  "intent": "market_entry",
  "business_context": { "market": "US", "category": "coffee_machine" },
  "constraints": { "minimum_margin": 0.3 },
  "priority": "HIGH"
}
```

所有真实请求必须从鉴权上下文取得 tenant/user，不接受客户端越权覆盖。当前本地基线保留请求字段以便独立演示。
