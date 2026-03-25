import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import psycopg
import redis
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from psycopg.rows import dict_row


REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://lessons:lessons@postgres:5432/lessons")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "14400"))
DB_STARTUP_RETRIES = int(os.getenv("DB_STARTUP_RETRIES", "20"))
DB_STARTUP_RETRY_DELAY_SECONDS = float(os.getenv("DB_STARTUP_RETRY_DELAY_SECONDS", "2"))

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
app = FastAPI(title="Lessons Memory Service", version="2.1.0")


class SessionResponse(BaseModel):
    session_id: str
    status: str


class MessageCreate(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1)
    mode: str = Field(default="chat", min_length=1)


class RoleMessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
    mode: str = Field(default="chat", min_length=1)


class MessageDTO(BaseModel):
    role: str
    content: str
    mode: str
    created_at: str


class SessionWithMessagesResponse(BaseModel):
    session_id: str
    status: str
    messages: list[MessageDTO]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_ts(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def get_conn():
    return psycopg.connect(POSTGRES_DSN)


def ensure_schema() -> None:
    last_error: Exception | None = None
    for _ in range(DB_STARTUP_RETRIES):
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        create table if not exists dialogs (
                            session_id text primary key,
                            status text not null,
                            created_at timestamptz not null,
                            updated_at timestamptz not null,
                            completed_at timestamptz null
                        );
                        """
                    )
                    cur.execute(
                        """
                        create table if not exists messages (
                            id bigserial primary key,
                            session_id text not null references dialogs(session_id) on delete cascade,
                            role text not null,
                            mode text not null,
                            content text not null,
                            created_at timestamptz not null
                        );
                        """
                    )
                    cur.execute(
                        """
                        create table if not exists request_logs (
                            id bigserial primary key,
                            session_id text null,
                            method text not null,
                            path text not null,
                            status_code int not null,
                            duration_ms int not null,
                            payload_size int not null default 0,
                            error_text text null,
                            created_at timestamptz not null
                        );
                        """
                    )
                    cur.execute(
                        """
                        create index if not exists idx_messages_session_id on messages(session_id);
                        """
                    )
                    cur.execute(
                        """
                        create index if not exists idx_request_logs_session_id on request_logs(session_id);
                        """
                    )
                conn.commit()
            return
        except Exception as exc:
            last_error = exc
            time.sleep(DB_STARTUP_RETRY_DELAY_SECONDS)
    raise RuntimeError("Postgres is not available") from last_error


def redis_messages_key(session_id: str) -> str:
    return f"session:{session_id}:messages"


def redis_meta_key(session_id: str) -> str:
    return f"session:{session_id}:meta"


def touch_redis_session(session_id: str) -> None:
    redis_client.expire(redis_messages_key(session_id), SESSION_TTL_SECONDS)
    redis_client.expire(redis_meta_key(session_id), SESSION_TTL_SECONDS)


def parse_session_id_from_path(path: str) -> str | None:
    parts = [part for part in path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "sessions":
        return parts[1]
    return None


def persist_request_log(
    *,
    session_id: str | None,
    method: str,
    path: str,
    status_code: int,
    duration_ms: int,
    payload_size: int,
    error_text: str | None = None,
) -> None:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into request_logs
                    (session_id, method, path, status_code, duration_ms, payload_size, error_text, created_at)
                    values (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        session_id,
                        method,
                        path,
                        status_code,
                        duration_ms,
                        payload_size,
                        error_text,
                        utc_now(),
                    ),
                )
            conn.commit()
    except Exception:
        # Keep API flow resilient even if log writing fails.
        return


def load_dialog(session_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "select session_id, status, created_at, updated_at, completed_at from dialogs where session_id = %s",
                (session_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def load_messages_from_postgres(session_id: str) -> list[dict[str, Any]]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select role, content, mode, created_at
                from messages
                where session_id = %s
                order by id asc
                """,
                (session_id,),
            )
            rows = cur.fetchall()
            return [dict(row) for row in rows]


def load_messages(session_id: str) -> tuple[list[dict[str, Any]], str]:
    """Postgres is the source of truth. Redis is a cache; resync if lengths diverge."""
    rows = load_messages_from_postgres(session_id)
    redis_key = redis_messages_key(session_id)
    formatted = [
        {
            "role": row["role"],
            "content": row["content"],
            "mode": row["mode"],
            "created_at": iso_ts(row["created_at"]),
        }
        for row in rows
    ]

    if formatted:
        if redis_client.llen(redis_key) != len(formatted):
            redis_client.delete(redis_key)
            for item in formatted:
                redis_client.rpush(redis_key, json.dumps(item, ensure_ascii=False))
        touch_redis_session(session_id)
        return formatted, "postgres"

    raw_messages = redis_client.lrange(redis_key, 0, -1)
    if raw_messages:
        touch_redis_session(session_id)
        return [json.loads(item) for item in raw_messages], "redis"
    return [], "empty"


def ensure_active_dialog(session_id: str) -> dict[str, Any]:
    dialog = load_dialog(session_id)
    if not dialog:
        raise HTTPException(status_code=404, detail="Session not found")
    if dialog["status"] != "active":
        raise HTTPException(status_code=409, detail=f"Session is not active: {dialog['status']}")
    return dialog


def append_message(session_id: str, role: str, content: str, mode: str) -> SessionResponse:
    ensure_active_dialog(session_id)

    created_at = utc_now()
    payload = {
        "role": role,
        "content": content,
        "mode": mode,
        "created_at": iso_ts(created_at),
    }

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into messages (session_id, role, mode, content, created_at)
                values (%s, %s, %s, %s, %s)
                """,
                (session_id, role, mode, content, created_at),
            )
            cur.execute(
                """
                update dialogs
                set updated_at = %s, status = %s
                where session_id = %s
                """,
                (created_at, "active", session_id),
            )
        conn.commit()

    try:
        redis_client.rpush(redis_messages_key(session_id), json.dumps(payload, ensure_ascii=False))
        redis_client.hset(
            redis_meta_key(session_id),
            mapping={
                "status": "active",
                "updated_at": payload["created_at"],
            },
        )
        touch_redis_session(session_id)
    except redis.exceptions.RedisError:
        pass

    return SessionResponse(session_id=session_id, status="active")


@app.middleware("http")
async def request_logger(request: Request, call_next):
    started = time.perf_counter()
    payload_size = int(request.headers.get("content-length", "0") or "0")
    session_id = parse_session_id_from_path(request.url.path)
    error_text = None
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception as exc:
        error_text = str(exc)
        raise
    finally:
        duration_ms = int((time.perf_counter() - started) * 1000)
        persist_request_log(
            session_id=session_id,
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            duration_ms=duration_ms,
            payload_size=payload_size,
            error_text=error_text,
        )


@app.on_event("startup")
async def startup() -> None:
    ensure_schema()


@app.get("/health")
async def health() -> dict:
    redis_ok = bool(redis_client.ping())
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("select 1")
            cur.fetchone()
    return {"status": "ok", "redis": redis_ok, "postgres": True}


@app.get("/health/ready")
async def health_ready() -> dict:
    return await health()


@app.post("/sessions", response_model=SessionResponse)
async def create_session() -> SessionResponse:
    session_id = uuid.uuid4().hex
    now = utc_now()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into dialogs (session_id, status, created_at, updated_at, completed_at)
                values (%s, %s, %s, %s, %s)
                """,
                (session_id, "active", now, now, None),
            )
        conn.commit()

    redis_client.hset(
        redis_meta_key(session_id),
        mapping={
            "status": "active",
            "created_at": iso_ts(now),
            "updated_at": iso_ts(now),
        },
    )
    touch_redis_session(session_id)
    return SessionResponse(session_id=session_id, status="active")


@app.get("/sessions/{session_id}", response_model=SessionWithMessagesResponse)
async def get_session(session_id: str) -> SessionWithMessagesResponse:
    dialog = load_dialog(session_id)
    if not dialog:
        raise HTTPException(status_code=404, detail="Session not found")

    messages, _ = load_messages(session_id)
    return SessionWithMessagesResponse(
        session_id=session_id,
        status=dialog["status"],
        messages=[MessageDTO(**item) for item in messages],
    )


@app.get("/sessions/{session_id}/messages", response_model=list[MessageDTO])
async def get_session_messages(session_id: str) -> list[MessageDTO]:
    dialog = load_dialog(session_id)
    if not dialog:
        raise HTTPException(status_code=404, detail="Session not found")
    messages, _ = load_messages(session_id)
    return [MessageDTO(**item) for item in messages]


@app.post("/sessions/{session_id}/messages", response_model=SessionResponse)
async def add_message(session_id: str, request: MessageCreate) -> SessionResponse:
    return append_message(session_id, request.role, request.content, request.mode)


@app.post("/sessions/{session_id}/messages/user", response_model=SessionResponse)
async def add_user_message(session_id: str, request: RoleMessageCreate) -> SessionResponse:
    return append_message(session_id, "user", request.content, request.mode)


@app.post("/sessions/{session_id}/messages/assistant", response_model=SessionResponse)
async def add_assistant_message(session_id: str, request: RoleMessageCreate) -> SessionResponse:
    return append_message(session_id, "assistant", request.content, request.mode)


@app.post("/sessions/{session_id}/complete", response_model=SessionResponse)
async def complete_session(session_id: str) -> SessionResponse:
    dialog = load_dialog(session_id)
    if not dialog:
        raise HTTPException(status_code=404, detail="Session not found")
    if dialog["status"] != "active":
        return SessionResponse(session_id=session_id, status=dialog["status"])

    ended_at = utc_now()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update dialogs
                set status = %s, updated_at = %s, completed_at = %s
                where session_id = %s
                """,
                ("completed", ended_at, ended_at, session_id),
            )
        conn.commit()

    redis_client.delete(redis_messages_key(session_id))
    redis_client.delete(redis_meta_key(session_id))
    return SessionResponse(session_id=session_id, status="completed")
