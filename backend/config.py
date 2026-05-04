import os

HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("hf_token", "")
LLM_MODEL = os.getenv("LLM_MODEL") or os.getenv("LLAMA_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
LLM_PROVIDER = os.getenv("LLM_PROVIDER") or os.getenv("LLAMA_PROVIDER", "groq")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").strip()
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))

MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", "http://memory-service:8005")
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://rag-service:8002")
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))

LESSONS_PATH = os.getenv("LESSONS_PATH", "/data/lessons.json").strip()
GLOSSARY_PATH = os.getenv("GLOSSARY_PATH", "/data/glossary.json").strip()
