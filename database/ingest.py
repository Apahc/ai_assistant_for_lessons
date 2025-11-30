import json
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import os
from hashlib import md5
from typing import List

persist_dir = os.getenv("CHROMA_PERSIST_DIR", "/data/chroma")
client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=persist_dir))
collection = client.get_or_create_collection(name="lessons")

embed_model = SentenceTransformer("all-MiniLM-L6-v2")

def record_to_text(rec: dict) -> str:
    pieces = []
    for field in ["Наименование_урока", "Описание_проблема", "Описание_решение", "Заключение_эксперта"]:
        if rec.get(field):
            pieces.append(f"{field}: {rec.get(field)}")
    meta = f"Проект: {rec.get('Проект_организация','')}; Дата: {rec.get('Дата_урока','')}; Вид: {rec.get('Вид_деятельности','')}"
    pieces.append(meta)
    return "\n".join(pieces)

def chunk_text(text: str, max_chars=1600, overlap=200) -> List[str]:
    if len(text) <= max_chars:
        return [text]
    chunks = []
    i = 0
    while i < len(text):
        chunk = text[i:i+max_chars]
        chunks.append(chunk)
        i += max_chars - overlap
    return chunks

def ingest_file(path_to_json: str = "/data/lessons.json"):
    with open(path_to_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    ids, docs, metadatas, embeddings = [], [], [], []
    for rec in data:
        base_id = rec.get("ID_урока") or rec.get("id") or str(md5(json.dumps(rec, ensure_ascii=False).encode()).hexdigest())
        combined = record_to_text(rec)
        chunks = chunk_text(combined)
        for idx, c in enumerate(chunks):
            doc_id = f"{base_id}::{idx}"
            emb = embed_model.encode(c).tolist()
            ids.append(doc_id)
            docs.append(c)
            metadatas.append({
                "doc_id": base_id,
                "chunk_index": idx,
                "Дата_урока": rec.get("Дата_урока"),
                "Проект_организация": rec.get("Проект_организация"),
                "Наименование_урока": rec.get("Наименование_урока")
            })
            embeddings.append(emb)
    collection.add(ids=ids, documents=docs, metadatas=metadatas, embeddings=embeddings)
    client.persist()
    print(f"Ingested {len(ids)} chunks into Chroma at {persist_dir}")

if __name__ == "__main__":
    ingest_file()
