from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from huggingface_hub import InferenceClient
from pydantic import BaseModel, Field

from config import HF_TOKEN, LLM_MODEL, LLM_PROVIDER, MEMORY_SERVICE_URL, RAG_SERVICE_URL, RETRIEVAL_TOP_K
from prompts import CHAT_PROMPT, DOCUMENT_PROMPT, MAIL_PROMPT, SEARCH_PROMPT


Mode = Literal["chat", "search", "document", "mail"]


class SessionResponse(BaseModel):
    session_id: str
    status: str


class RespondRequest(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1)
    mode: Mode = "chat"
    top_k: int = Field(default=RETRIEVAL_TOP_K, ge=1, le=20)


class RespondResponse(BaseModel):
    session_id: str
    mode: Mode
    answer: str
    results_count: int


class BackendService:
    def __init__(self) -> None:
        self.llm_client = None
        if HF_TOKEN:
            try:
                self.llm_client = InferenceClient(provider=LLM_PROVIDER, token=HF_TOKEN)
            except Exception:
                self.llm_client = None

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

    def history_to_text(self, messages: list[dict]) -> str:
        if not messages:
            return "История пока пустая."
        return "\n".join(f"{item['role']}: {item['content']}" for item in messages[-8:])

    def fallback_response(self, mode: Mode, message: str, context: str, results: list[dict]) -> str:
        if mode == "search":
            intro = f"По запросу найдено {len(results)} релевантных фрагментов."
            body = "\n\n".join(item["text"] for item in results[:3]) if results else "Релевантных уроков пока не найдено."
            return f"{intro}\n\n{body}"
        if mode == "document":
            return f"# Черновик\n## Тема\n{message}\n## Материалы\n{context or 'Контекст пока не найден.'}"
        if mode == "mail":
            return f"Коллеги,\n\nпо запросу \"{message}\" собран следующий контекст:\n{context or 'Контекст пока не найден.'}\n\nС уважением,\nКоманда раздела Извлеченные уроки"
        return context or "По запросу не найден релевантный контекст."

    def build_prompt(self, mode: Mode, message: str, history: str, context: str) -> str:
        if mode == "search":
            return SEARCH_PROMPT.format(message=message, history=history, context=context)
        if mode == "document":
            return DOCUMENT_PROMPT.format(message=message, history=history, context=context)
        if mode == "mail":
            return MAIL_PROMPT.format(message=message, history=history, context=context)
        return CHAT_PROMPT.format(message=message, history=history, context=context)

    def generate_text(self, mode: Mode, message: str, history: str, context: str, results: list[dict]) -> str:
        if not self.llm_client:
            return self.fallback_response(mode, message, context, results)
        prompt = self.build_prompt(mode, message, history, context)
        try:
            completion = self.llm_client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
            )
            content = completion.choices[0].message.content
            return content or self.fallback_response(mode, message, context, results)
        except Exception:
            return self.fallback_response(mode, message, context, results)


service = BackendService()
app = FastAPI(title="Lessons Backend", version="2.0.0")
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


@app.post("/api/v1/respond", response_model=RespondResponse)
async def respond(request: RespondRequest) -> RespondResponse:
    try:
        session = await service.call_memory("GET", f"/sessions/{request.session_id}")
        history_messages = session.get("messages", [])

        await service.call_memory(
            "POST",
            f"/sessions/{request.session_id}/messages",
            {"role": "user", "content": request.message, "mode": request.mode},
        )

        retrieval = await service.call_rag(
            {
                "query": request.message,
                "mode": request.mode,
                "top_k": request.top_k,
                "session_messages": history_messages,
            }
        )
        context = retrieval.get("context", "")
        results = retrieval.get("results", [])
        answer = service.generate_text(
            request.mode,
            request.message,
            service.history_to_text(history_messages),
            context,
            results,
        )

        await service.call_memory(
            "POST",
            f"/sessions/{request.session_id}/messages",
            {"role": "assistant", "content": answer, "mode": request.mode},
        )

        return RespondResponse(
            session_id=request.session_id,
            mode=request.mode,
            answer=answer,
            results_count=len(results),
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Downstream service error: {exc}") from exc


@app.get("/api/v1/health")
async def health() -> dict:
    memory = await service.call_memory("GET", "/health")
    async with httpx.AsyncClient(timeout=15.0) as client:
        rag_response = await client.get(f"{RAG_SERVICE_URL}/health")
        rag = rag_response.json()
    return {"status": "ok", "memory": memory, "rag": rag, "llm_enabled": bool(service.llm_client)}
