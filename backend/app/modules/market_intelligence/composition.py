from dataclasses import dataclass

from app.adapters.commerce import CommerceAdapterRegistry
from app.adapters.commerce.dataset import DatasetAdapter, DatasetCatalog, DatasetRegistry
from app.adapters.commerce.dataset.dataset_adapter import DEFAULT_DATASET_ROOT
from app.agents.market_intelligence_reporter import LLMMarketIntelligenceReporter
from app.core.config import Settings
from app.graph.market_intelligence_graph import (
    CancellationPort,
    CheckpointPort,
    MarketIntelligenceGraph,
    ReportPersistencePort,
    StepExecutionPort,
    ToolExecutionPort,
)
from app.llm.factory import build_structured_llm_client
from app.modules.market_intelligence.dataset_availability import DatasetAvailability
from app.modules.market_intelligence.input_extractor import (
    MarketIntelligenceInputExtractor,
)
from app.modules.market_intelligence.persistence import (
    SQLAlchemyMarketCancellationPort,
    SQLAlchemyMarketCheckpointPort,
    SQLAlchemyStepExecutionPort,
    SQLAlchemyTaskEventPublisher,
    SQLAlchemyToolExecutionPort,
)
from app.modules.market_intelligence.task_executor import (
    MarketIntelligenceTaskExecutor,
)
from app.modules.task_center import TaskInputDispatcher
from app.repositories.collection_repository import (
    CollectionRepository,
    SQLAlchemyCollectionRepository,
)
from app.services.market_intelligence_service import MarketIntelligenceService
from app.tools.market_data import MarketDataTool
from app.tools.product_search import ProductSearchTool
from app.tools.profit_calculator import ProfitCalculatorTool
from app.tools.review_insight import ReviewInsightTool
from app.tools.support.llm_review_analyzer import LLMReviewAnalyzer


@dataclass(frozen=True)
class MarketIntelligenceComponents:
    dataset_registry: DatasetRegistry
    input_extractor: MarketIntelligenceInputExtractor
    executor: MarketIntelligenceTaskExecutor


def build_dataset_registry() -> DatasetRegistry:
    return DatasetCatalog(DEFAULT_DATASET_ROOT).load()


def build_task_input_dispatcher(
    settings: Settings,
    dataset_registry: DatasetRegistry | None = None,
) -> TaskInputDispatcher:
    extractor = build_market_intelligence_input_extractor(
        settings,
        dataset_registry,
    )
    return TaskInputDispatcher({"market_entry": extractor})


def build_market_intelligence_input_extractor(
    settings: Settings,
    dataset_registry: DatasetRegistry | None = None,
) -> MarketIntelligenceInputExtractor:
    llm_settings = (
        settings.llm_provider,
        settings.llm_api_key,
        settings.llm_base_url,
        settings.llm_model,
    )
    llm_client = build_structured_llm_client(settings) if all(llm_settings) else None
    return MarketIntelligenceInputExtractor(
        availability=DatasetAvailability(dataset_registry or build_dataset_registry()),
        llm_client=llm_client,
    )


def build_commerce_adapter_registry(
    settings: Settings,
    dataset_registry: DatasetRegistry | None = None,
) -> CommerceAdapterRegistry:
    registry = CommerceAdapterRegistry()

    if settings.environment.lower() in {
        "test",
        "demo",
        "local",
    }:
        fixed_dataset_registry = dataset_registry or build_dataset_registry()
        amazon_dataset_adapter = DatasetAdapter(
            platform="amazon",
            dataset_registry=fixed_dataset_registry,
            max_products=settings.market_max_product_limit,
            max_reviews_per_product=(settings.market_max_reviews_per_product),
            public_dataset_ids={
                entry.manifest.dataset_id
                for entry in fixed_dataset_registry.all()
                if entry.manifest.platform.casefold() == "amazon"
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
    settings: Settings,
) -> MarketDataTool:
    return MarketDataTool(
        registry=registry
    )


def build_profit_calculator_tool() -> ProfitCalculatorTool:
    return ProfitCalculatorTool()


def build_market_intelligence_graph(
    registry: CommerceAdapterRegistry,
    repository: CollectionRepository,
    settings: Settings,
    *,
    cancellation_port: CancellationPort | None = None,
    checkpoint_port: CheckpointPort | None = None,
    report_persistence_port: ReportPersistencePort | None = None,
    tool_execution_port: ToolExecutionPort | None = None,
    step_execution_port: StepExecutionPort | None = None,
) -> MarketIntelligenceGraph:
    return MarketIntelligenceGraph(
        product_search_tool=build_product_search_tool(
            registry, repository, settings
        ),
        market_data_tool=build_market_data_tool(
            registry, repository, settings
        ),
        review_insight_tool=build_review_insight_tool(
            registry, repository, settings
        ),
        profit_calculator_tool=build_profit_calculator_tool(),
        report_synthesizer=LLMMarketIntelligenceReporter(
            build_structured_llm_client(settings)
        ),
        cancellation_port=cancellation_port,
        checkpoint_port=checkpoint_port,
        report_persistence_port=report_persistence_port,
        tool_execution_port=tool_execution_port,
        step_execution_port=step_execution_port,
        max_retries=2,
    )


def build_market_intelligence_service(
    registry: CommerceAdapterRegistry,
    repository: CollectionRepository,
    settings: Settings,
    *,
    cancellation_port: CancellationPort | None = None,
    checkpoint_port: CheckpointPort | None = None,
    report_persistence_port: ReportPersistencePort | None = None,
    tool_execution_port: ToolExecutionPort | None = None,
    step_execution_port: StepExecutionPort | None = None,
) -> MarketIntelligenceService:
    graph = build_market_intelligence_graph(
        registry,
        repository,
        settings,
        cancellation_port=cancellation_port,
        checkpoint_port=checkpoint_port,
        report_persistence_port=report_persistence_port,
        tool_execution_port=tool_execution_port,
        step_execution_port=step_execution_port,
    )
    return MarketIntelligenceService(graph)


def build_market_intelligence_components(
    settings: Settings,
    session_factory,
) -> MarketIntelligenceComponents:
    dataset_registry = build_dataset_registry()
    commerce_registry = build_commerce_adapter_registry(
        settings,
        dataset_registry,
    )
    repository = build_repository(session_factory)
    event_publisher = SQLAlchemyTaskEventPublisher(session_factory)
    service = build_market_intelligence_service(
        commerce_registry,
        repository,
        settings,
        cancellation_port=SQLAlchemyMarketCancellationPort(
            session_factory, settings.task_lease_seconds
        ),
        checkpoint_port=SQLAlchemyMarketCheckpointPort(session_factory),
        tool_execution_port=SQLAlchemyToolExecutionPort(
            session_factory, event_publisher
        ),
        step_execution_port=SQLAlchemyStepExecutionPort(
            session_factory, event_publisher
        ),
    )
    return MarketIntelligenceComponents(
        dataset_registry=dataset_registry,
        input_extractor=build_market_intelligence_input_extractor(
            settings,
            dataset_registry,
        ),
        executor=MarketIntelligenceTaskExecutor(service),
    )
