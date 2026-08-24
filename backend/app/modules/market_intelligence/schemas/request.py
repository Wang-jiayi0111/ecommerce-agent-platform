from typing import Literal

from pydantic import ConfigDict, Field, JsonValue

from app.modules.market_intelligence.schemas.adapter import ProductSort
from app.modules.market_intelligence.schemas.common import (
    DataSourceMode,
    MarketIntelligenceModel,
    NonEmptyStr,
)
from app.modules.market_intelligence.schemas.profit import (
    ProfitCalculatorParameters,
)


class MarketIntelligenceContext(MarketIntelligenceModel):
    """由任务系统提供的可信运行上下文。"""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        frozen=True,
    )

    schema_version: Literal["1.0"] = "1.0"
    task_id: NonEmptyStr
    tenant_id: NonEmptyStr
    user_id: NonEmptyStr
    trace_id: NonEmptyStr
    user_query: NonEmptyStr
    constraints: dict[str, JsonValue] = Field(default_factory=dict)

class CollectionOptions(MarketIntelligenceModel):
    product_limit: int = Field(ge=1, le=50)
    review_limit_per_product: int | None = Field(default=None, ge=1)
    sort_by: ProductSort = ProductSort.DEFAULT


class MarketIntelligenceRequest(MarketIntelligenceModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    market: NonEmptyStr
    category: NonEmptyStr
    keyword: NonEmptyStr
    platforms: list[NonEmptyStr] = Field(min_length=1, max_length=1)
    data_source_mode: DataSourceMode
    collection: CollectionOptions
    profit_constraints: ProfitCalculatorParameters | None = None


class MarketIntelligenceBusinessContext(MarketIntelligenceModel):
    """市场任务在 TaskCreate.business_context 中的稳定信封。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    market_intelligence_request: MarketIntelligenceRequest
