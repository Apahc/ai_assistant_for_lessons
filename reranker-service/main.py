import re

from fastapi import FastAPI
from pydantic import BaseModel, Field


class RerankRequest(BaseModel):
    query: str
    items: list[dict] = Field(default_factory=list)
    top_k: int = 5


def tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"\w+", (text or "").lower()) if len(token) > 1}


def _stable_id(item: dict) -> str:
    """Стабильный идентификатор для тай-брейкера сортировки."""
    meta = item.get("metadata") or {}
    return str(
        meta.get("ID_урока")
        or meta.get("id")
        or item.get("id")
        or item.get("text", "")[:64]
    )


app = FastAPI(title="Lessons Reranker Service", version="2.0.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/rerank")
async def rerank(request: RerankRequest) -> dict:
    query_tokens = tokenize(request.query)
    ranked = []
    for item in request.items:
        text_tokens = tokenize(item.get("text", ""))
        overlap = len(query_tokens & text_tokens)
        distance = float(item.get("distance") or 0.0)
        scored = dict(item)
        scored["rerank_score"] = overlap - distance
        ranked.append(scored)
    # Сортировка с детерминированным тай-брейкером по ID урока,
    # чтобы при равных rerank_score порядок не плавал между запросами.
    ranked.sort(key=lambda item: (-item["rerank_score"], _stable_id(item)))
    return {"items": ranked[: request.top_k]}
