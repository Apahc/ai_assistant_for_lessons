import os

CHROMA_HOST = os.getenv("CHROMA_HOST", "chroma")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "lessons")

EMBED_SERVICE_URL = os.getenv("EMBED_SERVICE_URL", "http://embed-service:8003")
RERANKER_SERVICE_URL = os.getenv("RERANKER_SERVICE_URL", "http://reranker-service:8004")

LESSONS_PATH = os.getenv("LESSONS_PATH", "/data/lessons.json")
PORTAL_META_PATH = os.getenv("PORTAL_META_PATH", "/data/portal_meta.txt")

REPORTS_PATH = os.getenv("REPORTS_PATH", "/data/reports.json")
INFORMATION_SHEETS_PATH = os.getenv("INFORMATION_SHEETS_PATH", "/data/information_sheets.json")
LETTERS_PATH = os.getenv("LETTERS_PATH", "/data/letters.json")
GLOSSARY_PATH = os.getenv("GLOSSARY_PATH", "/data/glossary.json")

RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))
# Шире пул кандидатов перед реранжированием — мелкие чанки (глоссарий) чаще попадают в топ.
RETRIEVAL_CANDIDATE_K = int(os.getenv("RETRIEVAL_CANDIDATE_K", "20"))
MAX_CHARS = 1400
OVERLAP = 200
