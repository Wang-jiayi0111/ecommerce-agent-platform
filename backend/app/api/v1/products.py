from fastapi import APIRouter, Query

router = APIRouter(prefix="/products", tags=["商品"])


@router.get("")
def list_products(keyword: str | None = Query(default=None)) -> dict:
    return {"items": [], "total": 0, "keyword": keyword, "data_status": "unavailable"}
