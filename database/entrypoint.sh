#!/bin/bash
if [ ! -f /data/chroma/chroma.sqlite3 ] || [ ! -s /data/chroma/chroma.sqlite3 ]; then
    echo "Инициализация базы данных..."
    python /app/ingest.py
fi

exec uvicorn app:app --host 0.0.0.0 --port 8001
