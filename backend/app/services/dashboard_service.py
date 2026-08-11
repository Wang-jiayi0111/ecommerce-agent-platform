from datetime import UTC, datetime

from app.schemas.dashboard import DashboardOverview, MetricCard, OperatingAlert


class DashboardService:
    """电商经营概览；M1 接入销售与库存数据服务后替换演示数据。"""

    def overview(self, shop_id: str, pending_approval_count: int) -> DashboardOverview:
        now = datetime.now(UTC)
        return DashboardOverview(
            shop_id=shop_id,
            data_cutoff=now,
            metrics=[
                MetricCard(
                    code="gmv",
                    label="今日 GMV",
                    value=128640,
                    display_value="¥128,640",
                    change_display="较昨日 +8.4%",
                    trend="up",
                ),
                MetricCard(
                    code="orders",
                    label="订单量",
                    value=1864,
                    display_value="1,864",
                    change_display="较昨日 +5.2%",
                    trend="up",
                ),
                MetricCard(
                    code="conversion",
                    label="转化率",
                    value=3.86,
                    display_value="3.86%",
                    change_display="较昨日 -0.3%",
                    trend="down",
                ),
                MetricCard(
                    code="inventory_risk",
                    label="库存风险 SKU",
                    value=12,
                    display_value="12",
                    change_display="其中 3 个高风险",
                    trend="flat",
                ),
            ],
            alerts=[
                OperatingAlert(
                    severity="high",
                    title="核心 SKU 转化率连续三日下降",
                    description="需核验流量结构、Listing 变更与竞品价格变化。",
                    module="运营诊断",
                    occurred_at=now,
                ),
                OperatingAlert(
                    severity="medium",
                    title="便携咖啡机安全库存不足",
                    description="当前可售天数低于计划补货周期，建议复核在途库存。",
                    module="库存",
                    occurred_at=now,
                ),
            ],
            pending_approval_count=pending_approval_count,
        )
