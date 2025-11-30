"""
Скрипт для запуска сервера

Использование:
    Из корня проекта: python -m backend.run
    Или: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Автоперезагрузка при изменении кода
    )

