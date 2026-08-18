from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import (
    Base,
    CollectionRunRecord,
    EvidenceReferenceRecord,
    ProductSnapshotRecord,
    ReviewSnapshotRecord,
)
from backend.app.repositories.collection_repository import (
    SQLAlchemyCollectionRepository,
)
from app.modules.market_intelligence.schemas import (
    CollectionRun,
    EvidenceReference,
    NormalizedProduct,
    NormalizedReview,
)


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    factory = sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
    )

    yield factory

    engine.dispose()


def build_product_collection():
    now = datetime.now(UTC)

    run = CollectionRun(
        id="run-product-001",
        task_id="task-product-001",
        trace_id="trace-product-001",
        tenant_id="tenant-001",
        keyword="portable coffee maker",
        requested_count=1,
        actual_count=1,
        status="COMPLETED",
        adapter_version="amazon-dataset-v1",
        parser_version=None,
        started_at=now,
        finished_at=now,
    )

    product = NormalizedProduct(
        snapshot_id="snapshot-001",
        collection_run_id=run.id,
        platform="amazon",
        market="US",
        product_id="B000001",
        title="Portable Coffee Maker",
        brand="Example",
        category="Coffee Makers",
        price=Decimal("49.99"),
        currency="USD",
        sales_display=None,
        sales_value=None,
        sales_value_type="unknown",
        shop_name="Example Store",
        rating=Decimal("4.5"),
        review_count=100,
        source_ref="amazon:B000001",
        source_url=None,
        source_snapshot_ref="products.jsonl#1",
        source_timestamp=now,
        ingest_timestamp=now,
        source_type="fixed_dataset",
        data_status="valid",
    )

    evidence = EvidenceReference(
        evidence_id="evidence-product-001",
        evidence_type="product",
        data_level="D",
        data_source="Amazon Reviews 2023",
        platform="amazon",
        product_id="B000001",
        review_id=None,
        query_range={
            "market": "US",
            "keyword": "portable coffee maker",
        },
        source_timestamp=now,
        ingest_timestamp=now,
        tool_call_id="tool-call-product-001",
        collection_run_id=run.id,
        snapshot_ref="products.jsonl#1",
        sha256="a" * 64,
        data_version="v1",
        sample_scope={
            "market": "US",
            "platforms": ["amazon"],
            "category": "Coffee Makers",
            "keyword": "portable coffee maker",
            "start_time": None,
            "end_time": now,
            "requested_product_count": 1,
            "actual_product_count": 1,
            "actual_review_count": 0,
            "data_source_mode": "fixed_dataset",
        },
    )

    return run, [product], [evidence]


def build_review_collection():
    now = datetime.now(UTC)

    run = CollectionRun(
        id="run-review-001",
        task_id="task-review-001",
        trace_id="trace-review-001",
        tenant_id="tenant-001",
        keyword="portable coffee maker",
        requested_count=1,
        actual_count=1,
        status="COMPLETED",
        adapter_version="amazon-dataset-v1",
        parser_version=None,
        started_at=now,
        finished_at=now,
    )

    review = NormalizedReview(
        review_id="R000001",
        collection_run_id=run.id,
        platform="amazon",
        market="US",
        product_id="B000001",
        content="Easy to use and convenient for travel.",
        rating=Decimal("5.0"),
        review_time=now,
        verified_purchase=True,
        helpful_count=12,
        sentiment="positive",
        themes=[
            "easy to use",
            "portable",
        ],
        source_ref="amazon-review:R000001",
        source_timestamp=now,
        ingest_timestamp=now,
        data_status="valid",
    )

    evidence = EvidenceReference(
        evidence_id="evidence-review-001",
        evidence_type="review",
        data_level="D",
        data_source="Amazon Reviews 2023",
        platform="amazon",
        product_id="B000001",
        review_id="R000001",
        query_range={
            "market": "US",
            "product_id": "B000001",
        },
        source_timestamp=now,
        ingest_timestamp=now,
        tool_call_id="tool-call-review-001",
        collection_run_id=run.id,
        snapshot_ref="reviews.jsonl#1",
        sha256="b" * 64,
        data_version="v1",
        sample_scope={
            "market": "US",
            "platforms": ["amazon"],
            "category": "Coffee Makers",
            "keyword": "portable coffee maker",
            "start_time": None,
            "end_time": now,
            "requested_product_count": 1,
            "actual_product_count": 1,
            "actual_review_count": 1,
            "data_source_mode": "fixed_dataset",
        },
    )

    return run, [review], [evidence]


def test_save_product_collection_persists_all_records(
    session_factory,
):
    repository = SQLAlchemyCollectionRepository(
        session_factory
    )

    run, products, evidence_refs = build_product_collection()

    repository.save_product_collection(
        run=run,
        products=products,
        evidence_refs=evidence_refs,
    )

    with session_factory() as session:
        saved_run = session.get(
            CollectionRunRecord,
            "run-product-001",
        )

        saved_product = session.get(
            ProductSnapshotRecord,
            "snapshot-001",
        )

        saved_evidence = session.get(
            EvidenceReferenceRecord,
            "evidence-product-001",
        )

        assert saved_run is not None
        assert saved_run.tenant_id == "tenant-001"
        assert saved_run.actual_count == 1

        assert saved_product is not None
        assert saved_product.product_id == "B000001"
        assert saved_product.price == Decimal("49.9900")
        assert saved_product.source_type == "fixed_dataset"

        assert saved_evidence is not None
        assert (
            saved_evidence.collection_run_id
            == "run-product-001"
        )
        assert (
            saved_evidence.tool_call_id
            == "tool-call-product-001"
        )
        assert saved_evidence.product_id == "B000001"
        assert saved_evidence.review_id is None
        assert saved_evidence.sample_scope["market"] == "US"


def test_save_product_collection_rolls_back_entire_transaction(
    session_factory,
):
    repository = SQLAlchemyCollectionRepository(
        session_factory
    )

    run, products, evidence_refs = build_product_collection()

    duplicate = products[0].model_copy(
        update={
            "snapshot_id": "snapshot-002",
        }
    )

    with pytest.raises(IntegrityError):
        repository.save_product_collection(
            run=run,
            products=[
                products[0],
                duplicate,
            ],
            evidence_refs=evidence_refs,
        )

    with session_factory() as session:
        run_count = session.scalar(
            select(func.count()).select_from(
                CollectionRunRecord
            )
        )

        product_count = session.scalar(
            select(func.count()).select_from(
                ProductSnapshotRecord
            )
        )

        evidence_count = session.scalar(
            select(func.count()).select_from(
                EvidenceReferenceRecord
            )
        )

        assert run_count == 0
        assert product_count == 0
        assert evidence_count == 0


def test_save_review_collection_persists_all_records(
    session_factory,
):
    repository = SQLAlchemyCollectionRepository(
        session_factory
    )

    run, reviews, evidence_refs = build_review_collection()

    repository.save_review_collection(
        run=run,
        reviews=reviews,
        evidence_refs=evidence_refs,
    )

    with session_factory() as session:
        saved_run = session.get(
            CollectionRunRecord,
            "run-review-001",
        )

        saved_review = session.scalar(
            select(ReviewSnapshotRecord).where(
                ReviewSnapshotRecord.collection_run_id
                == "run-review-001",
                ReviewSnapshotRecord.review_id
                == "R000001",
            )
        )

        saved_evidence = session.get(
            EvidenceReferenceRecord,
            "evidence-review-001",
        )

        assert saved_run is not None
        assert saved_run.tenant_id == "tenant-001"
        assert saved_run.trace_id == "trace-review-001"
        assert saved_run.actual_count == 1

        assert saved_review is not None
        assert saved_review.platform == "amazon"
        assert saved_review.market == "US"
        assert saved_review.product_id == "B000001"
        assert saved_review.review_id == "R000001"
        assert (
            saved_review.content
            == "Easy to use and convenient for travel."
        )
        assert saved_review.rating == Decimal("5.0000")
        assert saved_review.verified_purchase is True
        assert saved_review.helpful_count == 12
        assert saved_review.sentiment == "positive"
        assert saved_review.themes == [
            "easy to use",
            "portable",
        ]
        assert saved_review.data_status == "valid"

        assert saved_evidence is not None
        assert (
            saved_evidence.collection_run_id
            == "run-review-001"
        )
        assert saved_evidence.product_id == "B000001"
        assert saved_evidence.review_id == "R000001"
        assert (
            saved_evidence.evidence_type
            == "review"
        )
        assert (
            saved_evidence.tool_call_id
            == "tool-call-review-001"
        )
        assert saved_evidence.sample_scope["market"] == "US"
        assert (
            saved_evidence.sample_scope[
                "actual_review_count"
            ]
            == 1
        )


def test_save_review_collection_rolls_back_entire_transaction(
    session_factory,
):
    repository = SQLAlchemyCollectionRepository(
        session_factory
    )

    run, reviews, evidence_refs = build_review_collection()

    duplicate = reviews[0].model_copy(
        update={
            "content": "Duplicate review record.",
        }
    )

    with pytest.raises(IntegrityError):
        repository.save_review_collection(
            run=run,
            reviews=[
                reviews[0],
                duplicate,
            ],
            evidence_refs=evidence_refs,
        )

    with session_factory() as session:
        run_count = session.scalar(
            select(func.count()).select_from(
                CollectionRunRecord
            )
        )

        review_count = session.scalar(
            select(func.count()).select_from(
                ReviewSnapshotRecord
            )
        )

        evidence_count = session.scalar(
            select(func.count()).select_from(
                EvidenceReferenceRecord
            )
        )

        assert run_count == 0
        assert review_count == 0
        assert evidence_count == 0