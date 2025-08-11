# Task 4.2: Chat Endpoint with Streaming

## Objective
Create chat endpoints supporting streaming responses, session management, and document context integration.

## Files to Create
- `backend/app/routes/chat.py` - Chat endpoints with streaming
- `backend/app/services/chat_service.py` - Chat business logic

## API Endpoints

### POST /api/chat/sessions
- Create new chat session
- Return session ID and metadata
- Initialize empty message history

### POST /api/chat/sessions/{session_id}/messages
- Send message to existing session
- Stream response tokens via SSE
- Support Deep Research / Regular modes
- Include document references

### GET /api/chat/sessions/{session_id}
- Retrieve complete session history
- Return all messages and metadata
- Include document references used

### GET /api/chat/sessions
- List all chat sessions
- Return session metadata only

## Request Models
- `CreateSessionRequest` - Session creation parameters
- `SendMessageRequest` - Message with mode and document IDs
- `ChatMode` - Enum: "regular" | "deep_research"

## Response Models
- `SessionResponse` - Session metadata
- `MessageResponse` - Individual message data
- `SessionHistoryResponse` - Complete session with messages

## Chat Service Features
- Message validation and preprocessing
- Document context retrieval and injection
- Model client integration
- Session persistence coordination
- Error handling and recovery

## Streaming Implementation
- Use FastAPI's `StreamingResponse`
- Format as Server-Sent Events
- Handle client disconnections
- Proper error propagation

## Success Criteria
- Sessions created and managed correctly
- Messages sent and responses streamed
- Document context included in responses
- Both chat modes work differently
- Session history persisted and retrievable

## Tests
- `tests/unit/test_chat_routes.py`
  - Test session creation
  - Test message sending (mocked streaming)
  - Test session history retrieval
  - Test document context integration
  - Test chat mode differences
  - Test error handling
