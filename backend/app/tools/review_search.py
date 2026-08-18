from collections import Counter
from typing import Annotated
from uuid import uuid4

from pydantic import Field, StringConstraints, ValidationError

from app.adapters.commerce.adapter_registry import (
    CommerceAdapterRegistry,
)
from app.adapters.commerce.commerce_adapter_base import (
    AdapterContext,
    AdapterError,
)
from app.modules.market_intelligence.schemas import (
    AdapterCapabilities,
    CollectionRun,
    CollectionStatus,
    DataSourceMode,
    EvidenceReference,
    NormalizedReview,
    ReviewSearchRequest,
)
from app.repositories.collection_repository import (
    CollectionRepository,
)
from app.tools.contracts import (
    ToolError,
    ToolRequest,
    ToolResponse,
)


NonEmptyStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class ReviewSearchToolParameters(ReviewSearchRequest):
    schema_version: NonEmptyStr = "1.0"
    task_id: NonEmptyStr
    tool_call_id: NonEmptyStr = Field(
        default_factory=lambda: str(uuid4())
    )
    data_source_mode: DataSourceMode


class ReviewSearchTool:
    name = "review_search"
    schema_version = "1.0"

    def __init__(
        self,
        adapter_registry: CommerceAdapterRegistry,
        repository: CollectionRepository,
        *,
        max_reviews_per_product: int = 50,
    ) -> None:
        if not 1 <= max_reviews_per_product <= 50:
            raise ValueError(
                "max_reviews_per_product must be between 1 and 50"
            )

        self.adapter_registry = adapter_registry
        self.repository = repository
        self.max_reviews_per_product = max_reviews_per_product

    def execute(
        self,
        request: ToolRequest,
    ) -> ToolResponse:
        identity_error = self._validate_tool_identity(request)

        if identity_error is not None:
            return self._error_response(
                request=request,
                code="INVALID_ARGUMENT",
                message=identity_error,
                source=self.name,
            )

        try:
            parameters = ReviewSearchToolParameters.model_validate(
                request.parameters
            )
        except ValidationError as exc:
            return self._error_response(
                request=request,
                code="INVALID_ARGUMENT",
                message=self._error_summary(exc),
                source=self.name,
            )

        source = (
            f"{parameters.platform.lower()}:"
            f"{parameters.data_source_mode.value}"
        )

        if parameters.schema_version != self.schema_version:
            return self._error_response(
                request=request,
                code="SCHEMA_VERSION_UNSUPPORTED",
                message=(
                    "Unsupported ReviewSearchTool schema version: "
                    f"{parameters.schema_version}."
                ),
                source=source,
            )

        if (
            parameters.review_limit_per_product
            > self.max_reviews_per_product
        ):
            return self._error_response(
                request=request,
                code="INVALID_ARGUMENT",
                message=(
                    "review_limit_per_product exceeds server maximum "
                    f"{self.max_reviews_per_product}."
                ),
                source=source,
            )

        try:
            adapter = self.adapter_registry.get(
                parameters.platform,
                parameters.data_source_mode.value,
            )
        except KeyError:
            return self._error_response(
                request=request,
                code="UNSUPPORTED_DATA_SOURCE",
                message=(
                    "No commerce adapter is registered for "
                    f"{parameters.platform}/"
                    f"{parameters.data_source_mode.value}."
                ),
                source=source,
            )

        try:
            capabilities = AdapterCapabilities.model_validate(
                self._model_payload(
                    adapter.capabilities()
                )
            )
        except AdapterError as exc:
            return self._adapter_error_response(
                request=request,
                source=source,
                error=exc,
            )
        except (
            AttributeError,
            TypeError,
            ValidationError,
        ):
            return self._error_response(
                request=request,
                code="SCHEMA_VALIDATION_FAILED",
                message="Adapter returned invalid capabilities.",
                source=source,
            )

        if not capabilities.supports_reviews:
            return self._error_response(
                request=request,
                code="UNSUPPORTED_OPERATION",
                message=(
                    f"Adapter {source} does not support review search."
                ),
                source=source,
            )

        if (
            parameters.review_limit_per_product
            > capabilities.max_reviews_per_product
        ):
            return self._error_response(
                request=request,
                code="INVALID_ARGUMENT",
                message=(
                    "review_limit_per_product exceeds adapter maximum "
                    f"{capabilities.max_reviews_per_product}."
                ),
                source=source,
            )

        adapter_request = ReviewSearchRequest(
            platform=parameters.platform,
            market=parameters.market,
            category=parameters.category,
            keyword=parameters.keyword,
            product_ids=parameters.product_ids,
            review_limit_per_product=(
                parameters.review_limit_per_product
            ),
        )

        adapter_context = AdapterContext(
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            trace_id=request.trace_id,
            task_id=parameters.task_id,
            tool_call_id=parameters.tool_call_id,
        )

        try:
            adapter_result = adapter.search_reviews(
                adapter_request,
                adapter_context,
            )
        except AdapterError as exc:
            return self._adapter_error_response(
                request=request,
                source=source,
                error=exc,
            )
        except Exception:
            return self._error_response(
                request=request,
                code="COLLECTION_INTERNAL_ERROR",
                message="Review collection failed unexpectedly.",
                source=source,
                retryable=True,
            )

        try:
            run = CollectionRun.model_validate(
                self._model_payload(adapter_result.run)
            )

            reviews = [
                NormalizedReview.model_validate(
                    self._model_payload(review)
                )
                for review in adapter_result.data
            ]

            evidence_refs = [
                EvidenceReference.model_validate(
                    self._model_payload(evidence)
                )
                for evidence in adapter_result.evidence_refs
            ]

            warnings = list(adapter_result.warnings)

            self._validate_adapter_result(
                request=request,
                parameters=parameters,
                run=run,
                reviews=reviews,
                evidence_refs=evidence_refs,
            )

        except (
            AttributeError,
            TypeError,
            ValueError,
            ValidationError,
        ) as exc:
            return self._error_response(
                request=request,
                code="SCHEMA_VALIDATION_FAILED",
                message=(
                    "Adapter returned invalid review data: "
                    f"{exc}"
                ),
                source=source,
            )

        # AdapterResult 校验通过后再统一持久化
        try:
            self.repository.save_review_collection(
                run=run,
                reviews=reviews,
                evidence_refs=evidence_refs,
            )
        except Exception:
            return self._error_response(
                request=request,
                code="COLLECTION_INTERNAL_ERROR",
                message=(
                    "Failed to persist review collection."
                ),
                source=source,
                retryable=True,
            )

        return ToolResponse(
            success=True,
            source=source,
            trace_id=request.trace_id,
            degraded=(
                adapter_result.degraded
                or run.status is CollectionStatus.PARTIAL
            ),
            data={
                "collection_run_id": run.id,
                "keyword": parameters.keyword,
                "product_ids": parameters.product_ids,
                "requested_count": run.requested_count,
                "actual_count": run.actual_count,
                "status": run.status.value,
                "stop_reason": run.stop_reason,
                "adapter_version": run.adapter_version,
                "parser_version": run.parser_version,
                "warnings": warnings,
                "reviews": [
                    review.model_dump(mode="json")
                    for review in reviews
                ],
                "evidence_refs": [
                    evidence.model_dump(mode="json")
                    for evidence in evidence_refs
                ],
            },
        )

    @staticmethod
    def _validate_adapter_result(
        *,
        request: ToolRequest,
        parameters: ReviewSearchToolParameters,
        run: CollectionRun,
        reviews: list[NormalizedReview],
        evidence_refs: list[EvidenceReference],
    ) -> None:
        if run.tenant_id != request.tenant_id:
            raise ValueError(
                "run.tenant_id does not match ToolRequest"
            )

        if run.trace_id != request.trace_id:
            raise ValueError(
                "run.trace_id does not match ToolRequest"
            )

        if run.task_id != parameters.task_id:
            raise ValueError(
                "run.task_id does not match tool parameters"
            )

        if run.actual_count != len(reviews):
            raise ValueError(
                "run.actual_count does not match review count"
            )

        if not reviews:
            raise ValueError(
                "successful review result must not be empty"
            )

        requested_product_ids = set(parameters.product_ids)
        review_counts = Counter(
            review.product_id
            for review in reviews
        )

        for review in reviews:
            if review.collection_run_id != run.id:
                raise ValueError(
                    "review.collection_run_id must match run.id"
                )

            if review.product_id not in requested_product_ids:
                raise ValueError(
                    "adapter returned review for unrequested product"
                )

        for product_id, count in review_counts.items():
            if count > parameters.review_limit_per_product:
                raise ValueError(
                    "adapter returned too many reviews for "
                    f"product {product_id}"
                )

        if len(evidence_refs) != len(reviews):
            raise ValueError(
                "review count and evidence count must match"
            )

        for review, evidence in zip(
            reviews,
            evidence_refs,
            strict=True,
        ):
            if evidence.collection_run_id != run.id:
                raise ValueError(
                    "evidence.collection_run_id must match run.id"
                )

            if evidence.review_id != review.review_id:
                raise ValueError(
                    "evidence.review_id must match review.review_id"
                )

            if evidence.product_id != review.product_id:
                raise ValueError(
                    "evidence.product_id must match review.product_id"
                )

            if evidence.tool_call_id != parameters.tool_call_id:
                raise ValueError(
                    "evidence.tool_call_id must match tool_call_id"
                )

            # 每条评论必须能够回溯到同一份源快照
            if (
                evidence.snapshot_ref
                != review.source_snapshot_ref
            ):
                raise ValueError(
                    "evidence.snapshot_ref must match "
                    "review.source_snapshot_ref"
                )

    @staticmethod
    def _validate_tool_identity(
        request: ToolRequest,
    ) -> str | None:
        fields = {
            "tenant_id": request.tenant_id,
            "user_id": request.user_id,
            "trace_id": request.trace_id,
        }

        for field_name, value in fields.items():
            if not isinstance(value, str) or not value.strip():
                return f"{field_name} is required."

        return None

    @staticmethod
    def _model_payload(value):
        if hasattr(value, "model_dump"):
            return value.model_dump()

        return value

    @staticmethod
    def _error_summary(
        error: ValidationError,
    ) -> str:
        messages = []

        for item in error.errors():
            location = ".".join(
                str(part)
                for part in item["loc"]
            )
            messages.append(
                f"{location}: {item['msg']}"
            )

        return "; ".join(messages)

    @classmethod
    def _adapter_error_response(
        cls,
        *,
        request: ToolRequest,
        source: str,
        error: AdapterError,
    ) -> ToolResponse:
        return cls._error_response(
            request=request,
            code=error.code,
            message=str(error),
            source=source,
            retryable=error.retryable,
            collection_run_id=error.collection_run_id,
        )

    @staticmethod
    def _error_response(
        *,
        request: ToolRequest,
        code: str,
        message: str,
        source: str,
        retryable: bool = False,
        collection_run_id: str | None = None,
    ) -> ToolResponse:
        data = {}

        if collection_run_id is not None:
            data["collection_run_id"] = collection_run_id

        return ToolResponse(
            success=False,
            source=source,
            trace_id=request.trace_id,
            data=data,
            error=ToolError(
                code=code,
                message=message,
                retryable=retryable,
            ),
        )