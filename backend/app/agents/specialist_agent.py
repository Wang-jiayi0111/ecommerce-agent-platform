from dataclasses import dataclass

from app.domain import AgentResult, EvidenceRef, TaskCreate


@dataclass(frozen=True)
class SpecialistProfile:
    name: str
    result_type: str
    summary: str
    default_actions: list[str]
    requires_approval: bool = False


class RuleBasedSpecialistAgent:
    """可运行的结构化基线，后续可在不改变契约的前提下替换为模型节点。"""

    def __init__(self, profile: SpecialistProfile) -> None:
        self.profile = profile

    def run(self, task: TaskCreate) -> AgentResult:
        source = f"fixture://{self.profile.name}/v1"
        evidence = EvidenceRef(
            id=f"{self.profile.name}-evidence-001",
            grade="D",
            source=source,
            summary="当前为固定演示数据；接入授权 Tool 后升级为 A/B 级证据。",
        )
        return AgentResult(
            result_type=self.profile.result_type,
            summary=f"{self.profile.summary} 任务目标：{task.user_query}",
            facts=["开发环境尚未接入授权业务数据，关键数值标记为 unavailable。"],
            inferences=["以下结论仅用于验证编排、审批和审计闭环。"],
            actions=self.profile.default_actions,
            evidence_refs=[evidence],
            requires_approval=self.profile.requires_approval,
            payload={"intent": task.intent, "business_context": task.business_context},
        )
