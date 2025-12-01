"""
RAG сервис для работы с ChromaDB
"""
import httpx
from typing import List, Optional, Dict, Any
from config import CHROMA_HOST, CHROMA_PORT, CHROMA_COLLECTION_NAME, RAG_TOP_K
from models.schemas import LessonChunk, QueryRequest, QueryResponse


class RAGService:
    """Сервис для работы с векторной базой данных ChromaDB"""
    
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
        Выполняет запрос к ChromaDB через API
        
        Args:
            query: Поисковый запрос
            top_k: Количество результатов
            metadata_filter: Фильтр по метаданным
            
        Returns:
            Результаты поиска от ChromaDB
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "q": query,
                    "top_k": top_k
                }
                if metadata_filter:
                    payload["metadata_filter"] = metadata_filter
                
                response = await client.post(
                    f"{self.chroma_url}/query",
                    json=payload
                )
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
        Выполняет поиск в базе знаний
        
        Args:
            query: Поисковый запрос
            top_k: Количество результатов
            metadata_filter: Фильтр по метаданным
            
        Returns:
            Результаты поиска
        """
        results = await self._query_chroma(query, top_k, metadata_filter)
        
        chunks = []
        if results:
            # Обработка результатов от ChromaDB
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
        
        Args:
            chunks: Список чанков
            
        Returns:
            Отформатированный контекст
        """
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"--- Урок {i} ---")
            context_parts.append(chunk.document)
            if chunk.metadata:
                meta_info = []
                for key, value in chunk.metadata.items():
                    if value:
                        meta_info.append(f"{key}: {value}")
                if meta_info:
                    context_parts.append(f"Метаданные: {', '.join(meta_info)}")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    async def is_available(self) -> bool:
        """Проверка доступности ChromaDB"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.chroma_url}/health")
                return response.status_code == 200
        except Exception:
            return False

