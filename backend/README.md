# Backend - AI Assistant for Lessons

## Структура проекта

```
backend/
├── __init__.py
├── main.py                 # Главный файл FastAPI приложения
├── config.py              # Конфигурация приложения
├── prompts.py             # Промпты для различных задач
├── requirements.txt       # Зависимости
├── models/                # Модели данных
│   ├── __init__.py
│   └── schemas.py         # Pydantic схемы
├── services/              # Бизнес-логика
│   ├── __init__.py
│   ├── llm_service.py     # Сервис для работы с Llama API
│   └── rag_service.py     # RAG сервис для работы с ChromaDB
└── api/                   # API endpoints
    ├── __init__.py
    └── routes.py          # Маршруты API
```

## Установка и запуск

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Создайте файл `.env` в корне проекта с переменными:
```env
hf_token=your_huggingface_token
CHROMA_HOST=localhost
CHROMA_PORT=8001
LLAMA_MODEL=meta-llama/Llama-3.3-70B-Instruct
LLAMA_PROVIDER=groq
```

3. Запустите сервер:
```bash
python -m backend.main
```

Или через uvicorn:
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### GET `/`
Корневой endpoint с информацией о сервисе

### GET `/api/v1/health`
Проверка здоровья сервиса и его компонентов

### POST `/api/v1/search`
Поиск уроков в базе знаний
```json
{
  "query": "проблема с производительностью",
  "top_k": 5,
  "metadata_filter": null
}
```

### POST `/api/v1/chat`
Консультация с использованием RAG
```json
{
  "question": "Как решить проблему с производительностью?",
  "top_k": 5,
  "use_query_refinement": true,
  "metadata_filter": null
}
```

## Компоненты

### LLMService
Сервис для работы с Llama API через Hugging Face InferenceClient. Поддерживает:
- Генерацию ответов на основе контекста
- Улучшение поисковых запросов
- Извлечение ключевых слов
- Суммаризацию уроков

### RAGService
Сервис для работы с векторной базой данных ChromaDB. Выполняет:
- Поиск релевантных чанков
- Форматирование контекста для LLM
- Проверку доступности базы данных

### Prompts
Все промпты вынесены в отдельный файл `prompts.py`:
- `RAG_ANSWER_PROMPT` - для генерации ответов
- `QUERY_REFINEMENT_PROMPT` - для улучшения запросов
- `KEYWORD_EXTRACTION_PROMPT` - для извлечения ключевых слов
- `LESSONS_SUMMARY_PROMPT` - для суммаризации уроков

