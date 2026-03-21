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
  "chat_type": "question",
  "top_k": 5,
  "use_query_refinement": true,
  "metadata_filter": null
}
```

**Типы контента (chat_type):**
- `question` (по умолчанию) - получить ответ на вопрос
- `letter` - сгенерировать официальное письмо
- `document` - создать документ

## Фронтенд

Интерактивный интерфейс находится в папке `frontend/`.

### Страницы

1. **demo.html** - Главная страница с имитацией базы данных извлеченных уроков
2. **index.html** - Чистый интерфейс чата (для встраивания)

### Запуск фронтенда

1. Убедитесь, что бэкенд запущен на `http://localhost:8000`
2. Откройте демо-страницу в браузере или используйте локальный сервер:

```bash
# С помощью Python
cd frontend
python -m http.server 8080

# Откройте http://localhost:8080/demo.html
```

### Возможности фронтенда

- 🏢 Полноценная имитация базы данных с карточками уроков
- 💬 Интерактивный чат-виджет (кнопка в правом нижнем углу)
- 🔍 Поиск извлечённых уроков через ИИ
- 📝 Три типа генерации контента (вопрос/письмо/документ)
- 📚 История просмотренных уроков
- 🎨 Современный адаптивный дизайн

Подробнее см. `frontend/README.md`

## Полный запуск системы

### Вариант 1: Docker Compose (рекомендуется) ⭐

```bash
# Запустите все три сервиса одной командой
docker compose up --build

# Откройте в браузере: http://localhost:8080
```

Все сервисы будут доступны:
- 🌐 **Frontend:** http://localhost:8080
- 🔌 **Backend API:** http://localhost:8000
- 💾 **ChromaDB:** http://localhost:8001

### Вариант 2: Локальный запуск

**1. Запустите ChromaDB:**
```bash
cd database
pip install -r requirements.txt
python app.py
```

**2. Запустите Backend:**
```bash
cd backend
pip install -r requirements.txt
python main.py
```

**3. Откройте Frontend:**
```bash
cd frontend
python -m http.server 8080
# Откройте http://localhost:8080/demo.html
```

## Структура проекта

```
.
├── backend/           # FastAPI сервер
│   ├── api/          # API роуты
│   ├── models/       # Pydantic модели
│   ├── services/     # Бизнес-логика
│   └── main.py       # Точка входа
├── database/         # ChromaDB сервис
│   ├── ingest.py     # Загрузка данных
│   └── app.py        # Запуск ChromaDB
├── frontend/         # Веб-интерфейс
│   ├── css/         # Стили
│   ├── js/          # JavaScript
│   └── index.html   # Главная страница
└── docker-compose.yml
```