"""File validation and processing utilities for the AI Legal Assistant.

This module provides comprehensive file validation including MIME type checking,
file size limits, security validation, and filename sanitization.
"""

import logging
import mimetypes
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# Supported file types mapping
SUPPORTED_MIME_TYPES: Dict[str, Set[str]] = {
    "text/plain": {".txt", ".text"},
    "application/pdf": {".pdf"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
}

# File signature magic bytes for security validation
FILE_SIGNATURES: Dict[str, List[bytes]] = {
    "application/pdf": [b"%PDF-"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
        b"PK\x03\x04"  # DOCX files are ZIP archives
    ],
    "text/plain": [],  # Text files don't have a specific signature
}

# Dangerous file extensions that should never be allowed
DANGEROUS_EXTENSIONS: Set[str] = {
    ".exe", ".bat", ".cmd", ".com", ".scr", ".pif", ".vbs", ".js", ".jar",
    ".app", ".deb", ".pkg", ".dmg", ".rpm", ".msi", ".sh", ".bash", ".ps1",
    ".py", ".php", ".asp", ".jsp", ".html", ".htm", ".xml", ".svg"
}

# Maximum filename length
MAX_FILENAME_LENGTH = 255


class FileValidationError(Exception):
    """Base exception for file validation errors."""
    pass


class UnsupportedFileTypeError(FileValidationError):
    """Exception raised when file type is not supported."""
    pass


class FileSizeExceededError(FileValidationError):
    """Exception raised when file size exceeds limits."""
    pass


class SecurityValidationError(FileValidationError):
    """Exception raised when file fails security validation."""
    pass


class InvalidFilenameError(FileValidationError):
    """Exception raised when filename is invalid."""
    pass


def validate_file_type(content_type: str, filename: str) -> bool:
    """Validate that the file type is supported.
    
    Args:
        content_type: MIME type of the file
        filename: Original filename
        
    Returns:
        bool: True if file type is supported
        
    Raises:
        UnsupportedFileTypeError: If file type is not supported
    """
    try:
        # Normalize content type
        content_type = content_type.lower().strip()
        
        # Check if MIME type is supported
        if content_type not in SUPPORTED_MIME_TYPES:
            raise UnsupportedFileTypeError(
                f"Unsupported file type: {content_type}. "
                f"Supported types: {list(SUPPORTED_MIME_TYPES.keys())}"
            )
        
        # Get file extension
        file_extension = Path(filename).suffix.lower()
        
        # Check for dangerous extensions first (security check)
        if file_extension in DANGEROUS_EXTENSIONS:
            raise SecurityValidationError(
                f"Potentially dangerous file extension: {file_extension}"
            )
        
        # Check if extension matches the MIME type
        expected_extensions = SUPPORTED_MIME_TYPES[content_type]
        if file_extension not in expected_extensions:
            raise UnsupportedFileTypeError(
                f"File extension '{file_extension}' does not match "
                f"content type '{content_type}'. Expected: {expected_extensions}"
            )
        
        logger.info(f"File type validation passed: {content_type} ({file_extension})")
        return True
        
    except (UnsupportedFileTypeError, SecurityValidationError):
        raise
    except Exception as e:
        logger.error(f"Error validating file type: {e}")
        raise FileValidationError(f"File type validation failed: {e}") from e


def validate_file_size(size_bytes: int, max_size_mb: int) -> bool:
    """Validate that file size is within limits.
    
    Args:
        size_bytes: File size in bytes
        max_size_mb: Maximum allowed size in megabytes
        
    Returns:
        bool: True if file size is acceptable
        
    Raises:
        FileSizeExceededError: If file size exceeds limit
    """
    try:
        if size_bytes < 0:
            raise FileValidationError("File size cannot be negative")
        
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if size_bytes > max_size_bytes:
            size_mb = size_bytes / (1024 * 1024)
            raise FileSizeExceededError(
                f"File size ({size_mb:.2f} MB) exceeds maximum allowed "
                f"size ({max_size_mb} MB)"
            )
        
        if size_bytes == 0:
            raise FileValidationError("File is empty")
        
        logger.info(f"File size validation passed: {size_bytes} bytes")
        return True
        
    except (FileSizeExceededError, FileValidationError):
        raise
    except Exception as e:
        logger.error(f"Error validating file size: {e}")
        raise FileValidationError(f"File size validation failed: {e}") from e


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent security issues and ensure compatibility.
    
    Args:
        filename: Original filename
        
    Returns:
        str: Sanitized filename
        
    Raises:
        InvalidFilenameError: If filename cannot be sanitized
    """
    try:
        if not filename or not filename.strip():
            raise InvalidFilenameError("Filename cannot be empty")
        
        # Remove leading/trailing whitespace
        filename = filename.strip()
        
        # Check original length
        if len(filename) > MAX_FILENAME_LENGTH:
            raise InvalidFilenameError(
                f"Filename too long ({len(filename)} chars). "
                f"Maximum: {MAX_FILENAME_LENGTH}"
            )
        
        # Remove or replace dangerous characters
        # Keep alphanumeric, dots, hyphens, underscores, and spaces
        sanitized = re.sub(r'[^\w\s.-]', '_', filename)
        
        # Replace multiple spaces/underscores with single ones
        sanitized = re.sub(r'\s+', ' ', sanitized)
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # Remove leading dots (hidden files)
        sanitized = sanitized.lstrip('.')
        
        # Ensure we still have a filename after sanitization
        if not sanitized or sanitized.isspace():
            raise InvalidFilenameError("Filename becomes empty after sanitization")
        
        # Preserve file extension if it exists
        original_path = Path(filename)
        if original_path.suffix:
            sanitized_path = Path(sanitized)
            if not sanitized_path.suffix:
                # Add back the extension if it was lost
                sanitized += original_path.suffix
        
        logger.info(f"Filename sanitized: '{filename}' -> '{sanitized}'")
        return sanitized
        
    except InvalidFilenameError:
        raise
    except Exception as e:
        logger.error(f"Error sanitizing filename: {e}")
        raise InvalidFilenameError(f"Filename sanitization failed: {e}") from e


def detect_file_type(file_data: bytes, filename: str = "") -> str:
    """Detect file type from content and filename.
    
    Args:
        file_data: Raw file content
        filename: Optional filename for additional context
        
    Returns:
        str: Detected MIME type
        
    Raises:
        UnsupportedFileTypeError: If file type cannot be determined or is unsupported
    """
    try:
        if not file_data:
            raise FileValidationError("File data is empty")
        
        # First, try to detect by file signature (magic bytes)
        detected_type = _detect_by_signature(file_data)
        
        if detected_type:
            logger.info(f"File type detected by signature: {detected_type}")
            return detected_type
        
        # Fallback to filename-based detection
        if filename:
            detected_type = _detect_by_filename(filename)
            if detected_type:
                logger.info(f"File type detected by filename: {detected_type}")
                return detected_type
        
        # If we can't detect the type, check if it might be text content
        if len(file_data) < 1024 * 1024 and _is_text_content(file_data):
            # Only return text/plain if filename suggests it's a text file
            if filename and Path(filename).suffix.lower() in {'.txt', '.text'}:
                logger.info("File type detected as text/plain by content analysis")
                return "text/plain"
        
        raise UnsupportedFileTypeError(
            "Could not determine file type from content or filename"
        )
        
    except (UnsupportedFileTypeError, FileValidationError):
        raise
    except Exception as e:
        logger.error(f"Error detecting file type: {e}")
        raise FileValidationError(f"File type detection failed: {e}") from e


def _detect_by_signature(file_data: bytes) -> Optional[str]:
    """Detect file type by magic bytes signature."""
    for mime_type, signatures in FILE_SIGNATURES.items():
        for signature in signatures:
            if file_data.startswith(signature):
                return mime_type
    return None


def _detect_by_filename(filename: str) -> Optional[str]:
    """Detect file type by filename extension."""
    try:
        # Use mimetypes library for initial detection
        detected_type, _ = mimetypes.guess_type(filename)
        
        if detected_type and detected_type.lower() in SUPPORTED_MIME_TYPES:
            return detected_type.lower()
        
        # Manual mapping for extensions
        extension = Path(filename).suffix.lower()
        for mime_type, extensions in SUPPORTED_MIME_TYPES.items():
            if extension in extensions:
                return mime_type
        
        return None
        
    except Exception:
        return None


def _is_text_content(data: bytes) -> bool:
    """Check if content appears to be text."""
    try:
        # Try to decode as UTF-8
        text = data.decode('utf-8')
        
        # Check if it contains mostly printable characters
        printable_chars = sum(1 for c in text if c.isprintable() or c.isspace())
        total_chars = len(text)
        
        if total_chars == 0:
            return False
        
        # If more than 95% of characters are printable, consider it text
        return (printable_chars / total_chars) > 0.95
        
    except UnicodeDecodeError:
        # Try other common encodings
        for encoding in ['latin-1', 'cp1252', 'ascii']:
            try:
                data.decode(encoding)
                return True
            except UnicodeDecodeError:
                continue
        return False


def validate_file_security(file_data: bytes, filename: str, content_type: str) -> bool:
    """Perform comprehensive security validation on a file.
    
    Args:
        file_data: Raw file content
        filename: Original filename
        content_type: MIME type
        
    Returns:
        bool: True if file passes all security checks
        
    Raises:
        SecurityValidationError: If file fails security validation
    """
    try:
        # Check file signature matches declared content type
        detected_type = detect_file_type(file_data, filename)
        
        if detected_type != content_type.lower():
            raise SecurityValidationError(
                f"File signature ({detected_type}) does not match "
                f"declared content type ({content_type})"
            )
        
        # Additional security checks for specific file types
        if content_type.lower() == "application/pdf":
            _validate_pdf_security(file_data)
        elif content_type.lower() == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            _validate_docx_security(file_data)
        
        logger.info(f"Security validation passed for {filename}")
        return True
        
    except SecurityValidationError:
        raise
    except Exception as e:
        logger.error(f"Error in security validation: {e}")
        raise SecurityValidationError(f"Security validation failed: {e}") from e


def _validate_pdf_security(file_data: bytes) -> None:
    """Validate PDF file security."""
    # Check for basic PDF structure
    if not file_data.startswith(b"%PDF-"):
        raise SecurityValidationError("Invalid PDF signature")
    
    # Check for PDF trailer (basic structure validation)
    if b"%%EOF" not in file_data:
        raise SecurityValidationError("PDF file appears to be corrupted or incomplete")


def _validate_docx_security(file_data: bytes) -> None:
    """Validate DOCX file security."""
    # DOCX files are ZIP archives, check ZIP signature
    if not file_data.startswith(b"PK\x03\x04"):
        raise SecurityValidationError("Invalid DOCX/ZIP signature")
    
    # Basic size check - DOCX files should have some minimum structure
    if len(file_data) < 1000:  # Very small for a DOCX file
        raise SecurityValidationError("DOCX file appears to be too small or corrupted")


def get_file_info(file_data: bytes, filename: str) -> Dict[str, any]:
    """Get comprehensive file information.
    
    Args:
        file_data: Raw file content
        filename: Original filename
        
    Returns:
        dict: File information including type, size, validation status
    """
    try:
        sanitized_name = sanitize_filename(filename)
        detected_type = detect_file_type(file_data, filename)
        
        return {
            "original_filename": filename,
            "sanitized_filename": sanitized_name,
            "detected_content_type": detected_type,
            "size_bytes": len(file_data),
            "size_mb": len(file_data) / (1024 * 1024),
            "extension": Path(filename).suffix.lower(),
            "is_supported": detected_type in SUPPORTED_MIME_TYPES,
            "validation_passed": True
        }
        
    except Exception as e:
        return {
            "original_filename": filename,
            "sanitized_filename": None,
            "detected_content_type": None,
            "size_bytes": len(file_data) if file_data else 0,
            "size_mb": 0,
            "extension": Path(filename).suffix.lower() if filename else "",
            "is_supported": False,
            "validation_passed": False,
            "error": str(e)
        }
