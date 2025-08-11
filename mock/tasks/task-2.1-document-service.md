# Task 2.1: Document Storage Service

## Objective
Create document storage and retrieval service with content-addressed filenames and metadata management.

## Files to Create
- `backend/app/services/document_service.py` - Document storage and retrieval
- `backend/app/models/document.py` - Pydantic models for documents

## Key Features
- Content-addressed filename generation (SHA-256 hash)
- Async file operations with `aiofiles`
- Document metadata storage (filename, size, type, upload_time)
- Error handling for storage failures
- Duplicate detection via content hash

## Document Model Structure
```python
class Document(BaseModel):
    id: str  # SHA-256 hash
    original_filename: str
    content_type: str
    size_bytes: int
    upload_time: datetime
    file_path: Path
```

## Service Methods
- `store_document(file_data: bytes, filename: str, content_type: str) -> Document`
- `get_document(document_id: str) -> Optional[Document]`
- `list_documents() -> List[Document]`
- `delete_document(document_id: str) -> bool`
- `get_document_content(document_id: str) -> bytes`

## Success Criteria
- Documents stored with SHA-256 hash filenames
- Metadata persisted alongside files
- Async operations for all file I/O
- Proper error handling for storage failures
- No duplicate storage of identical content

## Tests
- `tests/unit/test_document_service.py`
  - Test document storage with various file types
  - Test duplicate detection
  - Test metadata persistence and retrieval
  - Test error handling for invalid files
  - Test document listing and deletion
