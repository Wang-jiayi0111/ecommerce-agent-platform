from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/knowledge", tags=["知识库"])


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=2)
    filters: dict[str, Any] = Field(default_factory=dict)


@router.post("/search")
def search(payload: KnowledgeSearchRequest) -> dict:
    return {"query": payload.query, "chunks": [], "data_status": "unavailable"}
