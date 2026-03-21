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
        self.hf_client = None
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

    def fallback_response(self, mode: Mode, context: str, results: list[dict]) -> str:
        if mode == "search":
            intro = f"По запросу найдено {len(results)} релевантных фрагментов."
            base = "\n\n".join(item.get("text", "") for item in results[:4]).strip()
            return f"{intro}\n\n{base or context or 'Релевантные материалы не найдены.'}"
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
            completion = self.hf_client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
            )
            return completion.choices[0].message.content
        except Exception:
            return None

    async def generate_text(self, mode: Mode, message: str, history: str, context: str, meta_context: str, results: list[dict]) -> str:
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
            except httpx.HTTPError:
                generated = None
        if not generated:
            generated = await self.generate_hf(prompt)
        if generated:
            return generated
        return self.fallback_response(mode, context, results)

    async def handle_message(self, request: MessageRequest) -> tuple[str, int]:
        session = await self.call_memory("GET", f"/sessions/{request.session_id}")
        history_messages = session.get("messages", [])

        await self.call_memory(
            "POST",
            f"/sessions/{request.session_id}/messages",
            {"role": "user", "content": request.message, "mode": request.mode},
        )

        retrieval = await self.call_rag(
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

        answer = await self.generate_text(
            request.mode,
            request.message,
            self.history_to_text(history_messages),
            context,
            meta_context,
            results,
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
    memory = await service.call_memory("GET", "/health")
    async with httpx.AsyncClient(timeout=15.0) as client:
        rag_response = await client.get(f"{RAG_SERVICE_URL}/health")
        rag = rag_response.json()
    llm_mode = "openai_compatible" if LLM_BASE_URL else ("huggingface" if service.hf_client else "fallback")
    return {"status": "ok", "memory": memory, "rag": rag, "llm_mode": llm_mode}
