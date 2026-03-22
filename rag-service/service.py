import asyncio

import chromadb

from clients import EmbedClient, RerankerClient
from config import (
    CHROMA_COLLECTION,
    CHROMA_HOST,
    CHROMA_PORT,
    EMBED_SERVICE_URL,
    LESSONS_PATH,
    MAX_CHARS,
    OVERLAP,
    PORTAL_META_PATH,
    RETRIEVAL_CANDIDATE_K,
    RERANKER_SERVICE_URL,
)
from context_builder import assemble_context
from data_loader import DataLoader, SourceDocument
from schemas import RetrieveRequest, RetrieveResponse, RetrievedChunk


class RAGService:
    def __init__(self) -> None:
        self.client = None
        self.lessons_collection = None
        self.meta_collection = None
        self.loader = DataLoader(LESSONS_PATH, PORTAL_META_PATH)
        self.embed_client = EmbedClient(EMBED_SERVICE_URL)
        self.reranker_client = RerankerClient(RERANKER_SERVICE_URL)

    async def startup(self) -> None:
        for _ in range(20):
            try:
                self.client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
                self.lessons_collection = self.client.get_or_create_collection(name=CHROMA_COLLECTION)
                self.meta_collection = self.client.get_or_create_collection(name=f"{CHROMA_COLLECTION}_meta")
                await self.ensure_index()
                return
            except Exception:
                await asyncio.sleep(2)
        raise RuntimeError("Chroma is not available")

    def chunk_text(self, text: str) -> list[str]:
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + MAX_CHARS
            chunks.append(text[start:end])
            start = end - OVERLAP
        return chunks

    async def ensure_index(self) -> None:
        if self.lessons_collection is None or self.meta_collection is None:
            return

        if self.lessons_collection.count() == 0:
            await self._index_documents(self.lessons_collection, self.loader.load_lessons())

        if self.meta_collection.count() == 0:
            await self._index_documents(self.meta_collection, self.loader.load_meta())

    async def _index_documents(self, collection, documents: list[SourceDocument]) -> None:
        ids: list[str] = []
        texts: list[str] = []
        metadatas: list[dict] = []

        for document in documents:
            if not document.text:
                continue
            for index, chunk in enumerate(self.chunk_text(document.text)):
                ids.append(f"{document.id}::{index}")
                texts.append(chunk)
                metadatas.append(
                    {
                        **document.metadata,
                        "title": document.title[:500],
                        "source_type": document.source_type,
                        "lesson_id": document.id,
                    }
                )

        if not texts:
            return

        embeddings = await self.embed_client.embed(texts)
        for start in range(0, len(ids), 32):
            end = start + 32
            collection.add(
                ids=ids[start:end],
                documents=texts[start:end],
                metadatas=metadatas[start:end],
                embeddings=embeddings[start:end],
            )

    def build_search_query(self, query: str, session_messages: list[dict]) -> str:
        recent_user_messages = [
            item.get("content", "").strip()
            for item in session_messages[-4:]
            if item.get("role") == "user" and item.get("content")
        ]
        parts = [item for item in recent_user_messages if item]
        parts.append(query.strip())
        unique_parts: list[str] = []
        for part in parts:
            if part and part not in unique_parts:
                unique_parts.append(part)
        return "\n".join(unique_parts)

    async def _query_collection(self, collection, query: str, top_k: int) -> list[dict]:
        if collection is None or collection.count() == 0:
            return []

        query_embedding = (await self.embed_client.embed([query]))[0]
        raw = collection.query(
            query_embeddings=[query_embedding],
            n_results=max(top_k, RETRIEVAL_CANDIDATE_K),
            include=["documents", "metadatas", "distances"],
        )

        ids = raw.get("ids", [[]])[0]
        docs = raw.get("documents", [[]])[0]
        metas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]
        items: list[dict] = []
        for idx, item_id in enumerate(ids):
            metadata = metas[idx] if idx < len(metas) else {}
            st = metadata.get("source_type") or "lesson"
            if st not in ("lesson", "meta"):
                st = "lesson"
            items.append(
                {
                    "id": item_id,
                    "text": docs[idx] if idx < len(docs) else "",
                    "title": metadata.get("title", ""),
                    "source_type": st,
                    "metadata": metadata,
                    "distance": distances[idx] if idx < len(distances) else None,
                }
            )
        return items

    async def _retrieve_lessons(self, search_query: str, top_k: int) -> list[dict]:
        lesson_candidates = await self._query_collection(self.lessons_collection, search_query, top_k)
        return await self.reranker_client.rerank(search_query, lesson_candidates, top_k)

    async def _retrieve_meta(self, search_query: str, mode: str, top_k: int) -> list[dict]:
        meta_top_k = 0
        if mode == "chat":
            meta_top_k = min(2, top_k)
        elif mode == "document":
            meta_top_k = min(2, top_k)
        elif mode == "mail":
            meta_top_k = 1
        elif mode == "search":
            meta_top_k = 0

        if meta_top_k == 0:
            return []

        meta_candidates = await self._query_collection(self.meta_collection, search_query, meta_top_k)
        return await self.reranker_client.rerank(search_query, meta_candidates, meta_top_k)

    async def retrieve(self, request: RetrieveRequest) -> RetrieveResponse:
        if self.lessons_collection is None or self.meta_collection is None:
            raise RuntimeError("Collections are not initialized")

        search_query = self.build_search_query(request.query, request.session_messages)
        lesson_results = await self._retrieve_lessons(search_query, request.top_k)
        meta_results = await self._retrieve_meta(search_query, request.mode, request.top_k)
        context, meta_context, lessons_texts = assemble_context(request.mode, lesson_results, meta_results)

        all_results = lesson_results + meta_results
        return RetrieveResponse(
            mode=request.mode,
            query=request.query,
            search_query=search_query,
            results=[RetrievedChunk(**item) for item in all_results],
            lesson_results=[RetrievedChunk(**item) for item in lesson_results],
            meta_results=[RetrievedChunk(**item) for item in meta_results],
            context=context,
            meta_context=meta_context,
            lessons_texts=lessons_texts,
            lessons_count=len(lesson_results),
            meta_count=len(meta_results),
        )
