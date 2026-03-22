import re

from fastapi import FastAPI
from pydantic import BaseModel, Field


class RerankRequest(BaseModel):
    query: str
    items: list[dict] = Field(default_factory=list)
    top_k: int = 5


def tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"\w+", (text or "").lower()) if len(token) > 1}


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
    ranked.sort(key=lambda item: item["rerank_score"], reverse=True)
    return {"items": ranked[: request.top_k]}
