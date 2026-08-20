# app/composition.py

from app.adapters.commerce import CommerceAdapterRegistry
from app.adapters.commerce.dataset import DatasetAdapter
from app.core.config import Settings
from app.repositories.collection_repository import (
    CollectionRepository,
    SQLAlchemyCollectionRepository,
)
from app.llm.factory import build_structured_llm_client
from app.tools.support.llm_review_analyzer import LLMReviewAnalyzer
from app.tools.support.review_analyzer import PrecomputedReviewAnalyzer
from app.tools.review_insight import ReviewInsightTool
from app.tools.product_search import ProductSearchTool
from app.tools.market_data import MarketDataTool




def build_commerce_adapter_registry(
    settings: Settings,
) -> CommerceAdapterRegistry:
    registry = CommerceAdapterRegistry()

    if settings.environment.lower() in {
        "test",
        "demo",
        "local",
    }:
        amazon_dataset_adapter = DatasetAdapter(
            platform="amazon",
            max_products=settings.market_max_product_limit,
            max_reviews_per_product=(settings.market_max_reviews_per_product),
            public_dataset_ids={
                "amazon_us_portable_coffee_v1",
            },
        )
        registry.register(amazon_dataset_adapter)

    return registry

def build_repository(
    session_factory,
) -> CollectionRepository:
    return SQLAlchemyCollectionRepository(
        session_factory
    )


def build_product_search_tool(
    registry: CommerceAdapterRegistry,
    repository: CollectionRepository,
    settings: Settings,
) -> ProductSearchTool:
    return ProductSearchTool(
        adapter_registry=registry,
        repository=repository,
        max_product_limit=settings.market_max_product_limit,
    )


# def build_review_insight_tool(
#     registry: CommerceAdapterRegistry,
#     repository: CollectionRepository,
#     settings: Settings,
# ) -> ReviewInsightTool:
#     return ReviewInsightTool(
#         adapter_registry=registry,
#         repository=repository,
#         analyzer=PrecomputedReviewAnalyzer(),
#         max_reviews_per_product=settings.market_max_reviews_per_product
#     )

def build_review_insight_tool(
    registry: CommerceAdapterRegistry,
    repository: CollectionRepository,
    settings: Settings,
) -> ReviewInsightTool:
    llm_client = build_structured_llm_client(settings)

    review_analyzer = LLMReviewAnalyzer(
        client=llm_client,
        batch_size=settings.review_llm_batch_size,
        max_content_chars=settings.review_llm_max_content_chars,
        output_language=settings.review_llm_output_language,
    )

    return ReviewInsightTool(
        adapter_registry=registry,
        repository=repository,
        analyzer=review_analyzer,
        max_reviews_per_product=settings.market_max_reviews_per_product,
    )

def build_market_data_tool(
    registry: CommerceAdapterRegistry,
    repository: CollectionRepository,
    setting: Settings,
) -> MarketDataTool:
    return MarketDataTool(
        registry=registry
    )
