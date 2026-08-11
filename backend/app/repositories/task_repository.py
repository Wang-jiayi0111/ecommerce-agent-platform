from collections.abc import Iterable
from typing import Protocol

from app.domain import AgentTask


class TaskRepository(Protocol):
    def add(self, task: AgentTask) -> AgentTask: ...

    def get(self, task_id: str) -> AgentTask: ...

    def list(self, limit: int = 50) -> list[AgentTask]: ...


class InMemoryTaskRepository:
    """开发期仓储；生产实现应替换为 PostgreSQL 并持久化状态转换。"""

    def __init__(self) -> None:
        self._tasks: dict[str, AgentTask] = {}

    def add(self, task: AgentTask) -> AgentTask:
        self._tasks[str(task.id)] = task
        return task

    def get(self, task_id: str) -> AgentTask:
        try:
            return self._tasks[task_id]
        except KeyError as error:
            raise KeyError("task not found") from error

    def list(self, limit: int = 50) -> list[AgentTask]:
        return list(reversed(list(self._tasks.values())))[:limit]

    def seed(self, tasks: Iterable[AgentTask]) -> None:
        for task in tasks:
            self.add(task)
