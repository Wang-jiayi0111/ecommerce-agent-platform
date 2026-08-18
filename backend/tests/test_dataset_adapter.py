import json
from pathlib import Path

import pytest

from backend.app.adapters.commerce.commerce_adapter_base import AdapterContext, AdapterError
from backend.app.adapters.commerce.dataset.dataset_adapter import DatasetAdapter
from app.modules.market_intelligence.schemas import (
    CollectionStatus,
    ProductSearchRequest,
    ReviewSearchRequest,
)


DATASET_ROOT = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "market_intelligence"
)

DATASET_DIR = (
    DATASET_ROOT
    / "amazon_us_portable_coffee_v1"
)


@pytest.fixture
def manifest() -> dict:
    return json.loads(
        (DATASET_DIR / "manifest.json").read_text(
            encoding="utf-8"
        )
    )


@pytest.fixture
def context() -> AdapterContext:
    return AdapterContext(
        tenant_id="test-tenant",
        user_id="test-user",
        trace_id="trace-001",
        task_id="task-001",
        tool_call_id="tool-call-001",
    )


@pytest.fixture
def adapter(manifest) -> DatasetAdapter:
    return DatasetAdapter(
        platform="amazon",
        dataset_root=DATASET_ROOT,
        public_dataset_ids={
            manifest["dataset_id"],
        },
    )


def test_capabilities_support_reviews(adapter):
    capabilities = adapter.capabilities()

    assert capabilities.platform == "amazon"
    assert capabilities.supports_products is True
    assert capabilities.supports_reviews is True
    assert capabilities.max_products > 0
    assert capabilities.max_reviews_per_product > 0


def test_search_products_returns_products(
    adapter,
    manifest,
    context,
):
    request = ProductSearchRequest(
        platform="amazon",
        market=manifest["market"],
        category=manifest["category"],
        keyword=manifest["keyword"],
        product_limit=3,
        sort_by="default",
    )

    result = adapter.search_products(
        request,
        context,
    )

    assert len(result.data) > 0
    assert len(result.data) <= 3

    assert result.run.actual_count == len(result.data)

    assert len(result.evidence_refs) == len(result.data)

    for product, evidence in zip(
        result.data,
        result.evidence_refs,
        strict=True,
    ):
        assert product.platform == "amazon"
        assert product.collection_run_id == result.run.id

        assert evidence.product_id == product.product_id
        assert (
            evidence.collection_run_id
            == result.run.id
        )

        assert (
            evidence.snapshot_ref
            == product.source_snapshot_ref
        )

def first_review_product_id() -> str:
    review_path = DATASET_DIR / "reviews.jsonl"

    for line in review_path.read_text(
        encoding="utf-8"
    ).splitlines():
        if not line.strip():
            continue

        raw = json.loads(line)
        product_id = raw.get("parent_asin")

        if product_id:
            return product_id

    raise AssertionError(
        "reviews.jsonl contains no product_id"
    )

def test_search_reviews_returns_requested_reviews(
    adapter,
    manifest,
    context,
):
    product_id = first_review_product_id()

    request = ReviewSearchRequest(
        platform="amazon",
        market=manifest["market"],
        category=manifest["category"],
        keyword=manifest["keyword"],
        product_ids=[product_id],
        review_limit_per_product=3,
    )

    result = adapter.search_reviews(
        request,
        context,
    )

    assert len(result.data) == 3

    assert result.run.requested_count == 3
    assert result.run.actual_count == 3
    assert (
        result.run.status
        is CollectionStatus.COMPLETED
    )

    assert result.degraded is False
    assert len(result.evidence_refs) == 3

    for review, evidence in zip(
        result.data,
        result.evidence_refs,
        strict=True,
    ):
        assert review.product_id == product_id
        assert review.platform == "amazon"

        assert (
            review.collection_run_id
            == result.run.id
        )

        assert review.source_snapshot_ref
        assert "reviews.jsonl#L" in (
            review.source_snapshot_ref
        )

        assert evidence.review_id == review.review_id
        assert evidence.product_id == review.product_id

        assert (
            evidence.snapshot_ref
            == review.source_snapshot_ref
        )

def review_product_ids(limit: int) -> list[str]:
    review_path = DATASET_DIR / "reviews.jsonl"

    product_ids = []

    for line in review_path.read_text(
        encoding="utf-8"
    ).splitlines():
        if not line.strip():
            continue

        raw = json.loads(line)
        product_id = raw.get("parent_asin")

        if (
            product_id
            and product_id not in product_ids
        ):
            product_ids.append(product_id)

        if len(product_ids) >= limit:
            break

    return product_ids



def test_search_reviews_limits_each_product(
    adapter,
    manifest,
    context,
):
    product_ids = review_product_ids(2)

    assert len(product_ids) == 2

    request = ReviewSearchRequest(
        platform="amazon",
        market=manifest["market"],
        category=manifest["category"],
        keyword=manifest["keyword"],
        product_ids=product_ids,
        review_limit_per_product=2,
    )

    result = adapter.search_reviews(
        request,
        context,
    )

    counts = {
        product_id: 0
        for product_id in product_ids
    }

    for review in result.data:
        counts[review.product_id] += 1

    assert counts[product_ids[0]] == 2
    assert counts[product_ids[1]] == 2

    assert result.run.requested_count == 4
    assert result.run.actual_count == 4
    assert (
        result.run.status
        is CollectionStatus.COMPLETED
    )

def test_search_reviews_is_partial_when_one_product_missing(
    adapter,
    manifest,
    context,
):
    existing_product_id = first_review_product_id()

    request = ReviewSearchRequest(
        platform="amazon",
        market=manifest["market"],
        category=manifest["category"],
        keyword=manifest["keyword"],
        product_ids=[
            existing_product_id,
            "PRODUCT_DOES_NOT_EXIST",
        ],
        review_limit_per_product=2,
    )

    result = adapter.search_reviews(
        request,
        context,
    )

    assert result.run.requested_count == 4
    assert result.run.actual_count == 2

    assert (
        result.run.status
        is CollectionStatus.PARTIAL
    )

    assert (
        result.run.stop_reason
        == "REQUESTED_COUNT_NOT_REACHED"
    )

    assert result.degraded is True



def test_search_reviews_rejects_limit_over_adapter_max(
    manifest,
    context,
):
    adapter = DatasetAdapter(
        platform="amazon",
        dataset_root=DATASET_ROOT,
        public_dataset_ids={
            manifest["dataset_id"],
        },
        max_reviews_per_product=2,
    )

    request = ReviewSearchRequest(
        platform="amazon",
        market=manifest["market"],
        category=manifest["category"],
        keyword=manifest["keyword"],
        product_ids=[
            first_review_product_id(),
        ],
        review_limit_per_product=3,
    )

    with pytest.raises(AdapterError) as exc_info:
        adapter.search_reviews(
            request,
            context,
        )

    assert exc_info.value.code == "INVALID_ARGUMENT"