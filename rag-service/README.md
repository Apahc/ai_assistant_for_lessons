# RAG Service

Retrieval-сервис.

Роль:

- адаптирует `data/lessons.json` к поисковому формату
- загружает `lessons` и отдельный `meta`-корпус
- индексирует `lessons` и `meta` в отдельные Chroma collection
- получает эмбеддинги из `embed-service`
- получает реранкинг из `reranker-service`
- отдает backend текстовые retrieval results, `context` и отдельный `meta_context`

## Endpoints

- `POST /retrieve` - retrieval для `chat/search/document/mail`
- `GET /health` - health и число проиндексированных документов
