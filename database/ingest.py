import json
import chromadb
import chromadb.utils.embedding_functions as ef
import os
from hashlib import md5
from typing import List

persist_dir = os.getenv("CHROMA_PERSIST_DIR", "/data/chroma")

client = chromadb.PersistentClient(
    path=persist_dir
)

embed_fn = ef.DefaultEmbeddingFunction()

collection = client.get_or_create_collection(
    name="lessons",
    embedding_function=embed_fn
)


def record_to_text(rec: dict) -> str:
    pieces = []
    for field in ["Наименование_урока", "Описание_проблема",
                  "Описание_решение", "Заключение_эксперта"]:
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
        chunks.append(text[i:i+max_chars])
        i += max_chars - overlap
    return chunks


def ingest_file(path_to_json: str = "/data/lessons.json"):
    with open(path_to_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    ids, docs, metadatas = [], [], []

    for rec in data:
        base_id = (
            rec.get("ID_урока")
            or rec.get("id")
            or md5(json.dumps(rec, ensure_ascii=False).encode()).hexdigest()
        )

        combined = record_to_text(rec)
        chunks = chunk_text(combined)

        for idx, chunk in enumerate(chunks):
            doc_id = f"{base_id}::{idx}"

            ids.append(doc_id)
            docs.append(chunk)
            metadatas.append({
                "doc_id": base_id,
                "chunk_index": idx,
                "Дата_урока": rec.get("Дата_урока"),
                "Проект_организация": rec.get("Проект_организация"),
                "Наименование_урока": rec.get("Наименование_урока")
            })

    collection.add(
        ids=ids,
        documents=docs,
        metadatas=metadatas
    )

    client.persist()
    print(f"Ingested {len(ids)} chunks into Chroma at {persist_dir}")


if __name__ == "__main__":
    ingest_file()
