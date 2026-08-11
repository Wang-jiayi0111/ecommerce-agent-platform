# 开发指南

当前框架具备可直接扩展的主链路：创建运营任务、生成收益建议、人工审批、受控执行及回读事件。需求到模块、API、数据对象和验收点的追踪见 `PRD_TRACEABILITY.md`。

## 模块入口

| 模块 | 开发内容 |
| --- | --- |
| `app/agents` | 新增市场、内容、口碑、会员等 Agent；只输出结构化建议。 |
| `app/graph` | 将 Agent 组装为 LangGraph 状态图，并保存 Checkpoint。 |
| `app/tools` | 定义统一的 Tool 输入输出契约。 |
| `app/policy` | 增加审批矩阵、硬规则、预算与品牌策略。 |
| `app/adapters` | 接入已授权的 PMS、CRS、OTA 或内容平台，并完成回读。 |
| `app/repositories` | 以 PostgreSQL 仓储替换本地内存实现。 |
| `app/evaluation` | 增加固定评测集、回归测试与故障注入。 |

## 本地运行

首次安装依赖后执行：

```powershell
.\scripts\Start-Local.ps1
```

浏览器访问 `http://127.0.0.1:5173`，API 文档访问 `http://127.0.0.1:8000/docs`。Docker Desktop 安装后仍可使用 `docker compose up --build` 启动完整依赖环境。

## 扩展要求

任何新增外部写操作必须先实现：策略校验、审批、参数哈希锁定、幂等键、真实状态回读、审计事件和失败恢复。不得通过 Agent 或前端绕过这些边界。
