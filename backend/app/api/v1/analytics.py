from fastapi import APIRouter, Query

router = APIRouter(prefix="/analytics", tags=["分析"])


@router.get("/market")
def market(category: str, market: str = "US") -> dict:
    return {"category": category, "market": market, "data_status": "unavailable", "source": None}


@router.get("/operations")
def operations(shop_id: str, sku: str | None = Query(default=None)) -> dict:
    return {"shop_id": shop_id, "sku": sku, "data_status": "unavailable", "source": None}
