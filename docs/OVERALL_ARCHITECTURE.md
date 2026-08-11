# 总体架构总览

交互层提供 AI 工作台、任务中心、分析、策略、Listing、诊断与知识管理；应用服务层提供鉴权、任务、商品和分析 API；Agent 层负责规划、路由与综合判断；能力数据层包含 Tool/MCP Adapter、RAG、关系数据库、Redis、向量库与对象存储。

详细的组件、状态与实施路径见 [PROJECT_FRAMEWORK.md](PROJECT_FRAMEWORK.md)。
