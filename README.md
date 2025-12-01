# AI-Ассистент: прототип (окт-дек 2025)

## Цель этапа

Прототип диалога «пользователь ↔ система».

## Направления

| Направление    | Ответственный | Участники           |
|----------------|---------------|---------------------|
| 1. Методология | Татьяна       | Яна, Алина          |
| 2. Прототип    | Дмитрий       | Степан, Андрей, Яна |
| 3. UI          | Алина         | —                   |

## Запуск в докере

1) Перейти в папку проекта
2) Запустить создание контейнеров
```bash
docker compose build --no-cache
```
3) Поднять контейнеры
```bash
docker compose up
```
4) Создать файл `.env` в корне проекта с переменными:
```env
hf_token=your_huggingface_token
CHROMA_HOST=localhost
CHROMA_PORT=8001
LLAMA_MODEL=meta-llama/Llama-3.3-70B-Instruct
LLAMA_PROVIDER=groq
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