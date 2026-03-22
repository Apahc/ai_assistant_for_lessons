FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2; print('Preloading ONNX embedding model during image build...'); ONNXMiniLM_L6_V2()(['warmup']); print('Embedding model cached in image layer.')"

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
