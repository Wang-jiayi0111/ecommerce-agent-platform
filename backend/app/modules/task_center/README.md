# Task Center

负责 `agent_task`、`agent_step`、事件流、Checkpoint、取消、重试和终态管理。状态转换必须先持久化再广播。
