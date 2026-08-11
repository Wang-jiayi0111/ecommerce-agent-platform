from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TenantAuditRecord(Base):
    __abstract__ = True

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AgentTaskRecord(TenantAuditRecord):
    __tablename__ = "agent_task"

    user_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    intent: Mapped[str] = mapped_column(String(64), index=True)
    user_query: Mapped[str] = mapped_column(Text)
    state_version: Mapped[int] = mapped_column(Integer, default=1)


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


class ApprovalRecord(TenantAuditRecord):
    __tablename__ = "approval"

    task_id: Mapped[str] = mapped_column(String(36), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    result_hash: Mapped[str] = mapped_column(String(64))
    approver_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
