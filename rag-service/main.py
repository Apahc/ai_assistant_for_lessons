import httpx
from fastapi import FastAPI, HTTPException

from config import CHROMA_COLLECTION
from schemas import RetrieveRequest, RetrieveResponse
from service import RAGService


service = RAGService()
app = FastAPI(title="Lessons RAG Service", version="2.1.0")


@app.on_event("startup")
async def startup() -> None:
    await service.startup()


@app.get("/")
async def root() -> dict:
    return {"service": "rag-service", "lessons_collection": CHROMA_COLLECTION, "meta_collection": f"{CHROMA_COLLECTION}_meta"}


@app.get("/health")
async def health() -> dict:
    lessons_documents = service.lessons_collection.count() if service.lessons_collection is not None else 0
    meta_documents = service.meta_collection.count() if service.meta_collection is not None else 0
    return {"status": "ok", "lessons_documents": lessons_documents, "meta_documents": meta_documents}


@app.post("/retrieve", response_model=RetrieveResponse)
async def retrieve(request: RetrieveRequest) -> RetrieveResponse:
    try:
        return await service.retrieve(request)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Downstream service error: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
