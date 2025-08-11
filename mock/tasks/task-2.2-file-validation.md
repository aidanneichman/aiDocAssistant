# Task 2.2: File Validation & Content Extraction

## Objective
Implement comprehensive file validation and text extraction utilities for supported document types.

## Files to Create
- `backend/app/utils/file_utils.py` - File validation and processing utilities
- `backend/app/utils/content_extraction.py` - Text extraction from PDF/DOCX

## File Validation Features
- MIME type validation (PDF, DOCX, TXT only)
- File size limits (configurable via environment)
- Security validation (no executable files, scripts)
- File signature verification (magic bytes)
- Filename sanitization

## Content Extraction Features
- Plain text extraction from TXT files
- Text extraction from PDF files (using PyPDF2 or similar)
- Text extraction from DOCX files (using python-docx)
- Error handling for corrupted files
- Encoding detection and handling

## Supported File Types
- `text/plain` (.txt)
- `application/pdf` (.pdf)
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (.docx)

## Utility Functions
- `validate_file_type(content_type: str, filename: str) -> bool`
- `validate_file_size(size_bytes: int, max_size_mb: int) -> bool`
- `extract_text_content(file_path: Path, content_type: str) -> str`
- `sanitize_filename(filename: str) -> str`
- `detect_file_type(file_data: bytes) -> str`

## Dependencies to Add
- `PyPDF2` or `pypdf` - PDF text extraction
- `python-docx` - DOCX text extraction
- `python-magic` - File type detection (optional)

## Success Criteria
- Only allowed file types pass validation
- File size limits enforced
- Text extraction works for all supported formats
- Security checks prevent malicious file uploads
- Graceful error handling for corrupted files

## Tests
- `tests/unit/test_file_utils.py`
  - Test file type validation with valid/invalid types
  - Test file size validation
  - Test filename sanitization
  - Test text extraction from each supported format
  - Test error handling for corrupted files
