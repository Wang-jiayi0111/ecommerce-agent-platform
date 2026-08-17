from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import uuid4

from pydantic import Field, StringConstraints, model_validator

from app.modules.market_intelligence.schemas.common import (
    AnalysisScope,
    DataSourceMode,
    MarketIntelligenceModel,
    NonEmptyStr,
    NonNegativeInt,
)


class ProductSort(StrEnum):
    DEFAULT = "default"
    SALES_DESC = "sales_desc"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"


class CollectionStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PARTIAL = "PARTIAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class EvidenceType(StrEnum):
    PRODUCT = "product"
    REVIEW = "review"
    MARKET_METRIC = "market_metric"
    PROFIT_INPUT = "profit_input"
    DATASET = "dataset"
    API_RESPONSE = "api_response"


class DataLevel(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class DatasetSourceType(StrEnum):
    SYNTHETIC = "synthetic"
    AUTHORIZED_EXPORT = "authorized_export"
    ANONYMIZED_SNAPSHOT = "anonymized_snapshot"


Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F]{64}$")]


class DatasetManifest(MarketIntelligenceModel):
    dataset_id: NonEmptyStr
    dataset_version: NonEmptyStr
    schema_version: NonEmptyStr
    platform: NonEmptyStr
    market: NonEmptyStr
    category: NonEmptyStr
    keyword: NonEmptyStr
    source_type: DatasetSourceType
    source_description: NonEmptyStr
    generated_at: datetime
    source_timestamp: datetime
    expires_at: datetime | None = None
    license_or_authorization: NonEmptyStr
    checksums: dict[NonEmptyStr, Sha256]

    @model_validator(mode="after")
    def validate_manifest(self) -> "DatasetManifest":
        if not self.checksums:
            raise ValueError("checksums must contain at least one dataset file")
        if self.expires_at is not None:
            try:
                invalid_range = self.expires_at <= self.generated_at
            except TypeError as exc:
                raise ValueError(
                    "generated_at and expires_at must use compatible timezones"
                ) from exc
            if invalid_range:
                raise ValueError("expires_at must be later than generated_at")
        return self


class ProductSearchRequest(MarketIntelligenceModel):
    platform: NonEmptyStr
    market: NonEmptyStr
    category: NonEmptyStr
    keyword: NonEmptyStr
    product_limit: int = Field(ge=1, le=50)
    sort_by: ProductSort = ProductSort.DEFAULT


class AdapterCapabilities(MarketIntelligenceModel):
    platform: NonEmptyStr
    data_source_mode: DataSourceMode
    supports_products: bool
    supports_reviews: bool
    supports_market_metrics: bool
    max_products: int = Field(ge=1)
    max_reviews_per_product: NonNegativeInt
    adapter_version: NonEmptyStr
    schema_version: NonEmptyStr = "1.0"


class CollectionRun(MarketIntelligenceModel):
    id: NonEmptyStr = Field(default_factory=lambda: str(uuid4()))
    task_id: NonEmptyStr
    trace_id: NonEmptyStr
    tenant_id: NonEmptyStr
    keyword: NonEmptyStr
    requested_count: NonNegativeInt
    actual_count: NonNegativeInt = 0
    status: CollectionStatus = CollectionStatus.PENDING
    stop_reason: NonEmptyStr | None = None
    adapter_version: NonEmptyStr
    parser_version: NonEmptyStr | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None


class EvidenceReference(MarketIntelligenceModel):
    evidence_id: NonEmptyStr
    evidence_type: EvidenceType
    data_level: DataLevel
    data_source: NonEmptyStr
    platform: NonEmptyStr
    product_id: NonEmptyStr | None = None
    review_id: NonEmptyStr | None = None
    query_range: dict[str, Any]
    source_timestamp: datetime
    ingest_timestamp: datetime
    tool_call_id: NonEmptyStr
    collection_run_id: NonEmptyStr
    snapshot_ref: NonEmptyStr
    sha256: NonEmptyStr
    data_version: NonEmptyStr
    sample_scope: AnalysisScope
