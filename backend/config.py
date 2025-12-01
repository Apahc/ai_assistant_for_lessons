"""
Конфигурация приложения
"""
import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
HF_TOKEN = os.environ.get("hf_token")
LLAMA_MODEL = "meta-llama/Llama-3.3-70B-Instruct"
LLAMA_PROVIDER = "groq"

# ChromaDB Configuration
CHROMA_HOST = "database"
CHROMA_PORT = "8001"
CHROMA_COLLECTION_NAME = "lessons"

# RAG Configuration
RAG_TOP_K = 5
RAG_CHUNK_MAX_CHARS = 1600
RAG_CHUNK_OVERLAP = 200

# API Configuration
API_HOST = "0.0.0.0"
API_PORT = 8000

