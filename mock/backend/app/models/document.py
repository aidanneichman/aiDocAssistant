"""Document models for the AI Legal Assistant.

This module defines Pydantic models for document storage and metadata management.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Document(BaseModel):
    """Document model with metadata and storage information.
    
    Uses SHA-256 hash as the document ID for content-addressed storage.
    """
    
    id: str = Field(
        ...,
        description="SHA-256 hash of the document content (content-addressed ID)",
        min_length=64,
        max_length=64
    )
    
    original_filename: str = Field(
        ...,
        description="Original filename as uploaded by user",
        min_length=1,
        max_length=255
    )
    
    content_type: str = Field(
        ...,
        description="MIME type of the document",
        min_length=1
    )
    
    size_bytes: int = Field(
        ...,
        description="Size of the document in bytes",
        ge=0
    )
    
    upload_time: datetime = Field(
        ...,
        description="When the document was uploaded"
    )
    
    file_path: Path = Field(
        ...,
        description="Absolute path to the stored document file"
    )

    @field_validator("id")
    @classmethod
    def validate_document_id(cls, v: str) -> str:
        """Validate that the document ID is a valid SHA-256 hash."""
        if not all(c in "0123456789abcdef" for c in v.lower()):
            raise ValueError("Document ID must be a valid SHA-256 hash (hexadecimal)")
        return v.lower()

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        """Validate that content type is in expected format."""
        if "/" not in v:
            raise ValueError("Content type must be in format 'type/subtype'")
        return v.lower()

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: Path) -> Path:
        """Ensure file path is absolute."""
        return v.resolve()

    def get_file_extension(self) -> str:
        """Get the file extension from the original filename."""
        return Path(self.original_filename).suffix.lower()

    def get_size_mb(self) -> float:
        """Get document size in megabytes."""
        return self.size_bytes / (1024 * 1024)

    def is_pdf(self) -> bool:
        """Check if document is a PDF."""
        return self.content_type == "application/pdf"

    def is_docx(self) -> bool:
        """Check if document is a DOCX file."""
        return self.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def is_text(self) -> bool:
        """Check if document is plain text."""
        return self.content_type == "text/plain"

    model_config = {
        "json_encoders": {
            Path: str,
            datetime: lambda v: v.isoformat()
        }
    }


class DocumentCreate(BaseModel):
    """Model for document creation requests."""
    
    original_filename: str = Field(
        ...,
        description="Original filename",
        min_length=1,
        max_length=255
    )
    
    content_type: str = Field(
        ...,
        description="MIME type of the document"
    )
    
    file_data: bytes = Field(
        ...,
        description="Raw file data"
    )

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        """Validate content type format."""
        if "/" not in v:
            raise ValueError("Content type must be in format 'type/subtype'")
        return v.lower()


class DocumentMetadata(BaseModel):
    """Document metadata without file content for listing operations."""
    
    id: str
    original_filename: str
    content_type: str
    size_bytes: int
    upload_time: datetime
    
    @classmethod
    def from_document(cls, document: Document) -> "DocumentMetadata":
        """Create metadata from a full Document instance."""
        return cls(
            id=document.id,
            original_filename=document.original_filename,
            content_type=document.content_type,
            size_bytes=document.size_bytes,
            upload_time=document.upload_time
        )

    def get_size_mb(self) -> float:
        """Get document size in megabytes."""
        return self.size_bytes / (1024 * 1024)

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }
