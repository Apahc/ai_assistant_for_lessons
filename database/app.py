from fastapi import FastAPI
from pydantic import BaseModel
import chromadb
import chromadb.utils.embedding_functions as ef
import os

persist_dir = os.getenv("CHROMA_PERSIST_DIR", "/data/chroma")

client = chromadb.PersistentClient(
    path=persist_dir
)

embed_fn = ef.DefaultEmbeddingFunction()

collection = client.get_or_create_collection(
    name="lessons",
    embedding_function=embed_fn
)

app = FastAPI(title="Vector service (Chroma)")


class QueryIn(BaseModel):
    q: str
    top_k: int = 5
    metadata_filter: dict | None = None


@app.post("/query")
def query(qin: QueryIn):
    if qin.metadata_filter:
        results = collection.query(
            query_texts=[qin.q],
            n_results=qin.top_k,
            where=qin.metadata_filter
        )
    else:
        results = collection.query(
            query_texts=[qin.q],
            n_results=qin.top_k
        )
    return results


@app.get("/health")
def health():
    return {"status": "ok", "chroma_persist": persist_dir}