import json
import os
import uuid
import httpx
import asyncio
from typing import List
from dotenv import load_dotenv

load_dotenv()

CHROMA_URL = "http://database:8001"
COLLECTION = "lessons"

# Llama (Groq)
from huggingface_hub import InferenceClient

HF_TOKEN = os.environ.get("hf_token")
LLAMA_MODEL = os.environ.get("LLAMA_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
LLAMA_PROVIDER = os.environ.get("LLAMA_PROVIDER", "groq")


client = InferenceClient(
    provider=LLAMA_PROVIDER,
    token=HF_TOKEN
)


async def embed_text(text: str) -> List[float]:
    """
    Получает embedding из Llama-3.3-70B-Instruct через Groq
    """
    try:
        response = client.embeddings.create(
            model=LLAMA_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"[ERROR] Ошибка получения embedding: {e}")
        return [0.0] * 4096   # fallback — пустой вектор


MAX_CHARS = 1600
OVERLAP = 200


def chunk_text(text: str) -> List[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + MAX_CHARS
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - OVERLAP
    return chunks


async def chroma_create_collection():
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{CHROMA_URL}/create_collection",
            json={"name": COLLECTION}
        )


async def chroma_add(ids, embeddings, documents, metadatas):
    payload = {
        "ids": ids,
        "embeddings": embeddings,
        "documents": documents,
        "metadatas": metadatas
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(f"{CHROMA_URL}/add", json=payload)
        if r.status_code != 200:
            print(f"[ERROR] Ошибка записи в ChromaDB: {r.text}")
        else:
            print("[OK] Добавлены элементы:", len(ids))


import asyncio


async def ingest():
    print("=== Загрузка lessons.json ===")
    with open("lessons.json", "r", encoding="utf-8") as f:
        lessons = json.load(f)

    print("Создание коллекции...")
    await chroma_create_collection()

    for item in lessons:
        doc = item.get("document", "")
        metadata = item.get("metadata", {})

        chunks = chunk_text(doc)

        for chunk in chunks:
            emb = await embed_text(chunk)

            chunk_id = "lesson_" + uuid.uuid4().hex[:12]

            await chroma_add(
                ids=[chunk_id],
                embeddings=[emb],
                documents=[chunk],
                metadatas=[metadata]
            )

    print("=== Ingestion completed ===")


if __name__ == "__main__":
    asyncio.run(ingest())