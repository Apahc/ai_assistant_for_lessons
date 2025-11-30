"""
Pydantic схемы для валидации данных
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class LessonChunk(BaseModel):
    """Модель чанка урока из ChromaDB"""
    id: str
    document: str
    metadata: Dict[str, Any]
    distance: Optional[float] = None


class QueryRequest(BaseModel):
    """Запрос на поиск в базе знаний"""
    query: str = Field(..., description="Поисковый запрос")
    top_k: int = Field(default=5, ge=1, le=20, description="Количество результатов")
    metadata_filter: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Фильтр по метаданным"
    )


class QueryResponse(BaseModel):
    """Ответ на запрос поиска"""
    query: str
    results: List[LessonChunk]
    total_results: int


class ChatRequest(BaseModel):
    """Запрос на консультацию с использованием RAG"""
    question: str = Field(..., description="Вопрос пользователя")
    top_k: int = Field(default=5, ge=1, le=20, description="Количество контекстных чанков")
    use_query_refinement: bool = Field(
        default=True, 
        description="Использовать улучшение запроса"
    )
    metadata_filter: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Фильтр по метаданным"
    )


class ChatResponse(BaseModel):
    """Ответ на консультацию"""
    answer: str
    question: str
    context_chunks: List[LessonChunk]
    sources_count: int


class HealthResponse(BaseModel):
    """Статус здоровья сервиса"""
    status: str
    chroma_connected: bool
    llama_available: bool

