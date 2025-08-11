"""Document storage service for the AI Legal Assistant.

This service provides content-addressed document storage with metadata management.
All file operations are async and use SHA-256 hashing for deduplication.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import aiofiles
import aiofiles.os
from pydantic import ValidationError

from backend.app.config import get_settings
from backend.app.models.document import Document, DocumentCreate, DocumentMetadata

logger = logging.getLogger(__name__)


class DocumentStorageError(Exception):
    """Base exception for document storage operations."""
    pass


class DocumentNotFoundError(DocumentStorageError):
    """Exception raised when a document is not found."""
    pass


class DocumentService:
    """Service for managing document storage and retrieval.
    
    Features:
    - Content-addressed storage using SHA-256 hashes
    - Async file operations
    - Metadata persistence
    - Duplicate detection
    - Error handling and logging
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize the document service.
        
        Args:
            storage_path: Optional custom storage path. If None, uses config.
        """
        self.settings = get_settings()
        self.storage_path = storage_path or self.settings.storage_path
        self.metadata_path = self.storage_path / "metadata"
        
        # Ensure directories exist
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.metadata_path.mkdir(parents=True, exist_ok=True)

    def _get_content_hash(self, content: bytes) -> str:
        """Generate SHA-256 hash of content for content-addressed storage."""
        return hashlib.sha256(content).hexdigest()

    def _get_document_file_path(self, document_id: str) -> Path:
        """Get the file path for a document by its ID."""
        return self.storage_path / document_id

    def _get_metadata_file_path(self, document_id: str) -> Path:
        """Get the metadata file path for a document by its ID."""
        return self.metadata_path / f"{document_id}.json"

    async def store_document(
        self, 
        file_data: bytes, 
        filename: str, 
        content_type: str
    ) -> Document:
        """Store a document with content-addressed naming.
        
        Args:
            file_data: Raw file content as bytes
            filename: Original filename
            content_type: MIME type of the file
            
        Returns:
            Document: The stored document with metadata
            
        Raises:
            DocumentStorageError: If storage operation fails
        """
        try:
            # Generate content hash for deduplication
            document_id = self._get_content_hash(file_data)
            file_path = self._get_document_file_path(document_id)
            metadata_path = self._get_metadata_file_path(document_id)
            
            # Check if document already exists (deduplication)
            if await aiofiles.os.path.exists(file_path):
                logger.info(f"Document {document_id} already exists, returning existing metadata")
                existing_doc = await self.get_document(document_id)
                if existing_doc:
                    return existing_doc
            
            # Create document model
            document = Document(
                id=document_id,
                original_filename=filename,
                content_type=content_type,
                size_bytes=len(file_data),
                upload_time=datetime.utcnow(),
                file_path=file_path
            )
            
            # Store file content
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_data)
            
            # Store metadata
            metadata_dict = document.model_dump(mode='json')
            async with aiofiles.open(metadata_path, 'w') as f:
                await f.write(json.dumps(metadata_dict, indent=2, default=str))
            
            logger.info(f"Stored document {document_id} ({len(file_data)} bytes)")
            return document
            
        except Exception as e:
            logger.error(f"Failed to store document {filename}: {e}")
            raise DocumentStorageError(f"Failed to store document: {e}") from e

    async def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieve document metadata by ID.
        
        Args:
            document_id: SHA-256 hash ID of the document
            
        Returns:
            Document: Document metadata if found, None otherwise
        """
        try:
            metadata_path = self._get_metadata_file_path(document_id)
            
            if not await aiofiles.os.path.exists(metadata_path):
                return None
            
            async with aiofiles.open(metadata_path, 'r') as f:
                metadata_json = await f.read()
            
            metadata_dict = json.loads(metadata_json)
            return Document(**metadata_dict)
            
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Failed to parse document metadata {document_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve document {document_id}: {e}")
            return None

    async def get_document_content(self, document_id: str) -> bytes:
        """Retrieve document content by ID.
        
        Args:
            document_id: SHA-256 hash ID of the document
            
        Returns:
            bytes: Raw document content
            
        Raises:
            DocumentNotFoundError: If document is not found
            DocumentStorageError: If read operation fails
        """
        try:
            file_path = self._get_document_file_path(document_id)
            
            if not await aiofiles.os.path.exists(file_path):
                raise DocumentNotFoundError(f"Document {document_id} not found")
            
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()
            
            return content
            
        except DocumentNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to read document content {document_id}: {e}")
            raise DocumentStorageError(f"Failed to read document: {e}") from e

    async def list_documents(self) -> List[DocumentMetadata]:
        """List all stored documents.
        
        Returns:
            List[DocumentMetadata]: List of document metadata
        """
        documents = []
        
        try:
            # Iterate through metadata files
            if not self.metadata_path.exists():
                return documents
                
            for metadata_file in self.metadata_path.glob("*.json"):
                try:
                    async with aiofiles.open(metadata_file, 'r') as f:
                        metadata_json = await f.read()
                    
                    metadata_dict = json.loads(metadata_json)
                    document = Document(**metadata_dict)
                    documents.append(DocumentMetadata.from_document(document))
                    
                except (json.JSONDecodeError, ValidationError) as e:
                    logger.warning(f"Skipping invalid metadata file {metadata_file}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            raise DocumentStorageError(f"Failed to list documents: {e}") from e
        
        # Sort by upload time (newest first)
        documents.sort(key=lambda d: d.upload_time, reverse=True)
        return documents

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document and its metadata.
        
        Args:
            document_id: SHA-256 hash ID of the document
            
        Returns:
            bool: True if document was deleted, False if not found
            
        Raises:
            DocumentStorageError: If deletion operation fails
        """
        try:
            file_path = self._get_document_file_path(document_id)
            metadata_path = self._get_metadata_file_path(document_id)
            
            # Check if document exists
            if not await aiofiles.os.path.exists(metadata_path):
                return False
            
            # Delete file content if it exists
            if await aiofiles.os.path.exists(file_path):
                await aiofiles.os.remove(file_path)
            
            # Delete metadata
            await aiofiles.os.remove(metadata_path)
            
            logger.info(f"Deleted document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            raise DocumentStorageError(f"Failed to delete document: {e}") from e

    async def document_exists(self, document_id: str) -> bool:
        """Check if a document exists.
        
        Args:
            document_id: SHA-256 hash ID of the document
            
        Returns:
            bool: True if document exists, False otherwise
        """
        metadata_path = self._get_metadata_file_path(document_id)
        return await aiofiles.os.path.exists(metadata_path)

    async def get_storage_stats(self) -> dict:
        """Get storage statistics.
        
        Returns:
            dict: Storage statistics including count and total size
        """
        try:
            documents = await self.list_documents()
            total_size = sum(doc.size_bytes for doc in documents)
            
            return {
                "total_documents": len(documents),
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "storage_path": str(self.storage_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {
                "total_documents": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0.0,
                "storage_path": str(self.storage_path),
                "error": str(e)
            }


# Global service instance
_document_service: Optional[DocumentService] = None


def get_document_service() -> DocumentService:
    """Get the global document service instance.
    
    This function provides a singleton pattern for the document service
    and can be used for dependency injection in FastAPI.
    """
    global _document_service
    if _document_service is None:
        _document_service = DocumentService()
    return _document_service
