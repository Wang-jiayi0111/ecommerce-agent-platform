import logging
from uuid import uuid4

from pydantic import Field, ValidationError

from app.adapters.commerce import AdapterContext, AdapterError, CommerceAdapterRegistry
from app.modules.market_intelligence.schemas import (
    DataSourceMode,
    MarketDataRequest,
    MarketMetric,
    MetricStatus,
    NonEmptyStr,
    EvidenceReference,
    NormalizedProduct,
)
from app.tools.support.contracts import ToolError, ToolRequest, ToolResponse
from app.tools.support.market_sample_metrics import (
    MarketSampleMetricsError,
    MarketSampleMetricsResult,
    build_market_sample_metrics,
)


logger = logging.getLogger(__name__)


class MarketDataToolParameters(MarketDataRequest):
    """MarketDataTool 对外参数。"""

    schema_version: NonEmptyStr = "1.0"
    task_id: NonEmptyStr
    data_source_mode: DataSourceMode
    tool_call_id: NonEmptyStr = Field(default_factory=lambda: str(uuid4()))
    products: list[NormalizedProduct] = Field(default_factory=list)
    evidence_refs: list[EvidenceReference] = Field(default_factory=list)


class MarketDataTool:
    name = "MarketDataTool"
    schema_version = "1.0"

    FULL_MARKET_METRIC_CODES = {
        "market_size",
        "gmv",
        "growth",
        "price_distribution",
        "brand_concentration",
        "product_concentration",
    }

    def __init__(self, registry: CommerceAdapterRegistry) -> None:
        self.registry = registry

    def execute(self, tool_request: ToolRequest) -> ToolResponse:
        try:
            return self._execute(tool_request)
        except Exception:
            logger.exception(
                "MarketDataTool failed unexpectedly stage=execute "
                "task_id=%s trace_id=%s",
                tool_request.task_id,
                tool_request.trace_id,
            )
            return self._error_response(
                request=tool_request,
                code="MARKET_DATA_INTERNAL_ERROR",
                message="Market data processing failed unexpectedly.",
                source=self.name,
            )

    def _execute(self, tool_request: ToolRequest) -> ToolResponse:
        identity_error = self._validate_tool_identity(tool_request)
        if identity_error is not None:
            return self._error_response(
                request=tool_request,
                code="INVALID_ARGUMENT",
                message=identity_error,
                source=self.name,
            )
        
        # 1. 校验 Tool 参数
        try:
            parameters = MarketDataToolParameters.model_validate(tool_request.parameters)
        except ValidationError as exc:
            return self._error_response(
                request=tool_request,
                code="INVALID_ARGUMENT",
                message=self._error_summary(exc),
            )

        platform = parameters.platform
        data_source_mode = parameters.data_source_mode.value

        if parameters.schema_version != self.schema_version:
            return self._error_response(
                request=tool_request,
                code="SCHEMA_VERSION_UNSUPPORTED",
                message=(
                    "Unsupported MarketDataTool schema version: "
                    f"{parameters.schema_version}."
                ),
                source=f"{platform}:{data_source_mode}",
            )

        # 2. 根据 platform + data_source_mode 选择 Adapter
        try:
            adapter = self.registry.get(platform=platform, data_source_mode=data_source_mode)
        except (KeyError, TypeError, ValueError):
            return self._error_response(
                request=tool_request,
                code="UNSUPPORTED_DATA_SOURCE",
                message=f"Unsupported market data source: {platform}/{data_source_mode}.",
                source=f"{platform}:{data_source_mode}",
            )

        # 3. Adapter 不支持聚合市场指标时，退回到明确标注的商品样本统计
        capabilities = adapter.capabilities()

        if not capabilities.supports_market_metrics:
            try:
                sample_result = build_market_sample_metrics(
                    platform=parameters.platform,
                    market=parameters.market,
                    category=parameters.category,
                    keyword=parameters.keyword,
                    data_source_mode=parameters.data_source_mode,
                    requested_start_time=parameters.start_time,
                    requested_end_time=parameters.end_time,
                    products=parameters.products,
                    evidence_refs=parameters.evidence_refs,
                )
            except MarketSampleMetricsError as exc:
                return self._error_response(
                    request=tool_request,
                    code="INVALID_ARGUMENT",
                    message=str(exc),
                    source=f"{platform}:{data_source_mode}",
                )

            return self._sample_fallback_response(
                request=tool_request,
                platform=platform,
                data_source_mode=data_source_mode,
                adapter_version=capabilities.adapter_version,
                sample_result=sample_result,
            )

        # 4. Tool 参数 → Adapter 业务请求
        request = MarketDataRequest(
            platform=parameters.platform, market=parameters.market,
            category=parameters.category, keyword=parameters.keyword,
            start_time=parameters.start_time, end_time=parameters.end_time,
        )

        # 5. 构造 Adapter 执行上下文
        context = AdapterContext(
            tenant_id=tool_request.tenant_id, user_id=tool_request.user_id,
            trace_id=tool_request.trace_id, task_id=parameters.task_id,
            tool_call_id=parameters.tool_call_id,
        )

        # 6. 调 Adapter
        try:
            result = adapter.get_market_metrics(request, context)
        except AdapterError as exc:
            return self._adapter_error_response(
                request=tool_request,
                platform=platform,
                data_source_mode=data_source_mode,
                error=exc,
            )
        except Exception:
            logger.exception(
                "MarketDataTool failed unexpectedly stage=get_market_metrics "
                "task_id=%s trace_id=%s source=%s",
                tool_request.task_id,
                tool_request.trace_id,
                f"{platform}:{data_source_mode}",
            )
            return self._error_response(
                request=tool_request,
                code="MARKET_DATA_INTERNAL_ERROR",
                message="Market data retrieval failed because of an internal error.",
                source=f"{platform}:{data_source_mode}",
                retryable=True,
            )

        # 7. Tool 层判断是否属于降级市场数据
        degraded = result.degraded or self._has_incomplete_market_data(result.data)
        # 8. AdapterResult → ToolResponse
        return ToolResponse(
            success=True,
            data={
                "schema_version": self.schema_version,
                "collection_run_id": result.run.id,
                "status": result.run.status.value,
                "stop_reason": result.run.stop_reason,
                "adapter_version": result.run.adapter_version,
                "metrics": [metric.model_dump(mode="json") for metric in result.data],
                "evidence_refs": [e.model_dump(mode="json") for e in result.evidence_refs],
                "warnings": list(result.warnings),
            },
            error=None,
            source=f"{platform}:{data_source_mode}",
            trace_id=tool_request.trace_id,
            degraded=degraded,
        )

    def _sample_fallback_response(
        self, *, request: ToolRequest, platform: str, data_source_mode: str,
        adapter_version: str, sample_result: MarketSampleMetricsResult,
    ) -> ToolResponse:
        return ToolResponse(
            success=True,
            data={
                "schema_version": self.schema_version,
                "collection_run_id": str(uuid4()),
                "source_collection_run_ids": sample_result.source_collection_run_ids,
                "status": "COMPLETED",
                "stop_reason": "AGGREGATE_MARKET_DATA_MISSING",
                "adapter_version": adapter_version,
                "metrics": [metric.model_dump(mode="json") for metric in sample_result.metrics],
                "evidence_refs": [e.model_dump(mode="json") for e in sample_result.evidence_refs],
                "warnings": sample_result.warnings,
            },
            error=None,
            source=f"{platform}:{data_source_mode}",
            trace_id=request.trace_id,
            degraded=True,
        )

    @staticmethod
    def _validate_tool_identity(request: ToolRequest) -> str | None:
        for field_name in ("tenant_id", "user_id", "trace_id"):
            value = getattr(request, field_name, None)
            if not isinstance(value, str) or not value.strip():
                return f"{field_name} is required"
        return None

    def _has_incomplete_market_data(self, metrics: list[MarketMetric]) -> bool:
        """
        全市场核心指标不完整时，
        Tool 层视为降级结果。

        sample 指标仍可以正常返回。
        """

        metrics_by_code = {metric.metric_code: metric for metric in metrics}
        for metric_code in self.FULL_MARKET_METRIC_CODES:
            metric = metrics_by_code.get(metric_code)
            if metric is None or metric.status is not MetricStatus.AVAILABLE:
                return True

        return False

    def _adapter_error_response(
        self, *, request: ToolRequest, platform: str,
        data_source_mode: str, error: AdapterError,
    ) -> ToolResponse:
        data = {"schema_version": self.schema_version}

        if error.collection_run_id is not None:
            data["collection_run_id"] = error.collection_run_id

        return ToolResponse(
            success=False,
            data=data,
            error=ToolError(code=error.code, message=str(error), retryable=error.retryable),
            source=f"{platform}:{data_source_mode}",
            trace_id=request.trace_id,
            degraded=False,
        )

    def _error_response(
        self, *, request: ToolRequest, code: str, message: str,
        source: str | None = None, retryable: bool = False,
    ) -> ToolResponse:
        return ToolResponse(
            success=False,
            data={"schema_version": self.schema_version},
            error=ToolError(code=code, message=message, retryable=retryable),
            source=source or self.name,
            trace_id=request.trace_id,
            degraded=False,
        )

    @staticmethod
    def _error_summary(exc: ValidationError) -> str:
        messages = []

        for error in exc.errors():
            location = ".".join(str(part) for part in error["loc"])
            messages.append(f"{location}: {error['msg']}")

        return "; ".join(messages)
