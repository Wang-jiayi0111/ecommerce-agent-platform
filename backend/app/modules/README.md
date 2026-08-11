# 业务模块

每个模块按 `schemas -> services -> repositories -> tools/adapters -> API -> tests` 的顺序实现，Agent 只消费稳定契约。

- `task_center`：任务、状态、Trace、恢复与取消。
- `market_intelligence`：市场、竞品和评论证据。
- `product_strategy`：用户定位、价格带、卖点和风险。
- `listing`：结构化 Listing、事实与平台规则校验。
- `operations_diagnosis`：销售、流量、转化和库存异常诊断。
- `knowledge_base`：知识入库、版本、检索和引用。
- `governance`：审批、RBAC、幂等与审计。
- `evaluation`：固定评测集、指标与报告。
