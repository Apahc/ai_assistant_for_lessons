from fastapi import FastAPI
import chromadb
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.environ['CHROMA_TELEMETRY_ENABLED'] = 'false'

def get_collection():
    client = chromadb.PersistentClient(path=os.getenv("CHROMA_PERSIST_DIR", "/data/chroma"))
    embedding_fn = ONNXMiniLM_L6_V2()
    return client.get_or_create_collection(
        name="lessons",
        embedding_function=embedding_fn
    )

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/collection-info")
def collection_info():
    try:
        collection = get_collection()
        count = collection.count()
        return {
            "collection_name": "lessons",
            "documents_count": count
        }
    except Exception as e:
        return {"error": f"Ошибка: {str(e)}"}

@app.get("/search")
def search(q: str, n_results: int = 5):
    try:
        collection = get_collection()
        results = collection.query(
            query_texts=[q],
            n_results=n_results,
            include=["metadatas", "documents", "distances"]
        )
        formatted_results = []
        for i in range(len(results["ids"][0])):
            formatted_results.append({
                "id": results["ids"][0][i],
                "metadata": results["metadatas"][0][i],
                "document": results["documents"][0][i],
                "cosine_distance": float(results["distances"][0][i]) if results["distances"] else None
            })
        return {
            "query": q,
            "total_results": len(formatted_results),
            "results": formatted_results
        }
    except Exception as e:
        return {"error": f"Ошибка поиска: {str(e)}"}