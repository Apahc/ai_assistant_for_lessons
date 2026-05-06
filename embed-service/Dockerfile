FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ARG EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
ENV EMBEDDING_MODEL=${EMBEDDING_MODEL}

RUN python -c "import os; from fastembed import TextEmbedding; m=os.environ['EMBEDDING_MODEL']; print('Preloading', m); list(TextEmbedding(model_name=m).embed(['warmup'])); print('OK')"

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
