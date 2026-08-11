from app.domain import AgentTask, ApprovalStatus, TaskStatus, result_hash


class ApprovalPolicy:
    """审批快照与执行结果必须一致，避免批准后参数被替换。"""

    def validate_completion(self, task: AgentTask) -> None:
        if task.result is None:
            raise ValueError("task has no result")
        if task.result.requires_approval:
            if task.approval_status != ApprovalStatus.APPROVED:
                raise ValueError("approval required")
            if task.approval_hash != result_hash(task.result):
                raise ValueError("approved result hash mismatch")
        if task.status in {TaskStatus.CANCELLED, TaskStatus.FAILED}:
            raise ValueError(f"task cannot complete from {task.status}")
