from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.models.dependencies import get_db, get_write_user, get_current_user
from app.core.database import User
from app.services.document_service import DocumentService
from app.services.search_service import SearchService

router = APIRouter(prefix="/documents", tags=["Documents"])


class DocumentResponse(BaseModel):
    id: str
    filename: str
    title: str | None
    content_type: str
    file_size: int
    status: str
    category: str | None
    tags: list[str]
    chunks_count: int
    version: int = 1
    folder_id: str | None = None
    uploaded_at: str


class DocumentPreviewResponse(BaseModel):
    document_id: str
    filename: str
    title: str | None
    category: str | None
    tags: list[str]
    version: int
    chunks_count: int
    word_count: int
    preview: str
    uploaded_at: str


class UpdateDocumentRequest(BaseModel):
    title: str | None = None
    tags: list[str] | None = None


def _serialize(doc) -> DocumentResponse:
    return DocumentResponse(
        id=str(doc.id),
        filename=doc.filename,
        title=doc.title,
        content_type=doc.content_type,
        file_size=doc.file_size,
        status=doc.status,
        category=doc.category,
        tags=doc.tags or [],
        chunks_count=doc.chunks_count,
        version=doc.version or 1,
        folder_id=str(doc.folder_id) if doc.folder_id else None,
        uploaded_at=doc.uploaded_at.isoformat() if doc.uploaded_at else "",
    )


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    folder_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    docs = DocumentService.list_documents(db, current_user, folder_id)
    return [_serialize(d) for d in docs]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = DocumentService.get_document(db, current_user, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _serialize(doc)


@router.get("/{document_id}/preview", response_model=DocumentPreviewResponse)
async def preview_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    preview = SearchService.get_document_preview(db, current_user, document_id)
    if not preview:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentPreviewResponse(**preview)


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    body: UpdateDocumentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_write_user),
):
    try:
        doc = DocumentService.update_document(db, current_user, document_id, body.title, body.tags)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _serialize(doc)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    folder_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_write_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    content = await file.read()
    try:
        document = DocumentService.process_upload(
            db, current_user, file.filename, content, folder_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Document processing failed")

    return {
        "message": "Document uploaded and processed successfully",
        "document_id": str(document.id),
        "filename": document.filename,
        "chunks_created": document.chunks_count,
        "category": document.category,
        "tags": document.tags,
    }


class BulkUploadItem(BaseModel):
    filename: str
    status: str
    document_id: str | None = None
    chunks_created: int | None = None
    category: str | None = None
    error: str | None = None


class BulkUploadResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    results: list[BulkUploadItem]


@router.post("/bulk-upload", response_model=BulkUploadResponse)
async def bulk_upload_documents(
    files: list[UploadFile] = File(...),
    folder_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_write_user),
):
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 files per batch")

    payload: list[tuple[str, bytes]] = []
    for file in files:
        if not file.filename:
            continue
        content = await file.read()
        payload.append((file.filename, content))

    results = DocumentService.process_bulk_upload(db, current_user, payload, folder_id)
    succeeded = sum(1 for r in results if r["status"] == "success")
    return BulkUploadResponse(
        total=len(results),
        succeeded=succeeded,
        failed=len(results) - succeeded,
        results=[BulkUploadItem(**r) for r in results],
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_write_user),
):
    if not DocumentService.delete_document(db, current_user, document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted"}
