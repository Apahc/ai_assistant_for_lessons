from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
from fastapi import FastAPI
from pydantic import BaseModel, Field


class EmbedRequest(BaseModel):
    texts: list[str] = Field(default_factory=list)


embedding_fn = ONNXMiniLM_L6_V2()
app = FastAPI(title="Lessons Embed Service", version="2.0.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/embed")
async def embed(request: EmbedRequest) -> dict:
    return {"embeddings": embedding_fn(request.texts)}
