# Lessons Learned RAG System

Легкая сервисная RAG-система для раздела "Извлеченные уроки".

## Сервисы

- `portal/` - PHP-оболочка страницы раздела
- `frontend/` - HTML/CSS/JS виджет ассистента
- `backend/` - FastAPI orchestration API
- `rag-service/` - retrieval, подготовка контекста, индексация в Chroma
- `embed-service/` - сервис эмбеддингов
- `reranker-service/` - сервис реранкинга
- `memory-service/` - работа с Redis и Postgres для сессий, истории и логов

## Инфраструктура

- `redis` - оперативная память активных сессий
- `postgres` - история диалогов и логирование
- `chroma` - векторная база
- `data/` - неприкосновенные данные и локальная персистентность

## Быстрый старт

1. Скопируйте `.env.example` в `.env`
2. Запустите `docker compose up --build`
3. Откройте `http://localhost:8080`

## Данные

- `data/lessons.json` не переписывается приложением
- `data/raw_data/` не трогается приложением
- `data/chroma_db/` используется только для хранения индекса Chroma
