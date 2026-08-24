import re
from decimal import Decimal

from pydantic import ConfigDict, Field, ValidationError

from app.domain import (
    PreviewWarning,
    PreviewWarningSeverity,
    TaskCreate,
    TaskError,
    TaskPreviewRequest,
    TaskPreviewResponse,
)
from app.llm import LLMClientError, LLMMessage, StructuredLLMClient
from app.modules.market_intelligence.dataset_availability import DatasetAvailability
from app.modules.market_intelligence.schemas import (
    DataSourceMode,
    MarketIntelligenceBusinessContext,
    MarketIntelligenceRequest,
    ProductSort,
    ProfitCalculatorParameters,
)
from app.modules.market_intelligence.schemas.common import MarketIntelligenceModel
from app.modules.market_intelligence.schemas.request import CollectionOptions
from app.modules.task_center.input_dispatcher import TaskInputValidationError
from app.prompts.market_intelligence import build_input_extraction_prompt


class MarketInputExtraction(MarketIntelligenceModel):
    """LLM 输出模型；所有业务默认值由确定性代码补充。"""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    product_name: str | None = None
    market: str | None = None
    platform: str | None = None
    category: str | None = None
    keyword: str | None = None
    product_limit: int | None = Field(default=None, ge=1, le=50)
    review_limit_per_product: int | None = Field(default=None, ge=1, le=50)
    price: Decimal | None = Field(default=None, gt=0)
    product_cost: Decimal | None = Field(default=None, ge=0)
    platform_fee: Decimal | None = Field(default=None, ge=0)
    logistics_cost: Decimal | None = Field(default=None, ge=0)
    advertising_cost: Decimal | None = Field(default=None, ge=0)
    minimum_margin: Decimal | None = Field(default=None, ge=0, le=1)
    currency: str | None = None
    confidence: float = Field(default=0.5, ge=0, le=1)
    ambiguities: list[str] = Field(default_factory=list)


class MarketIntelligenceInputExtractor:
    def __init__(
        self,
        availability: DatasetAvailability,
        llm_client: StructuredLLMClient | None = None,
    ) -> None:
        self.availability = availability
        self.llm_client = llm_client

    def preview(self, payload: TaskPreviewRequest) -> TaskPreviewResponse:
        draft, warnings = self._extract(payload.user_query)
        canonical = self.availability.canonicalize_product(
            payload.user_query,
            draft.product_name,
            draft.category,
            draft.keyword,
        )
        if canonical:
            category = canonical.category
            keyword = canonical.keyword
            confidence = max(draft.confidence, 0.95)
        else:
            keyword = draft.keyword or draft.product_name
            category = draft.category or draft.product_name
            confidence = draft.confidence

        market = self._market(draft.market) or (
            canonical.market if canonical else self.availability.default_market()
        )
        platform = self._platform(draft.platform) or (
            canonical.platform if canonical else self.availability.default_platform()
        )
        if draft.market is None and market:
            warnings.append(self._default_warning("market", market))
        if draft.platform is None and platform:
            warnings.append(self._default_warning("platforms", platform))

        missing_fields = [
            field
            for field, value in (
                ("market", market),
                ("platforms", platform),
                ("category", category),
                ("keyword", keyword),
            )
            if not value
        ]
        normalized_input = None
        dataset_matches = []
        if not missing_fields:
            profit_constraints = self._profit_constraints(draft, warnings)
            normalized_input = MarketIntelligenceRequest(
                market=market,
                category=category,
                keyword=keyword,
                platforms=[platform],
                data_source_mode=DataSourceMode.FIXED_DATASET,
                collection=CollectionOptions(
                    product_limit=draft.product_limit or 20,
                    review_limit_per_product=draft.review_limit_per_product or 20,
                    sort_by=ProductSort.DEFAULT,
                ),
                profit_constraints=profit_constraints,
            )
            dataset_matches = self.availability.match(
                normalized_input,
                user_query=payload.user_query,
            )
            if not any(match.supported for match in dataset_matches):
                warnings.append(
                    PreviewWarning(
                        code="DATASET_NOT_AVAILABLE",
                        message="当前固定数据集不支持该商品、平台或市场。",
                        field="normalized_input",
                    )
                )

        return TaskPreviewResponse(
            intent=payload.intent,
            confidence=confidence,
            normalized_input=normalized_input,
            missing_fields=missing_fields,
            ambiguities=draft.ambiguities,
            dataset_matches=dataset_matches,
            warnings=warnings,
        )

    def validate_task(self, payload: TaskCreate) -> None:
        try:
            context = MarketIntelligenceBusinessContext.model_validate(
                payload.business_context
            )
        except ValidationError as exc:
            first = exc.errors()[0]
            field = ".".join(str(item) for item in first.get("loc", ()))
            raise TaskInputValidationError(
                TaskError(
                    code="MARKET_INPUT_INVALID",
                    message=str(first.get("msg", "Market task input is invalid.")),
                    step="validate_input",
                    details={"field": field},
                )
            ) from exc

        request = context.market_intelligence_request
        if request.data_source_mode is not DataSourceMode.FIXED_DATASET:
            raise TaskInputValidationError(
                TaskError(
                    code="DATA_SOURCE_MODE_NOT_SUPPORTED",
                    message="当前市场机会功能只支持 fixed_dataset。",
                    step="validate_input",
                )
            )
        if not self.availability.is_supported(request):
            raise TaskInputValidationError(
                TaskError(
                    code="DATASET_NOT_AVAILABLE",
                    message="没有固定数据集匹配该市场分析请求。",
                    step="validate_input",
                    details={
                        "platform": request.platforms[0],
                        "market": request.market,
                        "category": request.category,
                        "keyword": request.keyword,
                    },
                )
            )

    def _extract(self, user_query: str) -> tuple[MarketInputExtraction, list[PreviewWarning]]:
        warnings: list[PreviewWarning] = []
        if self.llm_client is not None:
            system_prompt, user_prompt = build_input_extraction_prompt(user_query)
            try:
                draft = self.llm_client.generate_structured(
                    messages=[
                        LLMMessage(role="system", content=system_prompt),
                        LLMMessage(role="user", content=user_prompt),
                    ],
                    response_model=MarketInputExtraction,
                )
                return draft.model_copy(
                    update={
                        "market": draft.market or self._fallback_market(user_query),
                        "platform": draft.platform or self._fallback_platform(user_query),
                    }
                ), warnings
            except LLMClientError:
                warnings.append(
                    PreviewWarning(
                        code="INPUT_EXTRACTION_FALLBACK",
                        message="LLM 输入提取不可用，已使用确定性规则。",
                        severity=PreviewWarningSeverity.INFO,
                        field="user_query",
                    )
                )

        product_name = self._fallback_product_name(user_query)
        confidence = 0.8 if self.availability.canonicalize_product(user_query) else 0.45
        return MarketInputExtraction(
            product_name=product_name,
            market=self._fallback_market(user_query),
            platform=self._fallback_platform(user_query),
            confidence=confidence,
        ), warnings

    @staticmethod
    def _fallback_product_name(user_query: str) -> str | None:
        query = " ".join(user_query.strip().split())
        patterns = (
            r"(?:分析|评估|研究|调研)(?:一下)?(?P<product>.+?)(?:是否|值不值得|有没有|市场|，|,|。|目标|$)",
            r"(?:想分析|想做|看看)(?P<product>.+?)(?:是否|值不值得|市场|，|,|。|目标|$)",
        )
        for pattern in patterns:
            match = re.search(pattern, query, flags=re.IGNORECASE)
            if match:
                product = match.group("product").strip(" 的在于")
                if product:
                    return product
        return None

    @staticmethod
    def _market(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().casefold()
        return "US" if normalized in {"us", "usa", "united states", "美国"} else value

    @staticmethod
    def _fallback_market(user_query: str) -> str | None:
        query = user_query.casefold()
        markets = {
            "US": ("美国", "united states", " usa ", " us "),
            "UK": ("英国", "united kingdom", " uk "),
            "DE": ("德国", "germany"),
            "JP": ("日本", "japan"),
        }
        padded = f" {query} "
        for market, aliases in markets.items():
            if any(alias in padded for alias in aliases):
                return market
        return None

    @staticmethod
    def _platform(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().casefold()
        return "amazon" if normalized in {"amazon", "亚马逊"} else normalized

    @staticmethod
    def _fallback_platform(user_query: str) -> str | None:
        query = user_query.casefold()
        platforms = {
            "amazon": ("amazon", "亚马逊"),
            "taobao": ("taobao", "淘宝"),
            "tiktok": ("tiktok", "抖音"),
        }
        for platform, aliases in platforms.items():
            if any(alias in query for alias in aliases):
                return platform
        return None

    @staticmethod
    def _default_warning(field: str, value: str) -> PreviewWarning:
        return PreviewWarning(
            code="DEFAULT_VALUE_APPLIED",
            message=f"未明确提供 {field}，已使用默认值 {value}。",
            severity=PreviewWarningSeverity.INFO,
            field=field,
        )

    @staticmethod
    def _profit_constraints(
        draft: MarketInputExtraction,
        warnings: list[PreviewWarning],
    ) -> ProfitCalculatorParameters | None:
        values = (
            draft.price,
            draft.product_cost,
            draft.platform_fee,
            draft.logistics_cost,
            draft.advertising_cost,
            draft.minimum_margin,
        )
        if all(value is not None for value in values):
            return ProfitCalculatorParameters(
                price=draft.price,
                product_cost=draft.product_cost,
                platform_fee=draft.platform_fee,
                logistics_cost=draft.logistics_cost,
                advertising_cost=draft.advertising_cost,
                minimum_margin=draft.minimum_margin,
                currency=draft.currency or "USD",
            )
        if any(value is not None for value in values):
            warnings.append(
                PreviewWarning(
                    code="PROFIT_INPUT_INCOMPLETE",
                    message="利润参数不完整，本次任务将生成降级利润报告。",
                    field="profit_constraints",
                )
            )
        else:
            warnings.append(
                PreviewWarning(
                    code="PROFIT_INPUT_MISSING",
                    message="未提供利润参数，利润分析将以降级状态返回。",
                    severity=PreviewWarningSeverity.INFO,
                    field="profit_constraints",
                )
            )
        return None


__all__ = ["MarketInputExtraction", "MarketIntelligenceInputExtractor"]
