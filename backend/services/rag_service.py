"""
RAG сервис для работы с ChromaDB (через HTTP API, совместимый с вашим database/app.py)
"""
import httpx
import asyncio
from typing import List, Optional, Dict, Any
from config import CHROMA_HOST, CHROMA_PORT, CHROMA_COLLECTION_NAME, RAG_TOP_K
from models.schemas import LessonChunk, QueryRequest, QueryResponse


class RAGService:
    """Сервис для работы с векторной базой данных ChromaDB (через HTTP эндпоинты /search и /ping)"""
    
    def __init__(self):
        self.chroma_url = f"http://{CHROMA_HOST}:{CHROMA_PORT}"
        self.collection_name = CHROMA_COLLECTION_NAME

    async def _query_chroma(
        self, 
        query: str, 
        top_k: int = RAG_TOP_K,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Выполняет запрос к вашему HTTP-слою ChromaDB (app.py -> /search).
        Ожидаемый ответ: JSON с полями: query, total_results, results (список элементов с id, metadata, document, cosine_distance)
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {"q": query, "n_results": top_k}
                # Если у вас в /search есть поддержка фильтрации через параметры — можно добавить их, 
                # но ваш текущий /search принимает q и n_results.
                response = await client.get(f"{self.chroma_url}/search", params=params)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"Ошибка при запросе к ChromaDB: {e}")
            return {}

    async def search(
        self, 
        query: str,
        top_k: int = RAG_TOP_K,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> QueryResponse:
        """
        Выполняет поиск в базе знаний, парсит ответ из HTTP /search и возвращает QueryResponse
        """
        results = await self._query_chroma(query, top_k, metadata_filter)
        
        chunks: List[LessonChunk] = []

        # Поддерживаем два возможных формата ответа:
        # 1) Формат вашего database/app.py: { "query": "...", "total_results": N, "results": [ {id, metadata, document, cosine_distance}, ... ] }
        # 2) (на случай) формат chroma server: ids/documents/metadatas/distances (вложенные списки).
        if results:
            if "results" in results and isinstance(results["results"], list):
                for r in results["results"]:
                    chunk = LessonChunk(
                        id=r.get("id", ""),
                        document=r.get("document", "") or "",
                        metadata=r.get("metadata", {}) or {},
                        distance=r.get("cosine_distance", None)
                    )
                    chunks.append(chunk)
            else:
                # fallback: старый chroma-формат (ids/documents/metadatas/distances)
                ids = results.get("ids", [[]])[0] if results.get("ids") else []
                documents = results.get("documents", [[]])[0] if results.get("documents") else []
                metadatas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
                distances = results.get("distances", [[]])[0] if results.get("distances") else []
                for i in range(len(ids)):
                    chunk = LessonChunk(
                        id=ids[i] if i < len(ids) else f"chunk_{i}",
                        document=documents[i] if i < len(documents) else "",
                        metadata=metadatas[i] if i < len(metadatas) else {},
                        distance=distances[i] if i < len(distances) else None
                    )
                    chunks.append(chunk)

        return QueryResponse(
            query=query,
            results=chunks,
            total_results=len(chunks)
        )

    def format_context(self, chunks: List[LessonChunk]) -> str:
        """
        Форматирует чанки в контекст для LLM
        """
        context_parts: List[str] = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"--- Урок {i} ---")
            context_parts.append(chunk.document)
            if chunk.metadata:
                meta_info: List[str] = []
                for key, value in chunk.metadata.items():
                    if value:
                        meta_info.append(f"{key}: {value}")
                if meta_info:
                    context_parts.append(f"Метаданные: {', '.join(meta_info)}")
            context_parts.append("")
        return "\n".join(context_parts)

    async def is_available(self) -> bool:
        """Проверка доступности ChromaDB — обращаемся к /ping (или /collection-info)"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.chroma_url}/ping")
                return response.status_code == 200
        except Exception:
            return False