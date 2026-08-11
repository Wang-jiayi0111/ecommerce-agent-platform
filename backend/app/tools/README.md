# Tool Contracts

一期 Tool：MarketData、ProductSearch、ReviewInsight、SalesMetrics、Inventory、ProfitCalculator、KnowledgeSearch、PolicyCheck、ProductPlanSave。

统一返回 `success/data/error/source/timestamp/trace_id`，错误使用稳定错误码；读操作可按策略重试，写操作必须同时具备审批和幂等键。
