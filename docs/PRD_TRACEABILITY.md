# 需求追踪矩阵

| 需求 | 当前落点 | 状态 |
| --- | --- | --- |
| FR-001 创建四类任务 | `POST /api/v1/agent/tasks`、Supervisor 路由 | 基线可运行 |
| FR-002 追加上下文 | AgentState 已预留 constraints/business_context | 待持久化版本 API |
| FR-003 流式进度 | `GET /agent/tasks/{id}/events` SSE | 快照流；待异步增量 |
| FR-004 事实/推断/建议 | `AgentResult` 分栏 + `EvidenceRef` | 基线可运行 |
| FR-010 任务中心 | Web 任务列表、筛选 API 参数 | 基线可运行 |
| FR-011 节点 Trace | 事件与数据库 `agent_step/tool_call` 骨架 | 待 OpenTelemetry |
| FR-012 恢复 | `state/`、retry/degraded 状态 | 待 Redis Checkpoint |
| FR-013 取消 | `POST /agent/tasks/{id}/cancel` | 基线可运行 |
| FR-020~024 市场评估 | market Agent、analytics API、Tool 契约 | 演示数据；待授权 Adapter |
| FR-030~033 商品/Listing | product/listing Agent、审批 | 结构基线；待规则 Tool |
| FR-040~043 运营诊断 | operations Agent、analytics API | 结构基线；待统计服务 |
| FR-050~052 知识与配置 | knowledge API、RAG 目录 | 契约已建 |
| AC-04 审批写入 | WAITING_APPROVAL、SHA-256 快照 | 自动测试覆盖 |
| Tool 确定性计算 | ProfitCalculator | 自动测试覆盖 |
| Docker Compose | web/api/worker/scheduler/核心依赖 | 已配置 |
