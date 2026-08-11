from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class ToolRequest(BaseModel):
    tenant_id: str
    user_id: str
    trace_id: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolError(BaseModel):
    code: str
    message: str
    retryable: bool = False


class ToolResponse(BaseModel):
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: ToolError | None = None
    source: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    trace_id: str
    degraded: bool = False


class ProfitInput(BaseModel):
    price: float = Field(gt=0)
    product_cost: float = Field(ge=0)
    platform_fee: float = Field(ge=0)
    logistics_cost: float = Field(ge=0)
    advertising_cost: float = Field(ge=0)


def calculate_profit(payload: ProfitInput) -> dict[str, float]:
    total_cost = (
        payload.product_cost
        + payload.platform_fee
        + payload.logistics_cost
        + payload.advertising_cost
    )
    profit = payload.price - total_cost
    return {
        "revenue": payload.price,
        "total_cost": total_cost,
        "profit": profit,
        "margin": round(profit / payload.price, 4),
    }
