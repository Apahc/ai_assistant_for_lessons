from typing import Any, Literal

from pydantic import BaseModel, Field


Mode = Literal["chat", "search", "document", "mail"]
SourceType = Literal["lesson", "meta", "report", "info_sheet", "letter", "glossary"]


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1)
    mode: Mode = "chat"
    top_k: int = Field(default=5, ge=1, le=20)
    session_messages: list[dict[str, Any]] = Field(default_factory=list)


class RetrievedChunk(BaseModel):
    id: str
    text: str
    title: str
    source_type: SourceType
    metadata: dict[str, Any] = Field(default_factory=dict)
    distance: float | None = None
    rerank_score: float | None = None


class RetrieveResponse(BaseModel):
    mode: Mode
    query: str
    search_query: str
    results: list[RetrievedChunk]
    lesson_results: list[RetrievedChunk]
    meta_results: list[RetrievedChunk]
    context: str
    meta_context: str
    lessons_texts: list[str]
    lessons_count: int
    meta_count: int
