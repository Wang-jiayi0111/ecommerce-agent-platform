from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Protocol

from pydantic import Field

from app.llm.contracts import LLMClientError, LLMMessage, StructuredLLMClient
from app.modules.market_intelligence.schemas.analysis import EntryAssessment
from app.modules.market_intelligence.schemas.common import MarketIntelligenceModel
from app.modules.market_intelligence.schemas.report import Statement
from app.prompts.market_intelligence import build_report_synthesis_prompt

if TYPE_CHECKING:
    from app.modules.market_intelligence.state import MarketIntelligenceState


class ReportSynthesisOutput(MarketIntelligenceModel):
    schema_version: Literal["1.0"] = "1.0"
    entry_assessment: EntryAssessment
    facts: list[Statement] = Field(default_factory=list)
    inferences: list[Statement] = Field(default_factory=list)
    opportunity_signals: list[Statement] = Field(default_factory=list)
    risk_signals: list[Statement] = Field(default_factory=list)
    suggested_actions: list[Statement] = Field(default_factory=list)


class ReportSynthesisError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


class ReportSynthesizer(Protocol):
    def synthesize(
        self,
        state: MarketIntelligenceState,
    ) -> ReportSynthesisOutput:
        ...


class LLMMarketIntelligenceReporter:
    """让 LLM 只综合已采集的结构化事实和证据。"""

    def __init__(self, client: StructuredLLMClient) -> None:
        self.client = client

    def synthesize(
        self,
        state: MarketIntelligenceState,
    ) -> ReportSynthesisOutput:
        payload = self._payload(state)
        system_prompt, user_prompt = build_report_synthesis_prompt(payload)
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]
        try:
            output = self.client.generate_structured(
                messages=messages,
                response_model=ReportSynthesisOutput,
            )
        except LLMClientError as exc:
            raise ReportSynthesisError(
                str(exc),
                retryable=exc.retryable,
            ) from exc

        self._validate_references(state, output)
        return output

    @staticmethod
    def degraded(
        *,
        limitation_id: str,
    ) -> ReportSynthesisOutput:
        return ReportSynthesisOutput(
            entry_assessment=EntryAssessment(
                decision="INSUFFICIENT_DATA",
                summary="报告综合服务不可用，当前仅保留已采集的结构化数据。",
                limitation_ids=[limitation_id],
            ),
            suggested_actions=[
                Statement(
                    statement_id="action-retry-report-synthesis",
                    text="恢复报告综合服务后重新生成进入判断。",
                    confidence=1,
                    affected_by_limitations=[limitation_id],
                )
            ],
        )

    @staticmethod
    def _payload(state: MarketIntelligenceState) -> dict:
        def data(name: str, key: str):
            response = state[name]  # type: ignore[literal-required]
            return response.data.get(key) if response and response.success else None

        return {
            "schema_version": "1.0",
            "request": state["request"].model_dump(mode="json"),
            "competitor_matrix": [
                item.model_dump(mode="json") for item in state["competitor_matrix"]
            ],
            "market_metrics": data("market_result", "metrics"),
            "review_insight": data("review_result", "review_insight"),
            "profit_analysis": data("profit_result", "profit_analysis"),
            "allowed_evidence_ids": [
                item.evidence_id for item in state["evidence_refs"]
            ],
            "data_limitations": [
                item.model_dump(mode="json") for item in state["data_limitations"]
            ],
        }

    @staticmethod
    def _validate_references(
        state: MarketIntelligenceState,
        output: ReportSynthesisOutput,
    ) -> None:
        allowed_evidence = {item.evidence_id for item in state["evidence_refs"]}
        allowed_limitations = {
            item.limitation_id for item in state["data_limitations"]
        }
        statements = [
            *output.facts,
            *output.inferences,
            *output.opportunity_signals,
            *output.risk_signals,
            *output.suggested_actions,
        ]
        used_evidence = {
            evidence_id for item in statements for evidence_id in item.evidence_ids
        } | set(output.entry_assessment.evidence_ids)
        used_limitations = {
            limitation_id
            for item in statements
            for limitation_id in item.affected_by_limitations
        } | set(output.entry_assessment.limitation_ids)
        if used_evidence - allowed_evidence or used_limitations - allowed_limitations:
            raise ReportSynthesisError(
                "Report synthesis contains references outside the supplied state.",
                retryable=False,
            )
