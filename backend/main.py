import asyncio
import logging
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from huggingface_hub import InferenceClient
from pydantic import BaseModel, Field

from config import (
    HF_TOKEN,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_TIMEOUT_SECONDS,
    MEMORY_SERVICE_URL,
    RAG_SERVICE_URL,
    RETRIEVAL_TOP_K,
)
from prompts import PROMPT_TEMPLATES


Mode = Literal["chat", "search", "document", "mail"]


class SessionResponse(BaseModel):
    session_id: str
    status: str


class MessageRequest(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1)
    mode: Mode = "chat"
    top_k: int = Field(default=RETRIEVAL_TOP_K, ge=1, le=20)


class MessageResponse(BaseModel):
    text: str


class RespondResponse(BaseModel):
    session_id: str
    mode: Mode
    answer: str
    results_count: int


class BackendService:
    def __init__(self) -> None:
        self.logger = logging.getLogger("backend")
        self.hf_client = None
        self.last_llm_error: str | None = None
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
            "messages": [{"role": "user", "content": prompt}],
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
                messages=[{"role": "user", "content": prompt}],
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
        if normalized:
            self.last_llm_error = None
            return normalized
        self.logger.warning("Falling back to local mode formatter for mode=%s", mode)
        return self.fallback_response(
            mode,
            message=message,
            context=context,
            meta_context=meta_context,
            lesson_results=lesson_results,
        )

    async def handle_message(self, request: MessageRequest) -> tuple[str, int]:
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
        return answer, len(results)


service = BackendService()
app = FastAPI(title="Lessons Backend", version="2.2.0")
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


@app.post("/message", response_model=MessageResponse)
async def message(request: MessageRequest) -> MessageResponse:
    try:
        answer, _ = await service.handle_message(request)
        return MessageResponse(text=answer)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Downstream service error: {exc}") from exc


@app.post("/api/v1/respond", response_model=RespondResponse)
async def respond(request: MessageRequest) -> RespondResponse:
    try:
        answer, results_count = await service.handle_message(request)
        return RespondResponse(
            session_id=request.session_id,
            mode=request.mode,
            answer=answer,
            results_count=results_count,
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
