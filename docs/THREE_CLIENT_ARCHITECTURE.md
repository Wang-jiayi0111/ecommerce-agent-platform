# 多端架构

一期主端为 `frontend/` Web 工作台；`clients/mobile-ops/` 保留轻量审批和任务查看骨架；外部系统通过版本化 API 或 `packages/shared-*` 契约集成。所有客户端只调用 API，不直连数据库、Redis、向量库或外部平台。
