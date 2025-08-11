"""API response models for document routes."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import SettingsConfigDict

from backend.app.models.document import DocumentMetadata


class ErrorResponse(BaseModel):
    code: str = Field(..., description="Error code identifier")
    message: str = Field(..., description="Human readable message")


class UploadErrorItem(BaseModel):
    filename: str
    code: str
    message: str


class DocumentUploadResponse(BaseModel):
    documents: List[DocumentMetadata] = Field(default_factory=list)
    errors: List[UploadErrorItem] = Field(default_factory=list)


class DocumentListResponse(BaseModel):
    documents: List[DocumentMetadata] = Field(default_factory=list)


class DocumentDeleteResponse(BaseModel):
    id: str
    success: bool


