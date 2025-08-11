# Task 4.1: Document Upload Endpoint

## Objective
Create FastAPI endpoints for document upload with validation, error handling, and metadata management.

## Files to Create
- `backend/app/routes/documents.py` - Document upload/list endpoints
- `backend/app/models/api_responses.py` - API response models

## API Endpoints

### POST /api/documents/upload
- Accept single or multiple file uploads
- Validate file types and sizes
- Store documents with content-addressed naming
- Return document metadata

### GET /api/documents
- List all uploaded documents
- Return document metadata without content
- Support pagination if needed

### GET /api/documents/{doc_id}
- Get specific document metadata
- Optionally return document content

### DELETE /api/documents/{doc_id}
- Delete document and metadata
- Return success/error status

## Request/Response Models
- `DocumentUploadResponse` - Success response with document metadata
- `DocumentListResponse` - List of documents
- `ErrorResponse` - Standardized error format
- `DocumentMetadata` - Document info without content

## Validation & Security
- File type validation (PDF, DOCX, TXT only)
- File size limits from configuration
- Filename sanitization
- MIME type verification
- Request size limits

## Error Handling
- Invalid file types → 400 Bad Request
- File too large → 413 Payload Too Large
- Storage errors → 500 Internal Server Error
- Duplicate uploads → 200 OK (return existing)

## Success Criteria
- Upload endpoint accepts valid files
- Proper validation and error responses
- Document metadata returned correctly
- List endpoint shows all documents
- Delete endpoint removes documents

## Tests
- `tests/unit/test_document_routes.py`
  - Test successful file upload
  - Test file validation errors
  - Test file size limit enforcement
  - Test document listing
  - Test document deletion
  - Test error response formats
