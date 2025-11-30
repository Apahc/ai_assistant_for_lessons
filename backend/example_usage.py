"""
Пример использования API для тестирования
"""
import asyncio
import httpx


async def test_api():
    """Примеры использования API"""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        # 1. Проверка здоровья сервиса
        print("=== Проверка здоровья сервиса ===")
        response = await client.get(f"{base_url}/api/v1/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}\n")
        
        # 2. Поиск в базе знаний
        print("=== Поиск в базе знаний ===")
        search_request = {
            "query": "проблема с производительностью",
            "top_k": 3
        }
        response = await client.post(
            f"{base_url}/api/v1/search",
            json=search_request
        )
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Найдено результатов: {result['total_results']}")
        for i, chunk in enumerate(result['results'][:2], 1):
            print(f"\nРезультат {i}:")
            print(f"ID: {chunk['id']}")
            print(f"Документ: {chunk['document'][:200]}...")
        print()
        
        # 3. Консультация с RAG
        print("=== Консультация с RAG ===")
        chat_request = {
            "question": "Как решить проблему с производительностью системы?",
            "top_k": 3,
            "use_query_refinement": True
        }
        response = await client.post(
            f"{base_url}/api/v1/chat",
            json=chat_request
        )
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Вопрос: {result['question']}")
        print(f"Ответ: {result['answer'][:500]}...")
        print(f"Использовано источников: {result['sources_count']}\n")


if __name__ == "__main__":
    print("Запуск примеров использования API...")
    print("Убедитесь, что сервер запущен на http://localhost:8000")
    print("И что ChromaDB доступен на http://localhost:8001\n")
    
    try:
        asyncio.run(test_api())
    except Exception as e:
        print(f"Ошибка: {e}")
        print("\nУбедитесь, что:")
        print("1. Сервер запущен: uvicorn backend.main:app --host 0.0.0.0 --port 8000")
        print("2. ChromaDB доступен на порту 8001")
        print("3. Переменная окружения hf_token установлена")

