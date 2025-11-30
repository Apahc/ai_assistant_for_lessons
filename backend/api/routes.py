"""
API маршруты для RAG системы
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from ..models.schemas import (
    QueryRequest,
    QueryResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse
)
from ..services.rag_service import RAGService
from ..services.llm_service import LLMService

router = APIRouter(prefix="/api/v1", tags=["RAG API"])


def get_rag_service() -> RAGService:
    """Dependency для RAG сервиса"""
    return RAGService()


def get_llm_service() -> LLMService:
    """Dependency для LLM сервиса"""
    return LLMService()


@router.post("/search", response_model=QueryResponse)
async def search_lessons(
    request: QueryRequest,
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    Поиск уроков в базе знаний
    
    Args:
        request: Параметры поиска
        
    Returns:
        Результаты поиска
    """
    try:
        results = await rag_service.search(
            query=request.query,
            top_k=request.top_k,
            metadata_filter=request.metadata_filter
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка поиска: {str(e)}")


@router.post("/chat", response_model=ChatResponse)
async def chat_with_rag(
    request: ChatRequest,
    rag_service: RAGService = Depends(get_rag_service),
    llm_service: LLMService = Depends(get_llm_service)
):
    """
    Консультация с использованием RAG
    
    Args:
        request: Запрос на консультацию
        
    Returns:
        Ответ с консультацией
    """
    try:
        # Улучшение запроса, если требуется
        search_query = request.question
        if request.use_query_refinement and llm_service.is_available():
            refined = llm_service.refine_query(request.question)
            if refined:
                search_query = refined
        
        # Поиск релевантных чанков
        search_results = await rag_service.search(
            query=search_query,
            top_k=request.top_k,
            metadata_filter=request.metadata_filter
        )
        
        if not search_results.results:
            return ChatResponse(
                answer="К сожалению, в базе знаний не найдено релевантной информации для вашего вопроса.",
                question=request.question,
                context_chunks=[],
                sources_count=0
            )
        
        # Форматирование контекста
        context = rag_service.format_context(search_results.results)
        
        # Генерация ответа с помощью LLM
        answer = "Не удалось сгенерировать ответ."
        if llm_service.is_available():
            generated_answer = llm_service.generate_rag_answer(
                question=request.question,
                context=context
            )
            if generated_answer:
                answer = generated_answer
        else:
            # Fallback: просто возвращаем контекст, если LLM недоступен
            answer = f"Найдено {len(search_results.results)} релевантных уроков:\n\n{context}"
        
        return ChatResponse(
            answer=answer,
            question=request.question,
            context_chunks=search_results.results,
            sources_count=len(search_results.results)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при генерации ответа: {str(e)}")


@router.get("/health", response_model=HealthResponse)
async def health_check(
    rag_service: RAGService = Depends(get_rag_service),
    llm_service: LLMService = Depends(get_llm_service)
):
    """
    Проверка здоровья сервиса
    
    Returns:
        Статус сервиса и его компонентов
    """
    chroma_connected = await rag_service.is_available()
    llama_available = llm_service.is_available()
    
    status = "healthy" if (chroma_connected and llama_available) else "degraded"
    
    return HealthResponse(
        status=status,
        chroma_connected=chroma_connected,
        llama_available=llama_available
    )

