from fastapi import FastAPI
from pydantic import BaseModel
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import os

persist_dir = os.getenv("CHROMA_PERSIST_DIR", "/data/chroma")
client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=persist_dir))
collection = client.get_or_create_collection(name="lessons")

embed_model = SentenceTransformer("all-MiniLM-L6-v2")

app = FastAPI(title="Vector service (Chroma)")

class QueryIn(BaseModel):
    q: str
    top_k: int = 5
    metadata_filter: dict | None = None

@app.post("/query")
def query(qin: QueryIn):
    q_emb = embed_model.encode(qin.q).tolist()
    if qin.metadata_filter:
        results = collection.query(query_embeddings=[q_emb], n_results=qin.top_k, where=qin.metadata_filter)
    else:
        results = collection.query(query_embeddings=[q_emb], n_results=qin.top_k)
    return results

@app.get("/health")
def health():
    return {"status": "ok", "chroma_persist": persist_dir}