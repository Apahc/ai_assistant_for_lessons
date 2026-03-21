# AI-Ассистент: прототип (февраль-май 2026)

## Цель этапа

Собрать минимально рабочую RAG-систему для раздела "Извлеченные уроки", в которой уже разложены основные сервисы, проходит полный путь одного запроса и подготовлена архитектура для дальнейшей доработки retrieval, памяти диалогов, промптов и подключения рабочей LLM.

## Направления

| Направление    | Ответственный | Участники           |
|----------------|---------------|---------------------|
| 1. Методология | Татьяна       | Яна, Алина          |
| 2. Прототип    | Дмитрий       | Степан, Андрей, Яна |
| 3. UI          | Алина         | —                   |

## Что это за проект

Это не общий AI-помощник по всему сайту. Система работает только в домене раздела "Извлеченные уроки" и отвечает по:

- содержимому `lessons.json`
- дополнительной метаинформации раздела, если она подключена
- истории текущего диалога в рамках одной открытой страницы

Пользователь открывает страницу раздела на портале, запускает виджет и работает с одним активным диалогом. При перезагрузке страницы создается новая `session_id`, а завершенный или прерванный диалог сохраняется как история.

## Режимы работы

- `chat` - генеративный диалог по урокам и метаинформации раздела
- `search` - retrieval по урокам с краткой генеративной подводкой и выдачей релевантных текстов уроков
- `document` - ответ в форме черновика служебного документа
- `mail` - ответ в форме делового письма

Режим выбирается на frontend одной активной кнопкой и передается в backend вместе с `session_id` и текстом запроса.

## Как устроена система

В проекте один репозиторий и один `docker-compose.yml`. Каждый сервис лежит в отдельной папке в корне.

- `portal/` - PHP-оболочка страницы раздела "Извлеченные уроки"
- `frontend/` - HTML/CSS/JS-виджет
- `backend/` - основной FastAPI orchestrator
- `rag-service/` - retrieval, сбор контекста и работа с Chroma
- `memory-service/` - работа с активной сессией, историей и логами
- `embed-service/` - сервис эмбеддингов
- `reranker-service/` - сервис реранкинга
- `data/` - данные, включая `lessons.json`, `raw_data/` и локальную персистентность Chroma

Вспомогательная инфраструктура поднимается в compose:

- `chroma` - векторная база
- `redis` - оперативная память активной сессии
- `postgres` - история диалогов и технические логи

## Как проходит один запрос

1. Пользователь открывает портал на странице раздела "Извлеченные уроки".
2. В портале встроен frontend-виджет.
3. Frontend создает новую `session_id` через backend.
4. Пользователь выбирает режим и отправляет сообщение.
5. Backend получает историю сессии из `memory-service`.
6. Backend отправляет запрос в `rag-service`.
7. `rag-service` строит retrieval-запрос, вызывает `embed-service`, ищет данные в Chroma, применяет `reranker-service` и возвращает текстовый контекст.
8. Backend собирает промпт по выбранному режиму и обращается к LLM.
9. Backend сохраняет сообщение пользователя и ответ ассистента через `memory-service`.
10. Frontend показывает пользователю только итоговый текстовый ответ.

## Хранение данных и памяти

- Активная текущая сессия хранится в `Redis`
- История диалогов и request logs сохраняются в `Postgres`
- Векторный индекс хранится в `Chroma`
- Основной корпус данных - `data/lessons.json`
- `data/raw_data/` не используется рантаймом и не должен изменяться приложением

`data/lessons.json` и `data/raw_data/` считаются неприкосновенными источниками данных. Приложение не должно их переписывать.

## Как сейчас устроена связь с LLM

Backend поддерживает два рабочих сценария генерации:

1. Через внешний OpenAI-compatible API
2. Через Hugging Face по токену

Логика такая:

- если заполнен `LLM_BASE_URL`, backend использует внешний endpoint формата `/v1/chat/completions`
- если `LLM_BASE_URL` пустой, backend пытается использовать Hugging Face через `HF_TOKEN`
- если генерация недоступна, backend использует retrieval-based fallback и система все равно остается минимально рабочей

Это означает, что проект уже готов и к облачной модели, и к локально развернутой модели на отдельном сервере, если она доступна по OpenAI-compatible API, например через Ollama или совместимый шлюз.

## Как переключать источник LLM

### Вариант 1. Hugging Face

Оставьте `LLM_BASE_URL` пустым и заполните:

```env
HF_TOKEN=your_token
LLM_MODEL=meta-llama/Llama-3.3-70B-Instruct
LLM_PROVIDER=groq
```

### Вариант 2. Внешняя или локальная LLM по API

Заполните `LLM_BASE_URL` и при необходимости `LLM_API_KEY`:

```env
LLM_BASE_URL=http://your-llm-host:11434
LLM_API_KEY=
LLM_MODEL=llama3.1
```

В этом режиме backend пойдет не в Hugging Face, а в указанный внешний endpoint.

## Запуск проекта

### Требования

- Docker
- Docker Compose

### Подготовка `.env`

В корне проекта должен быть файл `.env`. Основные переменные:

```env
BACKEND_PORT=8000
PORTAL_PORT=8080
FRONTEND_PORT=8081

MEMORY_SERVICE_PORT=8005
RAG_SERVICE_PORT=8002
EMBED_SERVICE_PORT=8003
RERANKER_SERVICE_PORT=8004
CHROMA_PORT=8006
REDIS_PORT=6379
POSTGRES_PORT=5432

BACKEND_PUBLIC_URL=http://localhost:8000
FRONTEND_PUBLIC_URL=http://localhost:8081

MEMORY_SERVICE_URL=http://memory-service:8005
RAG_SERVICE_URL=http://rag-service:8002
EMBED_SERVICE_URL=http://embed-service:8003
RERANKER_SERVICE_URL=http://reranker-service:8004

REDIS_URL=redis://redis:6379/0
POSTGRES_DSN=postgresql://lessons:lessons@postgres:5432/lessons

CHROMA_HOST=chroma
CHROMA_INTERNAL_PORT=8000
CHROMA_COLLECTION=lessons

LESSONS_PATH=/data/lessons.json
PORTAL_META_PATH=/data/portal_meta.txt

RETRIEVAL_TOP_K=5
RETRIEVAL_CANDIDATE_K=12
SESSION_TTL_SECONDS=14400
```

Для генерации также настройте один из вариантов:

- `HF_TOKEN` для Hugging Face
- или `LLM_BASE_URL` и при необходимости `LLM_API_KEY` для внешней LLM

### Запуск через Docker Compose

```bash
docker compose up --build
```

После старта сервисы доступны так:

- `http://localhost:8080` - портал
- `http://localhost:8081/demo.html` - frontend-виджет напрямую
- `http://localhost:8000/health` - backend
- `http://localhost:8002/health` - rag-service
- `http://localhost:8005/health` - memory-service
- `http://localhost:8006` - Chroma

## Как проверить минимальный сценарий

1. Откройте `http://localhost:8080`
2. Перейдите на страницу раздела "Извлеченные уроки"
3. Откройте виджет
4. Выберите режим `chat`
5. Отправьте сообщение
6. Убедитесь, что backend вернул текстовый ответ
7. Убедитесь, что сессия создалась и история сохраняется

Если LLM не подключена, ответ все равно может вернуться через retrieval fallback, но он будет проще, чем полноценная генерация моделью.

## API верхнего уровня

Для frontend основная точка входа сейчас одна:

### POST `/message`

Запрос:

```json
{
  "session_id": "string",
  "mode": "chat",
  "message": "Какие уроки есть по производительности бетонирования?"
}
```

Ответ:

```json
{
  "text": "..."
}
```

Также backend поддерживает:

- `POST /api/v1/sessions` - создать новую сессию
- `POST /api/v1/sessions/{session_id}/close` - завершить сессию
- `GET /health` и `GET /api/v1/health` - health-check

## Структура проекта

```text
.
├── portal/             # PHP-оболочка раздела
├── frontend/           # HTML/CSS/JS виджет
├── backend/            # FastAPI orchestrator
├── rag-service/        # Retrieval и подготовка контекста
├── memory-service/     # Redis/Postgres память и история
├── embed-service/      # Эмбеддинги
├── reranker-service/   # Реранкинг
├── data/               # lessons.json, raw_data, chroma_db
└── docker-compose.yml
```

## Текущее состояние

Система уже собрана как единый рабочий каркас и пригодна для дальнейшей разработки. Основная архитектура, режимы, память сессий, retrieval-контур и портал уже разложены по сервисам. Следующие доработки могут касаться качества промптов, улучшения retrieval, подключения целевой LLM и расширения метаинформации раздела.
