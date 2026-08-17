from typing import Protocol

from sqlalchemy.orm import Session, sessionmaker

from app.db.models import (
    CollectionRunRecord,
    EvidenceReferenceRecord,
    ProductSnapshotRecord,
)
from app.modules.market_intelligence.schemas import (
    CollectionRun,
    EvidenceReference,
    NormalizedProduct,
)


class CollectionRepository(Protocol):
    """商品采集结果持久化接口。"""

    def save_product_collection(
        self,
        *,
        run: CollectionRun,
        products: list[NormalizedProduct],
        evidence_refs: list[EvidenceReference],
    ) -> None:
        """保存一次完整的商品采集结果。"""
        ...


class SQLAlchemyCollectionRepository:
    """基于 SQLAlchemy 的商品采集结果持久化实现。"""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self.session_factory = session_factory

    def save_product_collection(
        self,
        *,
        run: CollectionRun,
        products: list[NormalizedProduct],
        evidence_refs: list[EvidenceReference],
    ) -> None:
        """在同一事务中保存采集批次、商品快照和证据信息。"""

        # 入库前检查数据是否属于同一个采集批次
        self._validate_collection(
            run=run,
            products=products,
            evidence_refs=evidence_refs,
        )

        with self.session_factory() as session:
            # 三类数据作为一个整体提交，任一失败则全部回滚
            with session.begin():
                session.add(
                    self._to_run_record(run)
                )

                session.add_all(
                    [
                        self._to_product_record(
                            product=product,
                            run=run,
                        )
                        for product in products
                    ]
                )

                session.add_all(
                    [
                        self._to_evidence_record(
                            evidence=evidence,
                            run=run,
                        )
                        for evidence in evidence_refs
                    ]
                )

    @staticmethod
    def _validate_collection(
        *,
        run: CollectionRun,
        products: list[NormalizedProduct],
        evidence_refs: list[EvidenceReference],
    ) -> None:
        """校验商品和证据是否归属于当前采集批次。"""

        for product in products:
            if product.collection_run_id != run.id:
                raise ValueError(
                    "product.collection_run_id must match run.id"
                )

        for evidence in evidence_refs:
            if evidence.collection_run_id != run.id:
                raise ValueError(
                    "evidence.collection_run_id must match run.id"
                )

    @staticmethod
    def _to_run_record(
        run: CollectionRun,
    ) -> CollectionRunRecord:
        """将采集批次领域模型转换为 ORM 模型。"""

        return CollectionRunRecord(
            id=run.id,
            tenant_id=run.tenant_id,
            trace_id=run.trace_id,
            task_id=run.task_id,
            keyword=run.keyword,
            requested_count=run.requested_count,
            actual_count=run.actual_count,
            status=run.status.value,
            stop_reason=run.stop_reason,
            adapter_version=run.adapter_version,
            parser_version=run.parser_version,
            started_at=run.started_at,
            finished_at=run.finished_at,
        )

    @staticmethod
    def _to_product_record(
        *,
        product: NormalizedProduct,
        run: CollectionRun,
    ) -> ProductSnapshotRecord:
        """将标准商品模型转换为商品快照 ORM 模型。"""

        return ProductSnapshotRecord(
            # 使用 canonical model 中的 snapshot_id 作为数据库主键
            id=product.snapshot_id,
            tenant_id=run.tenant_id,
            trace_id=run.trace_id,
            collection_run_id=product.collection_run_id,
            platform=product.platform,
            market=product.market,
            product_id=product.product_id,
            title=product.title,
            brand=product.brand,
            category=product.category,
            price=product.price,
            currency=product.currency,
            sales_display=product.sales_display,
            sales_value=product.sales_value,
            sales_value_type=product.sales_value_type.value,
            shop_name=product.shop_name,
            rating=product.rating,
            review_count=product.review_count,
            source_ref=product.source_ref,
            source_url=product.source_url,
            source_snapshot_ref=product.source_snapshot_ref,
            source_timestamp=product.source_timestamp,
            ingest_timestamp=product.ingest_timestamp,
            source_type=product.source_type.value,
            data_status=product.data_status.value,
        )

    @staticmethod
    def _to_evidence_record(
        *,
        evidence: EvidenceReference,
        run: CollectionRun,
    ) -> EvidenceReferenceRecord:
        """将证据引用模型转换为 ORM 模型。"""

        return EvidenceReferenceRecord(
            # evidence_id 是证据链中的稳定标识
            id=evidence.evidence_id,
            tenant_id=run.tenant_id,
            trace_id=run.trace_id,
            collection_run_id=evidence.collection_run_id,
            evidence_type=evidence.evidence_type.value,
            data_level=evidence.data_level.value,
            data_source=evidence.data_source,
            platform=evidence.platform,
            product_id=evidence.product_id,
            query_range=evidence.query_range,
            source_timestamp=evidence.source_timestamp,
            ingest_timestamp=evidence.ingest_timestamp,
            tool_call_id=evidence.tool_call_id,
            snapshot_ref=evidence.snapshot_ref,
            sha256=evidence.sha256,
            data_version=evidence.data_version,

            # Pydantic 模型转换为可写入 JSON 字段的字典
            sample_scope=evidence.sample_scope.model_dump(
                mode="json"
            ),
        )