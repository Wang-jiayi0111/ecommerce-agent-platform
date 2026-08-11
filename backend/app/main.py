from fastapi import FastAPI

from app.api.v1 import api_v1_router
from app.core import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "电商智能运营 Agent 平台 API。关键结论证据化，节点状态可恢复，"
        "正式商品方案等写操作必须审批且满足幂等约束。"
    ),
    openapi_tags=[
        {"name": "经营总览", "description": "经营指标、预警和审批概览。"},
        {"name": "Agent 任务", "description": "任务创建、状态、事件和取消。"},
        {"name": "审批", "description": "高风险写操作的人工审批。"},
    ],
)
app.include_router(api_v1_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
