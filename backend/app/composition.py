# app/composition.py

from app.adapters.commerce import CommerceAdapterRegistry
from app.adapters.commerce.dataset import DatasetAdapter
from app.core.config import Settings
from backend.app.repositories.collection_repository import (
    CollectionRepository,
    SQLAlchemyCollectionRepository,
)
from app.tools.review_analyzer import PrecomputedReviewAnalyzer
from app.tools.review_insight import ReviewInsightTool
from app.tools.product_search import ProductSearchTool


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


def build_review_insight_tool(
    registry: CommerceAdapterRegistry,
    repository: CollectionRepository,
    settings: Settings,
) -> ReviewInsightTool:
    return ReviewInsightTool(
        adapter_registry=registry,
        repository=repository,
        analyzer=PrecomputedReviewAnalyzer(),
        max_reviews_per_product=settings.market_max_reviews_per_product
    )