# Memory Service

Сервис памяти диалогов.

Роль:

- Redis хранит оперативную память активной сессии
- Postgres хранит долгую историю диалогов и технические request logs

## Data model

- `dialogs`: `session_id`, `status`, `created_at`, `updated_at`, `completed_at`
- `messages`: `id`, `session_id`, `role`, `mode`, `content`, `created_at`
- `request_logs`: `id`, `session_id`, `method`, `path`, `status_code`, `duration_ms`, `payload_size`, `error_text`, `created_at`

## Endpoints

- `POST /sessions` - create new active session
- `GET /sessions/{session_id}` - get session with messages
- `GET /sessions/{session_id}/messages` - get message list in chronological order
- `POST /sessions/{session_id}/messages` - add message with explicit role
- `POST /sessions/{session_id}/messages/user` - add user message
- `POST /sessions/{session_id}/messages/assistant` - add assistant message
- `POST /sessions/{session_id}/complete` - finalize session
- `GET /health` and `GET /health/ready` - health checks
