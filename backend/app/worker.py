"""Agent Worker 进程入口。

一期接入 LangGraph Checkpoint、Redis 队列和 OpenTelemetry 后，在此启动任务消费者。
"""

from app.core import settings


def main() -> None:
    print(f"agent-worker initialized for {settings.environment}")


if __name__ == "__main__":
    main()
