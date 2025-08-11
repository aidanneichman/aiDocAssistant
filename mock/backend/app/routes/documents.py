"""Document routes for upload, list, get, and delete."""

from typing import List, Optional

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse

from backend.app.config import get_settings
from backend.app.models.api_responses import (
    DocumentDeleteResponse,
    DocumentListResponse,
    DocumentUploadResponse,
    UploadErrorItem,
)
from backend.app.models.document import Document, DocumentMetadata
from backend.app.services.document_service import (
    DocumentNotFoundError,
    DocumentService,
    DocumentStorageError,
    get_document_service,
)
from backend.app.utils.file_utils import (
    FileSizeExceededError,
    FileValidationError,
    SecurityValidationError,
    UnsupportedFileTypeError,
    detect_file_type,
    sanitize_filename,
    validate_file_security,
    validate_file_size,
    validate_file_type,
)


router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_documents(
    files: List[UploadFile] = File(..., description="One or more files to upload"),
    service: DocumentService = Depends(get_document_service),
):
    settings = get_settings()
    max_bytes = settings.get_upload_max_size_bytes()

    documents: List[DocumentMetadata] = []
    errors: List[UploadErrorItem] = []

    for upload in files:
        try:
            filename = sanitize_filename(upload.filename or "upload")
            raw_data = await upload.read()

            # Size validation
            validate_file_size(len(raw_data), settings.upload_max_size_mb)

            # Type detection and validation
            detected_type = detect_file_type(raw_data, filename)
            validate_file_type(detected_type, filename)

            # Security validation
            validate_file_security(raw_data, filename, detected_type)

            # Store
            doc = await service.store_document(
                file_data=raw_data, filename=filename, content_type=detected_type
            )
            documents.append(DocumentMetadata.model_validate(doc.model_dump()))

        except FileSizeExceededError as e:
            errors.append(
                UploadErrorItem(filename=upload.filename or "upload", code="FILE_TOO_LARGE", message=str(e))
            )
        except (UnsupportedFileTypeError, SecurityValidationError, FileValidationError) as e:
            errors.append(
                UploadErrorItem(filename=upload.filename or "upload", code="INVALID_FILE", message=str(e))
            )
        except DocumentStorageError as e:
            errors.append(
                UploadErrorItem(filename=upload.filename or "upload", code="STORAGE_ERROR", message=str(e))
            )
        except Exception as e:
            errors.append(
                UploadErrorItem(filename=upload.filename or "upload", code="UNKNOWN_ERROR", message=str(e))
            )

    return DocumentUploadResponse(documents=documents, errors=errors)


@router.get("", response_model=DocumentListResponse)
async def list_documents(service: DocumentService = Depends(get_document_service)):
    docs = await service.list_documents()
    return DocumentListResponse(documents=docs)


@router.get("/{doc_id}", response_model=DocumentMetadata)
async def get_document(doc_id: str, service: DocumentService = Depends(get_document_service)):
    doc = await service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentMetadata.model_validate(doc.model_dump())


@router.delete("/{doc_id}", response_model=DocumentDeleteResponse)
async def delete_document(doc_id: str, service: DocumentService = Depends(get_document_service)):
    try:
        deleted = await service.delete_document(doc_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return DocumentDeleteResponse(id=doc_id, success=True)
    except DocumentStorageError as e:
        raise HTTPException(status_code=500, detail=str(e))


