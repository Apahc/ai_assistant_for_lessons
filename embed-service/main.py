import asyncio
import logging

from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


class EmbedRequest(BaseModel):
    texts: list[str] = Field(default_factory=list)


logger = logging.getLogger("embed-service")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

embedding_fn = ONNXMiniLM_L6_V2()
model_ready = False
startup_error: str | None = None
app = FastAPI(title="Lessons Embed Service", version="2.0.0")


def warmup_model() -> None:
    logger.info("Embedding model warmup started")
    embedding_fn(["warmup"])
    logger.info("Embedding model warmup completed")


@app.on_event("startup")
async def startup() -> None:
    global model_ready, startup_error

    logger.info("Preparing embedding model before accepting requests")
    try:
        await asyncio.to_thread(warmup_model)
        model_ready = True
        startup_error = None
    except Exception as exc:
        startup_error = str(exc)
        model_ready = False
        logger.exception("Embedding model warmup failed")
        raise


@app.get("/health")
async def health() -> dict:
    return {"status": "ok" if model_ready else "starting", "model_ready": model_ready, "error": startup_error}


@app.get("/health/ready")
async def health_ready() -> dict:
    if not model_ready:
        raise HTTPException(status_code=503, detail={"status": "starting", "error": startup_error})
    return {"status": "ok", "model_ready": True}


@app.post("/embed")
async def embed(request: EmbedRequest) -> dict:
    if not model_ready:
        raise HTTPException(status_code=503, detail="Embedding model is not ready yet")
    return {"embeddings": embedding_fn(request.texts)}
