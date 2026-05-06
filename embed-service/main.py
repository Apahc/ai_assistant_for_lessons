import asyncio
import logging
import os

from fastapi import FastAPI, HTTPException
from fastembed import TextEmbedding
from pydantic import BaseModel, Field

# Модели без PyTorch: fastembed использует ONNX Runtime.
# Список имён: https://qdrant.github.io/fastembed/examples/Supported_Models/
# Смена модели требует полной переиндексации Chroma (другая размерность вектора).
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

EMBEDDING_MODEL = (os.getenv("EMBEDDING_MODEL") or DEFAULT_EMBEDDING_MODEL).strip() or DEFAULT_EMBEDDING_MODEL


class EmbedRequest(BaseModel):
    texts: list[str] = Field(default_factory=list)


logger = logging.getLogger("embed-service")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

embedding_model: TextEmbedding | None = None
model_ready = False
startup_error: str | None = None
app = FastAPI(title="Lessons Embed Service", version="2.1.0")


def _vectors_to_json(embeddings: list) -> list[list[float]]:
    out: list[list[float]] = []
    for vec in embeddings:
        if hasattr(vec, "tolist"):
            row = vec.tolist()
        else:
            row = list(vec)
        out.append([float(x) for x in row])
    return out


def warmup_model() -> None:
    global embedding_model
    logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
    embedding_model = TextEmbedding(model_name=EMBEDDING_MODEL)
    list(embedding_model.embed(["warmup"]))
    logger.info("Embedding model ready (dim inferred from first use)")


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
    return {
        "status": "ok" if model_ready else "starting",
        "model_ready": model_ready,
        "embedding_model": EMBEDDING_MODEL,
        "error": startup_error,
    }


@app.get("/health/ready")
async def health_ready() -> dict:
    if not model_ready:
        raise HTTPException(status_code=503, detail={"status": "starting", "error": startup_error})
    return {"status": "ok", "model_ready": True, "embedding_model": EMBEDDING_MODEL}


@app.post("/embed")
async def embed(request: EmbedRequest) -> dict:
    if not model_ready or embedding_model is None:
        raise HTTPException(status_code=503, detail="Embedding model is not ready yet")
    if not request.texts:
        return {"embeddings": []}

    def run_embed() -> list:
        return list(embedding_model.embed(request.texts))

    raw = await asyncio.to_thread(run_embed)
    return {"embeddings": _vectors_to_json(raw)}
