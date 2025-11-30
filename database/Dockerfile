FROM python:3.13-slim

WORKDIR /app

COPY requirements_db.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV CHROMA_PERSIST_DIR=/data/chroma

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]