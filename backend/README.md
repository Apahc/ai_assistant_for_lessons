# Backend

FastAPI orchestration-сервис.

Роль:

- принимает запросы от фронтенда
- создает и завершает сессии
- получает историю из `memory-service`
- получает retrieval-контекст из `rag-service`
- генерирует итоговый текст по режимам `chat`, `search`, `document`, `mail`
