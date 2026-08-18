import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.commerce.adapter_registry import (
    CommerceAdapterRegistry,
)
from app.adapters.commerce.dataset.dataset_adapter import (
    DatasetAdapter,
)
from app.db.models import Base
from app.repositories.collection_repository import (
    SQLAlchemyCollectionRepository,
)
from app.tools.contracts import ToolRequest
from app.tools.review_analyzer import (
    PrecomputedReviewAnalyzer,
)
from app.tools.review_insight import (
    ReviewInsightTool,
)


DATASET_ID = "amazon_us_portable_coffee_v1"

BACKEND_DIR = Path(__file__).resolve().parents[1]

DATASET_ROOT = (
    BACKEND_DIR
    / "data"
    / "market_intelligence"
)

DATASET_DIR = (
    DATASET_ROOT
    / DATASET_ID
)

OUTPUT_DIR = (
    BACKEND_DIR
    / "tests"
    / "output"
)

TEST_DB_PATH = (
    OUTPUT_DIR
    / "review_insight_test.db"
)

# reviews.jsonl 中真实存在，并且有多条评论
TEST_PRODUCT_ID = "B0BMV7X9YJ"

REVIEW_LIMIT = 5


def load_manifest() -> dict:
    manifest_path = (
        DATASET_DIR
        / "manifest.json"
    )

    assert manifest_path.is_file(), (
        f"Dataset manifest does not exist: "
        f"{manifest_path}"
    )

    return json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )


@pytest.fixture
def real_database():
    """
    每次测试前重新创建 SQLite 数据库。

    测试结束后不删除，
    方便手动使用 SQLite Viewer 检查。
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # 删除上一次测试数据库
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    engine = create_engine(
        f"sqlite:///{TEST_DB_PATH.as_posix()}",
    )

    # 使用项目真实 ORM 创建所有表
    Base.metadata.create_all(engine)

    session_factory = sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
    )

    yield engine, session_factory

    engine.dispose()


def build_review_insight_tool(
    session_factory,
) -> ReviewInsightTool:

    # 真实 Repository
    repository = (
        SQLAlchemyCollectionRepository(
            session_factory
        )
    )

    # 真实 DatasetAdapter
    adapter = DatasetAdapter(
        platform="amazon",
        dataset_root=DATASET_ROOT,
        public_dataset_ids={
            DATASET_ID,
        },
    )

    registry = CommerceAdapterRegistry()

    registry.register(adapter)

    return ReviewInsightTool(
        adapter_registry=registry,
        repository=repository,
        analyzer=PrecomputedReviewAnalyzer(),
        max_reviews_per_product=50,
    )


def build_request() -> ToolRequest:
    manifest = load_manifest()

    return ToolRequest(
        tenant_id="test-tenant",
        user_id="test-user",
        trace_id="trace-review-persistence-001",
        parameters={
            "schema_version": "1.0",
            "task_id": "task-review-persistence-001",
            "tool_call_id": (
                "tool-call-review-persistence-001"
            ),
            "platform": manifest["platform"],
            "data_source_mode": "fixed_dataset",
            "market": manifest["market"],
            "category": manifest["category"],
            "keyword": manifest["keyword"],
            "product_ids": [
                TEST_PRODUCT_ID,
            ],
            "review_limit_per_product": (
                REVIEW_LIMIT
            ),
        },
    )


def test_review_insight_real_persistence(
    real_database,
):
    engine, session_factory = real_database

    tool = build_review_insight_tool(
        session_factory
    )

    request = build_request()

    # 真正执行 ReviewInsightTool
    response = tool.execute(request)

    # -----------------------------
    # 1. 验证 Tool 执行成功
    # -----------------------------

    assert response.success is True, (
        response.error.model_dump()
        if response.error
        else response.model_dump()
    )

    assert response.error is None

    assert (
        response.source
        == "amazon:fixed_dataset"
    )

    assert (
        response.data["status"]
        == "COMPLETED"
    )

    reviews = response.data["reviews"]

    assert len(reviews) == REVIEW_LIMIT

    assert all(
        review["product_id"]
        == TEST_PRODUCT_ID
        for review in reviews
    )

    # -----------------------------
    # 2. 验证数据库文件真的存在
    # -----------------------------

    assert TEST_DB_PATH.exists()

    assert TEST_DB_PATH.stat().st_size > 0

    # -----------------------------
    # 3. 验证真实数据库表存在
    # -----------------------------

    inspector = inspect(engine)

    table_names = set(
        inspector.get_table_names()
    )

    assert "collection_run" in table_names
    assert "review_snapshot" in table_names
    assert "evidence_reference" in table_names

    # -----------------------------
    # 4. 验证 collection_run 落库
    # -----------------------------

    with engine.connect() as connection:
        run_count = connection.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM collection_run
                """
            )
        )

        assert run_count == 1

        run_row = connection.execute(
            text(
                """
                SELECT
                    id,
                    task_id,
                    trace_id,
                    tenant_id,
                    keyword,
                    requested_count,
                    actual_count,
                    status
                FROM collection_run
                LIMIT 1
                """
            )
        ).mappings().one()

        assert (
            run_row["task_id"]
            == "task-review-persistence-001"
        )

        assert (
            run_row["trace_id"]
            == "trace-review-persistence-001"
        )

        assert (
            run_row["tenant_id"]
            == "test-tenant"
        )

        assert (
            run_row["requested_count"]
            == REVIEW_LIMIT
        )

        assert (
            run_row["actual_count"]
            == REVIEW_LIMIT
        )

        assert (
            run_row["status"]
            == "COMPLETED"
        )

    # -----------------------------
    # 5. 验证 review_snapshot 落库
    # -----------------------------

    with engine.connect() as connection:
        review_count = connection.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM review_snapshot
                """
            )
        )

        assert review_count == REVIEW_LIMIT

        saved_reviews = connection.execute(
            text(
                """
                SELECT
                    collection_run_id,
                    platform,
                    market,
                    product_id,
                    review_id,
                    content,
                    rating,
                    source_ref,
                    source_snapshot_ref
                FROM review_snapshot
                ORDER BY review_id
                """
            )
        ).mappings().all()

        assert len(saved_reviews) == REVIEW_LIMIT

        assert all(
            row["platform"] == "amazon"
            for row in saved_reviews
        )

        assert all(
            row["market"] == "US"
            for row in saved_reviews
        )

        assert all(
            row["product_id"]
            == TEST_PRODUCT_ID
            for row in saved_reviews
        )

        assert all(
            row["content"]
            for row in saved_reviews
        )

        assert all(
            row["source_ref"]
            for row in saved_reviews
        )

        assert all(
            row["source_snapshot_ref"]
            for row in saved_reviews
        )

    # -----------------------------
    # 6. 验证 Evidence 落库
    # -----------------------------

    with engine.connect() as connection:
        evidence_count = connection.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM evidence_reference
                WHERE evidence_type = 'review'
                """
            )
        )

        assert evidence_count == REVIEW_LIMIT

        evidence_rows = connection.execute(
            text(
                """
                SELECT
                    collection_run_id,
                    evidence_type,
                    platform,
                    product_id,
                    review_id,
                    tool_call_id,
                    snapshot_ref,
                    sha256
                FROM evidence_reference
                WHERE evidence_type = 'review'
                ORDER BY review_id
                """
            )
        ).mappings().all()

        assert len(evidence_rows) == REVIEW_LIMIT

        assert all(
            row["platform"] == "amazon"
            for row in evidence_rows
        )

        assert all(
            row["product_id"]
            == TEST_PRODUCT_ID
            for row in evidence_rows
        )

        assert all(
            row["tool_call_id"]
            == "tool-call-review-persistence-001"
            for row in evidence_rows
        )

        assert all(
            row["snapshot_ref"]
            for row in evidence_rows
        )

        assert all(
            row["sha256"]
            for row in evidence_rows
        )

    # -----------------------------
    # 7. 验证 Review ↔ Evidence
    # -----------------------------

    review_by_id = {
        row["review_id"]: row
        for row in saved_reviews
    }

    evidence_by_review_id = {
        row["review_id"]: row
        for row in evidence_rows
    }

    assert (
        set(review_by_id)
        == set(evidence_by_review_id)
    )

    for review_id, review in (
        review_by_id.items()
    ):
        evidence = (
            evidence_by_review_id[
                review_id
            ]
        )

        assert (
            evidence["collection_run_id"]
            == review["collection_run_id"]
        )

        assert (
            evidence["product_id"]
            == review["product_id"]
        )

        assert (
            evidence["snapshot_ref"]
            == review["source_snapshot_ref"]
        )

    # -----------------------------
    # 8. 验证 ReviewInsight
    # -----------------------------

    insight = response.data[
        "review_insight"
    ]

    # 当前还没有真正的评论文本分析器
    assert insight["status"] == "partial"

    assert insight["themes"] == []
    assert insight["pain_points"] == []
    assert insight["unmet_needs"] == []

    assert response.degraded is True

    print()
    print(
        "Test database created at:"
    )
    print(TEST_DB_PATH)