from typing import Any

from pydantic import BaseModel, Field


class AgentState(BaseModel):
    """PRD 6.2 定义的可持久化跨节点状态。"""

    task_id: str
    user_id: str
    tenant_id: str
    user_query: str
    constraints: dict[str, Any] = Field(default_factory=dict)
    intent: str
    task_plan: list[str] = Field(default_factory=list)
    current_step: str | None = None
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: dict[str, Any] = Field(default_factory=dict)
    business_context: dict[str, Any] = Field(default_factory=dict)
    agent_outputs: dict[str, Any] = Field(default_factory=dict)
    approval_status: str = "NOT_REQUIRED"
    error: str | None = None
    retry_count: int = 0
    degraded_flags: list[str] = Field(default_factory=list)
    final_result: dict[str, Any] = Field(default_factory=dict)
    state_version: int = 1
