# Task 4.3: Session Persistence Service

## Objective
Implement session management with file-based persistence for chat history and metadata.

## Files to Create
- `backend/app/services/session_service.py` - Session management
- `backend/app/models/session.py` - Session and message models
- `backend/app/storage/session_store.py` - File-based session storage

## Session Models
```python
class ChatSession(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    title: Optional[str]
    messages: List[ChatMessage] = []

class ChatMessage(BaseModel):
    id: str
    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime
    mode: Optional[ChatMode]
    document_ids: List[str] = []
```

## Session Service Methods
- `create_session() -> ChatSession`
- `get_session(session_id: str) -> Optional[ChatSession]`
- `add_message(session_id: str, message: ChatMessage) -> bool`
- `list_sessions() -> List[ChatSession]`
- `delete_session(session_id: str) -> bool`
- `update_session_title(session_id: str, title: str) -> bool`

## Storage Implementation
- File-based storage using JSON format
- One file per session: `{session_id}.json`
- Atomic writes to prevent corruption
- Session metadata indexing
- Cleanup for old sessions

## Session Features
- Unique session ID generation (UUID4)
- Automatic title generation from first message
- Message history preservation
- Document reference tracking
- Session metadata (creation time, last update)

## Success Criteria
- Sessions persist across server restarts
- Message history maintained correctly
- Concurrent access handled safely
- Storage errors handled gracefully
- Session cleanup and management

## Tests
- `tests/unit/test_session_service.py`
  - Test session creation and retrieval
  - Test message addition and persistence
  - Test session listing
  - Test concurrent access scenarios
  - Test storage error handling
  - Test session cleanup
