# AI Legal Assistant - Development Plan

## Overview
This plan breaks down the development of the AI legal assistant into 6 phases with specific tasks, files, and unit tests. Each task should be completed independently with full testing before moving to the next.

## Phase 1: Project Setup & Infrastructure

### Task 1.1: Initialize Poetry Project
**Files to create:**
- `pyproject.toml` - Poetry configuration with dependencies and scripts
- `.env.example` - Environment variable template
- `.gitignore` - Ignore patterns for Python/Node projects

**Dependencies:**
- Runtime: `fastapi`, `uvicorn`, `python-multipart`, `aiofiles`, `openai`, `pydantic`, `python-dotenv`
- Dev: `pytest`, `pytest-asyncio`, `pytest-watch`, `ruff`, `mypy`

**Tests:** None (setup task)

### Task 1.2: Create Project Structure
**Directories to create:**
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── routes/
│   ├── services/
│   ├── clients/
│   └── utils/
├── storage/
│   └── documents/
└── tests/
    ├── __init__.py
    ├── unit/
    └── integration/
frontend/
├── src/
├── public/
└── package.json
```

**Tests:** None (setup task)

### Task 1.3: Environment Configuration
**Files to create:**
- `backend/app/config.py` - Configuration management with Pydantic
- `.env.example` - Template for environment variables

**Environment variables:**
- `OPENAI_API_KEY`
- `UPLOAD_MAX_SIZE_MB`
- `STORAGE_PATH`
- `SESSION_STORAGE_PATH`

**Tests:** `tests/unit/test_config.py`

## Phase 2: Document Storage System

### Task 2.1: Document Storage Service
**Files to create:**
- `backend/app/services/document_service.py` - Document storage and retrieval
- `backend/app/models/document.py` - Pydantic models for documents

**Key features:**
- Content-addressed filename generation (SHA-256 hash)
- Async file operations with `aiofiles`
- Document metadata storage (filename, size, type, upload_time)
- Error handling for storage failures

**Tests:** `tests/unit/test_document_service.py`

### Task 2.2: File Validation & Utils
**Files to create:**
- `backend/app/utils/file_utils.py` - File validation and processing utilities
- `backend/app/utils/content_extraction.py` - Text extraction from PDF/DOCX

**Key features:**
- MIME type validation (PDF, DOCX, TXT only)
- File size limits
- Content extraction for different file types
- Security validation (no executable files)

**Tests:** `tests/unit/test_file_utils.py`

## Phase 3: Pluggable AI Model Client

### Task 3.1: Model Client Interface
**Files to create:**
- `backend/app/clients/base_model_client.py` - Abstract base class
- `backend/app/clients/openai_client.py` - OpenAI implementation
- `backend/app/models/chat.py` - Chat request/response models

**Key features:**
- Abstract interface for model clients
- OpenAI client with retry logic and error handling
- Support for Deep Research vs Regular modes
- Document context injection

**Tests:** `tests/unit/test_model_clients.py`

### Task 3.2: Streaming Response Handler
**Files to create:**
- `backend/app/clients/streaming_handler.py` - Streaming response processing
- `backend/app/utils/sse_utils.py` - Server-Sent Events utilities

**Key features:**
- Async streaming token processing
- SSE formatting for frontend consumption
- Error handling during streaming
- Connection management

**Tests:** `tests/unit/test_streaming.py`

## Phase 4: FastAPI Backend

### Task 4.1: Document Upload Endpoint
**Files to create:**
- `backend/app/routes/documents.py` - Document upload/list endpoints
- `backend/app/models/api_responses.py` - API response models

**Endpoints:**
- `POST /api/documents/upload` - Upload single/multiple documents
- `GET /api/documents` - List uploaded documents
- `GET /api/documents/{doc_id}` - Get document metadata

**Tests:** `tests/unit/test_document_routes.py`

### Task 4.2: Chat Endpoint
**Files to create:**
- `backend/app/routes/chat.py` - Chat endpoints with streaming
- `backend/app/services/chat_service.py` - Chat business logic

**Endpoints:**
- `POST /api/chat/sessions` - Create new chat session
- `POST /api/chat/sessions/{session_id}/messages` - Send message (streaming response)
- `GET /api/chat/sessions/{session_id}` - Get session history

**Tests:** `tests/unit/test_chat_routes.py`

### Task 4.3: Session Persistence
**Files to create:**
- `backend/app/services/session_service.py` - Session management
- `backend/app/models/session.py` - Session and message models
- `backend/app/storage/session_store.py` - File-based session storage

**Key features:**
- Session creation and retrieval
- Message history persistence
- File-based storage (JSON format)
- Session cleanup/expiration

**Tests:** `tests/unit/test_session_service.py`

## Phase 5: React Frontend

### Task 5.1: Frontend Setup
**Files to create:**
- `frontend/package.json` - Vite + React + TypeScript setup
- `frontend/src/main.tsx` - React app entry point
- `frontend/src/App.tsx` - Main application component
- `frontend/src/api/client.ts` - API client with fetch

**Dependencies:**
- `react`, `react-dom`, `typescript`, `vite`
- `@types/react`, `@types/react-dom`
- UI: `tailwindcss` or similar for styling

**Tests:** Basic component tests with `@testing-library/react`

### Task 5.2: Document Upload UI
**Files to create:**
- `frontend/src/components/DocumentUpload.tsx` - Drag & drop upload
- `frontend/src/components/DocumentList.tsx` - Uploaded documents display
- `frontend/src/hooks/useDocuments.ts` - Document management hook

**Key features:**
- Drag & drop file upload
- Progress indicators
- File type validation
- Error handling and user feedback

**Tests:** `frontend/src/components/__tests__/DocumentUpload.test.tsx`

### Task 5.3: Chat Interface
**Files to create:**
- `frontend/src/components/ChatInterface.tsx` - Main chat component
- `frontend/src/components/MessageList.tsx` - Message history display
- `frontend/src/components/MessageInput.tsx` - Message input with mode toggle
- `frontend/src/hooks/useChat.ts` - Chat state management
- `frontend/src/hooks/useStreaming.ts` - Streaming response handler

**Key features:**
- Real-time streaming message display
- Deep Research / Regular mode toggle
- Message history with document references
- Auto-scroll and typing indicators

**Tests:** Component tests for all chat UI components

## Phase 6: Integration & Polish

### Task 6.1: Integration Tests
**Files to create:**
- `tests/integration/test_upload_flow.py` - End-to-end upload testing
- `tests/integration/test_chat_flow.py` - End-to-end chat testing
- `tests/integration/test_streaming.py` - Streaming integration tests

**Key features:**
- Full upload → chat → response flow testing
- Multiple document handling
- Session persistence validation
- Error scenario testing

### Task 6.2: Documentation & Scripts
**Files to create:**
- `README.md` - Complete setup and usage instructions
- `docker-compose.yml` - Optional containerized deployment
- Update `pyproject.toml` with all necessary scripts

**Poetry scripts to add:**
- `dev` - Start backend development server
- `frontend` - Start frontend development server
- `test` - Run all tests
- `watch` - Run tests on file changes
- `fmt` - Format code with ruff
- `typecheck` - Run mypy type checking

## Testing Strategy

### Unit Tests
- Each service/utility class has comprehensive unit tests
- Mock external dependencies (OpenAI API, file system)
- Test error conditions and edge cases
- Aim for >80% code coverage

### Integration Tests
- Test complete workflows end-to-end
- Use temporary directories for file operations
- Test streaming responses
- Validate session persistence

### Development Workflow
1. Write tests first (TDD approach)
2. Implement minimal code to pass tests
3. Refactor and improve
4. Update documentation
5. Mark task as complete before moving to next

## File Organization Summary

```
ai-legal-assistant/
├── INTERVIEW_BRIEF.md
├── PROJECT_PLAN.md
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── routes/
│   │   │   ├── documents.py
│   │   │   └── chat.py
│   │   ├── services/
│   │   │   ├── document_service.py
│   │   │   ├── chat_service.py
│   │   │   └── session_service.py
│   │   ├── clients/
│   │   │   ├── base_model_client.py
│   │   │   ├── openai_client.py
│   │   │   └── streaming_handler.py
│   │   ├── models/
│   │   │   ├── document.py
│   │   │   ├── chat.py
│   │   │   ├── session.py
│   │   │   └── api_responses.py
│   │   └── utils/
│   │       ├── file_utils.py
│   │       ├── content_extraction.py
│   │       └── sse_utils.py
│   ├── storage/
│   │   ├── documents/
│   │   └── sessions/
│   └── tests/
│       ├── unit/
│       └── integration/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── api/
│   │   └── __tests__/
│   └── package.json
└── docker-compose.yml (optional)
```

This plan ensures each task is self-contained, testable, and builds incrementally toward the complete solution.
