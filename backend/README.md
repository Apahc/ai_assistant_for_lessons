# Backend

FastAPI orchestration-сервис.

Роль:

- принимает запросы от фронтенда
- создает и завершает сессии
- получает историю из `memory-service`
- получает retrieval-контекст из `rag-service`
- собирает промпт по режимам `chat`, `search`, `document`, `mail`
- вызывает LLM (OpenAI-compatible endpoint или HuggingFace fallback)
- возвращает фронтенду итоговый текст

## API

- `POST /message` - основной endpoint для виджета (`session_id`, `mode`, `message`)
- `POST /api/v1/respond` - совместимый endpoint со структурированным ответом
- `POST /api/v1/sessions` - создать сессию через memory-service
- `POST /api/v1/sessions/{session_id}/close` - завершить сессию
- `GET /health`, `GET /api/v1/health` - health checks

## Prompts

4 базовых промпта для режимов `chat`, `search`, `document`, `mail`
встроены прямо в `backend/main.py` в словаре `PROMPT_TEMPLATES`.
