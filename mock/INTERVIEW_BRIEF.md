# Mock Interview Brief (Founder/Engineer prompt)

## Goal
Ship a minimal, production-style slice of an AI legal assistant:

- Upload 1–N documents (PDF/Docx/TXT).
- Start a chat session; toggle between Deep Research and Regular modes.
- Messages should reference the uploaded docs (pass document handles to the backend → model).
- Show streaming tokens in the UI (bonus-but-expected).
- Persist session transcripts (in a file/db) so refresh doesn't lose state.

## Constraints
- **Backend**: Python 3.11+, Poetry for deps. Framework: FastAPI.
- **Frontend**: Up to you (React/Vite recommended). Keep it clean, simple, and fast.
- **Infra-minded**: Treat documents as large; store on disk (local "S3" folder) with content-addressed filenames; no in-memory blobs.
- **Config**: All secrets via env vars (no hardcoding).
- **No vendor lock**: Make the OpenAI client pluggable (an interface + impl).

## Success criteria (we'll evaluate)
- **Correctness**: Upload works, chats work in both modes, documents flow into the model call.
- **Resilience**: Good error handling + retries; graceful failures.
- **Streaming**: Real-time token stream in UI (SSE or fetch-stream).
- **Design**: Clear separation of concerns: routes, services, model clients.
- **Security hygiene**: Don't log secrets; validate file types; size limits.
- **DX**: Readable code, clear README, poetry run ... starts everything.

## Stretch goals (nice-to-have)
- Sessions stored in SQLite with migrations.
- "Citations" list: return doc/page IDs used by the model for each answer.
- Simple RBAC (dummy user/session cookie).
- Dockerfile + a one-liner to run both services.
- Basic tests (pytest) for upload + message flow.
