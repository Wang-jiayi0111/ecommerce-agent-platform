# Agent 架构

Supervisor 提取意图和约束并生成计划，然后只路由到一个主要业务 Agent；业务 Agent 可并行调用读 Tool、计算 Tool 和 RAG。Judge 校验 Schema、证据覆盖、逻辑与约束，不通过时仅重试缺失节点。

统一 `AgentState` 至少保存任务与权限归属、原始目标、约束、计划、当前节点、证据、Tool 结果、业务上下文、Agent 输出、审批、错误/重试/降级与最终结果。生产环境使用 LangGraph Checkpoint + Redis/PostgreSQL，禁止依赖进程内对象恢复。

模型或 Prompt 只处理语义理解和综合判断；查询、利润计算、统计、规则与写入必须由可测试的 Tool/Service 完成。
