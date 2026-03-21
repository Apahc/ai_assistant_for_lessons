import os

HF_TOKEN = os.getenv("HF_TOKEN", "")
LLM_MODEL = os.getenv("LLM_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")

MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", "http://memory-service:8005")
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://rag-service:8002")
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))
