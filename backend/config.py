"""
Конфигурация приложения
"""
import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
HF_TOKEN = os.environ.get("hf_token")
LLAMA_MODEL = os.environ.get("LLAMA_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
LLAMA_PROVIDER = os.environ.get("LLAMA_PROVIDER", "groq")

# ChromaDB Configuration
CHROMA_HOST = os.environ.get("CHROMA_HOST", "localhost")
CHROMA_PORT = os.environ.get("CHROMA_PORT", "8001")
CHROMA_COLLECTION_NAME = os.environ.get("CHROMA_COLLECTION_NAME", "lessons")

# RAG Configuration
RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "5"))
RAG_CHUNK_MAX_CHARS = int(os.environ.get("RAG_CHUNK_MAX_CHARS", "1600"))
RAG_CHUNK_OVERLAP = int(os.environ.get("RAG_CHUNK_OVERLAP", "200"))

# API Configuration
API_HOST = os.environ.get("API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("API_PORT", "8000"))

