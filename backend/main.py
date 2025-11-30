"""
Главный файл FastAPI приложения
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import router
from .config import API_HOST, API_PORT

app = FastAPI(
    title="AI Assistant for Lessons - RAG API",
    description="RAG система для поиска и консультации по извлечённым урокам",
    version="1.0.0"
)

# CORS middleware для работы с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(router)


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "message": "AI Assistant for Lessons - RAG API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)

