from datetime import datetime

from pydantic import BaseModel, Field


class MetricCard(BaseModel):
    code: str
    label: str
    value: float
    display_value: str
    change_display: str
    trend: str = Field(pattern="^(up|down|flat)$")


class OperatingAlert(BaseModel):
    severity: str = Field(pattern="^(critical|high|medium|low)$")
    title: str
    description: str
    module: str
    occurred_at: datetime


class DashboardOverview(BaseModel):
    shop_id: str
    data_cutoff: datetime
    metrics: list[MetricCard]
    alerts: list[OperatingAlert]
    pending_approval_count: int
