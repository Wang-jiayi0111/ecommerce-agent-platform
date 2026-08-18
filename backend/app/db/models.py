from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from decimal import Decimal
from sqlalchemy import (
    JSON,
    Boolean, 
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TenantAuditRecord(Base):
    __abstract__ = True

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class AgentTaskRecord(TenantAuditRecord):
    __tablename__ = "agent_task"

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    intent: Mapped[str] = mapped_column(String(64), index=True)
    user_query: Mapped[str] = mapped_column(Text)
    current_step: Mapped[str | None] = mapped_column(String(96), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    state_version: Mapped[int] = mapped_column(Integer, default=1)
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    result_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    approval_status: Mapped[str] = mapped_column(String(32), index=True)
    approval_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approver_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    events: Mapped[list[str]] = mapped_column(JSON, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class AgentStepRecord(TenantAuditRecord):
    __tablename__ = "agent_step"

    task_id: Mapped[str] = mapped_column(String(36), index=True)
    step_name: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)


class ToolCallRecord(TenantAuditRecord):
    __tablename__ = "tool_call"

    task_id: Mapped[str] = mapped_column(String(36), index=True)
    tool_name: Mapped[str] = mapped_column(String(96), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)

class CollectionRunRecord(TenantAuditRecord):
    __tablename__ = "collection_run"

    task_id: Mapped[str] = mapped_column(String(64), index=True)
    keyword: Mapped[str] = mapped_column(String(255), index=True)
    requested_count: Mapped[int] = mapped_column(Integer)
    actual_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), index=True)
    stop_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    adapter_version: Mapped[str] = mapped_column(String(64))
    parser_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ProductSnapshotRecord(TenantAuditRecord):
    __tablename__ = "product_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "collection_run_id",
            "platform",
            "product_id",
            name="uq_product_snapshot_run_platform_product",
        ),
    )

    collection_run_id: Mapped[str] = mapped_column(
        ForeignKey("collection_run.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(32), index=True)
    market: Mapped[str] = mapped_column(String(32), index=True)
    product_id: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(Text)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    currency: Mapped[str] = mapped_column(String(3))
    sales_display: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sales_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sales_value_type: Mapped[str] = mapped_column(String(32))
    shop_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_ref: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_snapshot_ref: Mapped[str] = mapped_column(Text)
    source_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ingest_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_type: Mapped[str] = mapped_column(String(32), index=True)
    data_status: Mapped[str] = mapped_column(String(32), index=True)

class ReviewSnapshotRecord(TenantAuditRecord):
    __tablename__ = "review_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "collection_run_id",
            "platform",
            "review_id",
            name="uq_review_snapshot_run_platform_review",
        ),
    )

    # 本条评论属于哪一次采集
    collection_run_id: Mapped[str] = mapped_column(
        ForeignKey("collection_run.id", ondelete="CASCADE"), index=True,
    )

    # 评论所属平台与市场
    platform: Mapped[str] = mapped_column(String(32), index=True)
    market: Mapped[str] = mapped_column(String(32), index=True)

    # 评论自身及所属商品
    review_id: Mapped[str] = mapped_column(String(128), index=True)
    product_id: Mapped[str] = mapped_column(String(128), index=True)

    # 评论正文
    content: Mapped[str] = mapped_column(Text)

    # 评论原始属性
    rating: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    review_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_purchase: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    helpful_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 后续评论分析可能产生的字段
    sentiment: Mapped[str | None] = mapped_column(String(32),nullable=True)
    themes: Mapped[list[str]] = mapped_column(JSON, default=list)

    # 数据来源与时间信息
    source_ref: Mapped[str] = mapped_column(Text)
    source_snapshot_ref: Mapped[str] = mapped_column(Text)
    source_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ingest_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # 数据质量状态
    data_status: Mapped[str] = mapped_column(String(32), index=True)


class EvidenceReferenceRecord(TenantAuditRecord):
    __tablename__ = "evidence_reference"

    collection_run_id: Mapped[str] = mapped_column(
        ForeignKey("collection_run.id", ondelete="CASCADE"), index=True
    )
    evidence_type: Mapped[str] = mapped_column(String(32), index=True)
    data_level: Mapped[str] = mapped_column(String(16))
    data_source: Mapped[str] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    product_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    review_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    query_range: Mapped[dict] = mapped_column(JSON)
    source_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ingest_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    tool_call_id: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_ref: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    data_version: Mapped[str] = mapped_column(String(128))
    sample_scope: Mapped[dict] = mapped_column(JSON)


class ApprovalRecord(TenantAuditRecord):
    __tablename__ = "approval"

    task_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(32), index=True)
    result_hash: Mapped[str] = mapped_column(String(64))
    approver_id: Mapped[str] = mapped_column(String(64), index=True)
    approver_roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class UserAccountRecord(Base):
    __tablename__ = "user_account"
    __table_args__ = (UniqueConstraint("tenant_id", "username", name="uq_user_tenant_username"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    username: Mapped[str] = mapped_column(String(64), index=True)
    display_name: Mapped[str] = mapped_column(String(96))
    password_hash: Mapped[str] = mapped_column(String(255))
    roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class CaptchaChallengeRecord(Base):
    __tablename__ = "captcha_challenge"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    target_x: Mapped[int] = mapped_column(Integer)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    login_consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AuthSessionRecord(Base):
    __tablename__ = "auth_session"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
