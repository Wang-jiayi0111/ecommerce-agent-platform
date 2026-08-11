from datetime import UTC, datetime

from app.domain import (
    AgentTask,
    ApprovalStatus,
    TaskCreate,
    TaskStatus,
    result_hash,
)
from app.graph.operations_graph import EcommerceOperationsGraph
from app.policy import ApprovalPolicy
from app.repositories import InMemoryTaskRepository, TaskRepository


class TaskService:
    """统一处理任务状态、编排、审批、取消和审计事件。"""

    def __init__(
        self,
        repository: TaskRepository | None = None,
        operations_graph: EcommerceOperationsGraph | None = None,
        approval_policy: ApprovalPolicy | None = None,
    ) -> None:
        self.repository = repository or InMemoryTaskRepository()
        self.operations_graph = operations_graph or EcommerceOperationsGraph()
        self.approval_policy = approval_policy or ApprovalPolicy()

    def create(self, payload: TaskCreate) -> AgentTask:
        task = AgentTask(request=payload)
        self.repository.add(task)
        self._transition(task, TaskStatus.PLANNING, "task:planning")
        self._transition(task, TaskStatus.RUNNING, "task:running")
        state = self.operations_graph.run(task)
        if state.approval_status == "WAITING_APPROVAL":
            task.approval_status = ApprovalStatus.WAITING_APPROVAL
            self._transition(task, TaskStatus.WAITING_APPROVAL, "task:waiting_approval")
        else:
            self._transition(task, TaskStatus.COMPLETED, "task:completed")
        return task

    def get(self, task_id: str) -> AgentTask:
        return self.repository.get(task_id)

    def list(self, limit: int = 50, status: TaskStatus | None = None) -> list[AgentTask]:
        tasks = self.repository.list(limit)
        return [task for task in tasks if status is None or task.status == status]

    def cancel(self, task_id: str) -> AgentTask:
        task = self.get(task_id)
        if task.status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}:
            raise ValueError(f"task cannot be cancelled from {task.status}")
        self._transition(task, TaskStatus.CANCELLED, "task:cancelled")
        return task

    def approve(self, task_id: str) -> AgentTask:
        task = self.get(task_id)
        if task.status != TaskStatus.WAITING_APPROVAL or task.result is None:
            raise ValueError("task is not waiting for approval")
        task.approval_hash = result_hash(task.result)
        task.approval_status = ApprovalStatus.APPROVED
        task.events.append("approval:approved")
        self.approval_policy.validate_completion(task)
        self._transition(task, TaskStatus.COMPLETED, "task:completed")
        return task

    def reject(self, task_id: str) -> AgentTask:
        task = self.get(task_id)
        if task.status != TaskStatus.WAITING_APPROVAL:
            raise ValueError("task is not waiting for approval")
        task.approval_status = ApprovalStatus.REJECTED
        task.events.append("approval:rejected")
        self._transition(task, TaskStatus.CANCELLED, "task:cancelled")
        return task

    @staticmethod
    def _transition(task: AgentTask, status: TaskStatus, event: str) -> None:
        task.status = status
        task.current_step = event.removeprefix("task:")
        task.state_version += 1
        task.updated_at = datetime.now(UTC)
        task.events.append(event)
