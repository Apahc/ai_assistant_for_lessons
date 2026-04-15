import asyncio
import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any, Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from huggingface_hub import InferenceClient
from pydantic import BaseModel, Field
from prompts import PROMPT_TEMPLATES, SYSTEM_PROMPT

from config import (
    HF_TOKEN,
    LESSONS_PATH,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_TIMEOUT_SECONDS,
    MEMORY_SERVICE_URL,
    RAG_SERVICE_URL,
    RETRIEVAL_TOP_K,
)

# ---------------------------------------------------------------------------
#  Многослойный фильтр иностранных символов
# ---------------------------------------------------------------------------

# Слой 2: Промпт для LLM fix-up прохода
FIXUP_PROMPT = """Ниже приведён текст, в котором МОГУТ встречаться слова на иностранных языках
(китайский, испанский, английский и др.), смешанные с русским текстом.

ЗАДАЧА: замени каждое иностранное слово или фрагмент его ТОЧНЫМ русским эквивалентом,
сохраняя падеж, число и смысл предложения. НЕ УДАЛЯЙ информацию. НЕ ДОБАВЛЯЙ ничего нового.
Верни ТОЛЬКО исправленный текст, без пояснений и комментариев.

Текст для исправления:
{text}"""


# ---------- Слой 1: Детектор иностранного контента ----------

# Диапазоны Unicode для нежелательных скриптов
_FOREIGN_RANGES = (
    ("\u2E80", "\u9FFF"),   # CJK (китайский, японский, корейский)
    ("\uAC00", "\uD7AF"),   # Хангыль (корейский)
    ("\uF900", "\uFAFF"),   # CJK совместимые иероглифы
    ("\u0600", "\u06FF"),   # Арабский
    ("\u0900", "\u097F"),   # Деванагари
    ("\u0E00", "\u0E7F"),   # Тайский
)

# Паттерн: слово, содержащее хотя бы одну латинскую букву, склеенное
# с кириллическими суффиксами/окончаниями (например "uniformных", "desarrollать")
_HYBRID_WORD_RE = re.compile(
    r'\b[a-zA-Z]{3,}[а-яёА-ЯЁ]+\b'   # латинский корень + кириллическое окончание
    r'|'
    r'\b[а-яёА-ЯЁ]+[a-zA-Z]{3,}\b',  # кириллическое начало + латинский хвост
    re.UNICODE,
)

# Чистые латинские слова длиной ≥ 4 (не аббревиатуры, не ID)
_PURE_LATIN_WORD_RE = re.compile(
    r'(?<![A-Za-z0-9_/\\])\b[a-zA-Z]{4,}\b(?![A-Za-z0-9_/\\])',
    re.UNICODE,
)

# Допустимые латинские слова (аббревиатуры, термины, ID)
_ALLOWED_LATIN = {
    "id", "ll", "uc", "http", "https", "url", "api", "json", "xml",
    "pdf", "doc", "docx", "xlsx", "csv", "html", "email", "smtp",
    "iaea", "wano", "rosatom", "iso", "gost", "snip", "meta",
    "chat", "search", "document", "mail", "ok", "null", "none",
    "true", "false", "etc", "vs",
}


def has_foreign_content(text: str) -> bool:
    """Слой 1: обнаруживает иностранные символы и гибридные слова."""
    # Проверка CJK / арабских / прочих нежелательных скриптов
    for char in text:
        for lo, hi in _FOREIGN_RANGES:
            if lo <= char <= hi:
                return True

    # Проверка гибридных слов (латиница+кириллица)
    if _HYBRID_WORD_RE.search(text):
        return True

    # Проверка чистых латинских слов (не аббревиатур)
    for match in _PURE_LATIN_WORD_RE.finditer(text):
        word = match.group().lower()
        if word not in _ALLOWED_LATIN and not word.startswith("ll"):
            return True

    return False

# ---------- Слой 3: Regex safety net ----------

def strip_remaining_foreign(text: str) -> str:
    """Слой 3: финальная зачистка — убирает оставшиеся нежелательные символы."""
    if not text:
        return text

    # Убрать CJK и прочие нежелательные скрипты
    cleaned = re.sub(
        r'[\u2E80-\u9FFF'       # CJK Unified
        r'\uAC00-\uD7AF'        # Хангыль
        r'\uF900-\uFAFF'        # CJK Compatibility
        r'\u0600-\u06FF'        # Арабский
        r'\u0900-\u097F'        # Деванагари
        r'\u0E00-\u0E7F'        # Тайский
        r'\U00020000-\U0002A6DF'  # CJK Extension B
        r'\U0002A700-\U0002B73F'  # CJK Extension C
        r']+',
        '',
        text,
    )

    # Убрать гибридные слова (латинский корень + кириллическое окончание)
    cleaned = _HYBRID_WORD_RE.sub('', cleaned)

    # Убрать markdown ** и *
    while "**" in cleaned:
        new = re.sub(r"\*\*([^*]+?)\*\*", r"\1", cleaned, count=1)
        if new == cleaned:
            break
        cleaned = new
    cleaned = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", cleaned)
    cleaned = cleaned.replace("*", "")

    # Убрать двойные пробелы и лишние пустые строки
    cleaned = re.sub(r'  +', ' ', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    return cleaned.strip()


# ---------------------------------------------------------------------------
#  Конец блока фильтра
# ---------------------------------------------------------------------------

Mode = Literal["chat", "search", "document", "mail"]


class SessionResponse(BaseModel):
    session_id: str
    status: str


class MessageRequest(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1)
    mode: Mode = "chat"
    top_k: int = Field(default=RETRIEVAL_TOP_K, ge=1, le=20)


class LessonSnippet(BaseModel):
    id: str
    title: str
    text: str
    lesson_id: str | None = None


class MessageResponse(BaseModel):
    text: str
    lessons: list[LessonSnippet] = Field(default_factory=list)


class RespondResponse(BaseModel):
    session_id: str
    mode: Mode
    answer: str
    results_count: int
    lessons: list[LessonSnippet] = Field(default_factory=list)


class BackendService:
    def __init__(self) -> None:
        self.logger = logging.getLogger("backend")
        self.hf_client = None
        self.last_llm_error: str | None = None
        self._lessons_by_id: dict[str, dict[str, Any]] | None = None
        self._lessons_index_file: str | None = None
        if HF_TOKEN:
            try:
                self.hf_client = InferenceClient(provider=LLM_PROVIDER, token=HF_TOKEN)
            except Exception:
                self.hf_client = None

    async def call_memory(self, method: str, path: str, payload: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, f"{MEMORY_SERVICE_URL}{path}", json=payload)
            response.raise_for_status()
            return response.json()

    async def call_rag(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{RAG_SERVICE_URL}/retrieve", json=payload)
            response.raise_for_status()
            return response.json()

    async def call_rag_safe(self, payload: dict) -> dict:
        try:
            return await self.call_rag(payload)
        except httpx.HTTPError:
            return {
                "context": "",
                "meta_context": "",
                "results": [],
                "lesson_results": [],
                "meta_results": [],
                "lessons_texts": [],
                "lessons_count": 0,
                "meta_count": 0,
            }

    def history_to_text(self, messages: list[dict]) -> str:
        if not messages:
            return "История пока пустая."
        return "\n".join(f"{item['role']}: {item['content']}" for item in messages[-10:])

    def build_prompt(self, mode: Mode, *, message: str, history: str, context: str, meta_context: str) -> str:
        template = PROMPT_TEMPLATES.get(mode, PROMPT_TEMPLATES["chat"])
        return template.format(
            message=message,
            history=history,
            context=context,
            meta_context=meta_context or "Мета-контекст не найден.",
        )

    def normalize_generated_text(self, generated: object) -> str | None:
        if isinstance(generated, str):
            cleaned = generated.strip()
            return cleaned or None
        if isinstance(generated, list):
            parts: list[str] = []
            for item in generated:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
            if parts:
                return "\n".join(parts)
        return None

    def format_lesson_brief(self, item: dict) -> str:
        title = item.get("title", "").strip() or item.get("metadata", {}).get("lesson_id", "Урок")
        text = " ".join((item.get("text", "") or "").split())
        if len(text) > 320:
            text = f"{text[:317]}..."
        return f"{title}: {text}" if text else title

    def fallback_response(
        self,
        mode: Mode,
        *,
        message: str,
        context: str,
        meta_context: str,
        lesson_results: list[dict],
    ) -> str:
        lesson_briefs = [self.format_lesson_brief(item) for item in lesson_results[:5]]

        if mode == "search":
            if not lesson_briefs:
                return "По запросу релевантные уроки не найдены. Уточните тему, этап проекта или вид работ."
            intro = f"По запросу \"{message}\" найдены релевантные уроки по теме. Ниже приведены наиболее полезные материалы для дальнейшего просмотра."
            lessons_block = "\n".join(f"{index}. {brief}" for index, brief in enumerate(lesson_briefs, start=1))
            return f"{intro}\n\nРелевантные уроки:\n{lessons_block}"

        if mode == "document":
            evidence = "\n".join(f"- {brief}" for brief in lesson_briefs[:3]) or "- Недостаточно релевантных данных в текущем корпусе уроков."
            return (
                "Заголовок\n"
                f"Черновик документа по теме: {message}\n\n"
                "Основание\n"
                "Подготовлено на основе материалов раздела \"Извлеченные уроки\".\n\n"
                "Текущая ситуация\n"
                f"{context or 'В доступном контексте недостаточно данных для развернутого описания текущей ситуации.'}\n\n"
                "Предлагаемые меры\n"
                f"{evidence}\n\n"
                "Ожидаемый эффект\n"
                "Уточнение и систематизация практик по рассматриваемой теме.\n\n"
                "Вывод\n"
                "Черновик требует проверки специалистом перед включением в официальный документ."
            )

        if mode == "mail":
            evidence = "\n".join(f"- {brief}" for brief in lesson_briefs[:3]) or "- В текущем контексте релевантные уроки не найдены."
            return (
                "Здравствуйте!\n\n"
                f"По теме \"{message}\" подготовлена краткая подборка материалов из раздела \"Извлеченные уроки\".\n\n"
                "Ключевые выводы:\n"
                f"{evidence}\n\n"
                "Предлагаю использовать эти материалы как основу для дальнейшей проработки вопроса. "
                "При необходимости можно дополнительно уточнить запрос по этапу проекта, виду работ или типу проблемы.\n\n"
                "С уважением,\n"
                "Ассистент раздела \"Извлеченные уроки\""
            )

        if lesson_briefs:
            recommendations = "\n".join(f"- {brief}" for brief in lesson_briefs[:3])
            return (
                f"По материалам раздела \"Извлеченные уроки\" по теме \"{message}\" можно выделить следующие практические ориентиры:\n"
                f"{recommendations}\n\n"
                "Если нужно, я могу переработать это в формат поиска, документа или делового письма."
            )
        if meta_context:
            return meta_context
        return context or "По запросу не найден релевантный контекст."

    def llm_url(self) -> str:
        base = LLM_BASE_URL.rstrip("/")
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        return f"{base}/v1/chat/completions"

    async def generate_openai_compatible(self, prompt: str) -> str | None:
        headers = {"Content-Type": "application/json"}
        if LLM_API_KEY:
            headers["Authorization"] = f"Bearer {LLM_API_KEY}"
        payload = {
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SECONDS) as client:
            response = await client.post(self.llm_url(), headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                return None
            return choices[0].get("message", {}).get("content")

    async def generate_hf(self, prompt: str) -> str | None:
        if not self.hf_client:
            return None
        try:
            completion = await asyncio.to_thread(
                self.hf_client.chat.completions.create,
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                stream=False,
            )
            choices = getattr(completion, "choices", None) or []
            if not choices:
                return None
            content = getattr(choices[0].message, "content", None)
            return self.normalize_generated_text(content)
        except Exception as exc:
            self.last_llm_error = str(exc)
            self.logger.exception("Hugging Face generation failed")
            return None

    async def _llm_fixup(self, dirty_text: str) -> str | None:
        """Слой 2: отправляет текст на повторный LLM-проход для замены иностранных слов."""
        fixup = FIXUP_PROMPT.format(text=dirty_text)
        try:
            if LLM_BASE_URL:
                result = await self.generate_openai_compatible(fixup)
                if result:
                    return result
            result = await self.generate_hf(fixup)
            return result
        except Exception as exc:
            self.logger.warning("LLM fixup pass failed: %s", exc)
            return None

    async def generate_text(
        self,
        mode: Mode,
        message: str,
        history: str,
        context: str,
        meta_context: str,
        lesson_results: list[dict],
    ) -> str:
        prompt = self.build_prompt(
            mode,
            message=message,
            history=history,
            context=context,
            meta_context=meta_context,
        )

        generated = None
        if LLM_BASE_URL:
            try:
                generated = await self.generate_openai_compatible(prompt)
            except httpx.HTTPError as exc:
                self.last_llm_error = str(exc)
                self.logger.exception("OpenAI-compatible generation failed")
                generated = None
        if not generated:
            generated = await self.generate_hf(prompt)

        normalized = self.normalize_generated_text(generated)
        if not normalized:
            self.logger.warning("Falling back to local mode formatter for mode=%s", mode)
            return self.fallback_response(
                mode,
                message=message,
                context=context,
                meta_context=meta_context,
                lesson_results=lesson_results,
            )

        self.last_llm_error = None

        # ===== Многослойный фильтр =====

        # Слой 1: Детекция — есть ли иностранный контент?
        if not has_foreign_content(normalized):
            # Чисто — только markdown-очистка
            return strip_remaining_foreign(normalized)

        self.logger.info("Foreign content detected, applying multi-layer filter")

        # Если после словаря всё чисто — готово
        if not has_foreign_content(normalized):
            self.logger.info("Layer 2 (dictionary) resolved all foreign content")
            return strip_remaining_foreign(normalized)

        # Слой 2: LLM fix-up проход
        fixup_result = await self._llm_fixup(normalized)
        if fixup_result:
            fixup_normalized = self.normalize_generated_text(fixup_result)
            if fixup_normalized and not has_foreign_content(fixup_normalized):
                self.logger.info("Layer 3 (LLM fixup) resolved all foreign content")
                return strip_remaining_foreign(fixup_normalized)
            # Даже если fix-up не полностью очистил — берём его результат как базу
            if fixup_normalized:
                normalized = fixup_normalized

        # Слой 3: Regex safety net — жёсткая зачистка оставшегося
        self.logger.info("Layer 4 (regex safety net) applied")
        return strip_remaining_foreign(normalized)

    def _ensure_lessons_index(self) -> dict[str, dict[str, Any]]:
        if not LESSONS_PATH:
            return {}
        path = Path(LESSONS_PATH)
        try:
            resolved = str(path.resolve())
        except OSError:
            resolved = LESSONS_PATH
        if self._lessons_by_id is not None and self._lessons_index_file == resolved:
            return self._lessons_by_id
        if not path.is_file():
            self.logger.warning("LESSONS_PATH is not a readable file: %s", LESSONS_PATH)
            self._lessons_by_id = {}
            self._lessons_index_file = resolved
            return self._lessons_by_id
        raw = json.loads(path.read_text(encoding="utf-8"))
        idx: dict[str, dict[str, Any]] = {}
        if isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict):
                    continue
                lid = str(item.get("ID_урока") or item.get("lesson_id") or item.get("id") or "").strip()
                if lid:
                    idx[lid] = dict(item)
        self._lessons_by_id = idx
        self._lessons_index_file = resolved
        return self._lessons_by_id

    def get_full_lesson(self, lesson_id: str) -> dict[str, Any] | None:
        lid = lesson_id.strip()
        if not lid:
            return None
        return self._ensure_lessons_index().get(lid)

    def lesson_snippets_from_results(self, lesson_results: list[dict]) -> list[LessonSnippet]:
        seen: set[str] = set()
        out: list[LessonSnippet] = []
        for item in lesson_results:
            if item.get("source_type") != "lesson":
                continue
            chunk_id = str(item.get("id", ""))
            if not chunk_id or chunk_id in seen:
                continue
            seen.add(chunk_id)
            meta = item.get("metadata") or {}
            title = (item.get("title") or "").strip() or str(meta.get("lesson_id") or "Урок")
            out.append(
                LessonSnippet(
                    id=chunk_id,
                    title=title,
                    text=item.get("text") or "",
                    lesson_id=meta.get("lesson_id"),
                )
            )
        return out

    async def handle_message(self, request: MessageRequest) -> tuple[str, int, list[LessonSnippet]]:
        session = await self.call_memory("GET", f"/sessions/{request.session_id}")
        history_messages = session.get("messages", [])

        await self.call_memory(
            "POST",
            f"/sessions/{request.session_id}/messages",
            {"role": "user", "content": request.message, "mode": request.mode},
        )

        retrieval = await self.call_rag_safe(
            {
                "query": request.message,
                "mode": request.mode,
                "top_k": request.top_k,
                "session_messages": history_messages,
            }
        )
        context = retrieval.get("context", "")
        meta_context = retrieval.get("meta_context", "")
        results = retrieval.get("results", [])
        lesson_results = retrieval.get("lesson_results", [])

        answer = await self.generate_text(
            request.mode,
            request.message,
            self.history_to_text(history_messages),
            context,
            meta_context,
            lesson_results,
        )

        await self.call_memory(
            "POST",
            f"/sessions/{request.session_id}/messages",
            {"role": "assistant", "content": answer, "mode": request.mode},
        )
        snippets = self.lesson_snippets_from_results(lesson_results)
        return answer, len(results), snippets


service = BackendService()
app = FastAPI(title="Lessons Backend", version="2.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict:
    return {"service": "backend", "domain": "lessons-learned"}


@app.post("/api/v1/sessions", response_model=SessionResponse)
async def create_session() -> SessionResponse:
    data = await service.call_memory("POST", "/sessions")
    return SessionResponse(**data)


@app.post("/api/v1/sessions/{session_id}/close", response_model=SessionResponse)
async def close_session(session_id: str) -> SessionResponse:
    data = await service.call_memory("POST", f"/sessions/{session_id}/complete")
    return SessionResponse(**data)


@app.get("/api/v1/lessons/{lesson_id}")
async def get_lesson_full(lesson_id: str) -> dict[str, Any]:
    row = service.get_full_lesson(lesson_id)
    if not row:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return row


@app.get("/api/v1/sessions/{session_id}")
async def get_session_state(session_id: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{MEMORY_SERVICE_URL.rstrip('/')}/sessions/{session_id}")
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Session not found")
            response.raise_for_status()
            return response.json()
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Downstream service error: {exc}") from exc


@app.post("/message", response_model=MessageResponse)
async def message(request: MessageRequest) -> MessageResponse:
    try:
        answer, _, lessons = await service.handle_message(request)
        return MessageResponse(text=answer, lessons=lessons)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Downstream service error: {exc}") from exc


@app.post("/api/v1/respond", response_model=RespondResponse)
async def respond(request: MessageRequest) -> RespondResponse:
    try:
        answer, results_count, lessons = await service.handle_message(request)
        return RespondResponse(
            session_id=request.session_id,
            mode=request.mode,
            answer=answer,
            results_count=results_count,
            lessons=lessons,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Downstream service error: {exc}") from exc


@app.get("/health")
async def health() -> dict:
    return await health_v1()


@app.get("/api/v1/health")
async def health_v1() -> dict:
    memory: dict = {"status": "unavailable"}
    rag: dict = {"status": "unavailable"}

    try:
        memory = await service.call_memory("GET", "/health")
    except httpx.HTTPError:
        pass

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            rag_response = await client.get(f"{RAG_SERVICE_URL}/health")
            rag_response.raise_for_status()
            rag = rag_response.json()
    except httpx.HTTPError:
        pass

    llm_mode = "openai_compatible" if LLM_BASE_URL else ("huggingface" if service.hf_client else "fallback")
    status = "ok" if memory.get("status") == "ok" and rag.get("status") == "ok" else "degraded"
    return {
        "status": status,
        "memory": memory,
        "rag": rag,
        "llm_mode": llm_mode,
        "llm_last_error": service.last_llm_error,
    }


@app.get("/health/ready")
async def health_ready() -> dict:
    data = await health_v1()
    if data["status"] != "ok":
        raise HTTPException(status_code=503, detail=data)
    return data
