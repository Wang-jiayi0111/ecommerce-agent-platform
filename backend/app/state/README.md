# State / Checkpoint

生产实现使用 Redis Checkpoint 与 PostgreSQL 状态记录；节点重试只读取已持久化的上游输出。
