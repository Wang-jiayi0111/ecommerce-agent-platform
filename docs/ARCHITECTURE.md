# 架构决策

- 一期采用模块化单体 + 独立 Agent Worker，避免过早微服务化。
- Agent 不直接访问数据源；所有能力经 Tool/Service/Adapter。
- 数据按租户、店铺、用户隔离，Tool 层再次鉴权。
- 证据分 A 业务事实、B 检索证据、C 模型推断、D 缺失/未知。
- 写操作必须审批、RBAC、审计和幂等；审批快照哈希与实际参数一致。
- 外部调用统一 timeout、retry、backoff、circuit breaker 与 rate limit。
