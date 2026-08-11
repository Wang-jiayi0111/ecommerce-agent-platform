# 项目框架

## 1. 参考与边界

工程治理沿用酒店项目的模块化单体、独立 Worker、统一仓储/服务/Adapter 分层、审批哈希和 CI。业务能力按电商需求重新映射，不保留酒店的房价、房态、渠道或收益管理模型。

## 2. 运行架构

```text
Web / Mobile Ops
       |
FastAPI /api/v1
       |
Task Service ---- PostgreSQL (业务、任务、审计)
       |
LangGraph Supervisor -> 4 Business Agents -> Judge
       |                         |
Tool / Adapter / RAG -------- Redis Checkpoint
       |
授权平台 API / 企业数据 / Qdrant / MinIO
```

一期部署为 `web + api + agent-worker + scheduler + db + redis + qdrant + minio`。Agent 不直接访问数据库或外部写接口。

## 3. Agent 最小责任边界

| 组件 | 负责 | 不负责 |
| --- | --- | --- |
| Supervisor | 意图、约束、计划、路由、汇总 | 业务计算、查库、写业务对象 |
| 市场情报 Agent | 市场/竞品/评论证据综合 | 补造缺失数据 |
| 商品策略 Agent | 定位、价格、卖点、差异化、风险 | 直接保存商品方案 |
| Listing Agent | 结构化文案生成 | 绕过事实与平台规则校验 |
| 运营诊断 Agent | 异常解释、证据等级、建议 | 替代统计服务计算基础指标 |
| Judge | Schema、证据、约束与逻辑检查 | 自动批准高风险写操作 |

## 4. 状态与恢复

状态为 `PENDING -> PLANNING -> RUNNING -> COMPLETED`，有写入意图时进入 `WAITING_APPROVAL`；错误路径可进入 `RETRYING / DEGRADED / FAILED`，用户可取消到 `CANCELLED`。

每次转换先持久化，再发布 SSE 事件。节点输出经 Schema 校验后进入下一节点；重试只读 Checkpoint；副作用 Tool 携带 `idempotency_key`。

## 5. 分层约束

- `api`：鉴权、租户上下文、HTTP/SSE 契约。
- `services`：状态转换、事务与用例编排。
- `agents/graph`：语义判断与结构化结果。
- `tools/adapters/rag`：确定性能力、数据源与知识检索。
- `repositories/db/state`：持久化与 Checkpoint。
- `observability/evaluation`：Trace、指标、离线与在线评测。

## 6. 交付策略

当前实现是能通过测试的架构基线：同步运行的规则型 Agent 与内存仓储用于证明契约。接入真实数据前，按业务纵切替换仓储、Tool、模型节点与异步 Worker，不改变审批、证据和状态边界。
