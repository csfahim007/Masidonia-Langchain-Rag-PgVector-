from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field

from app.models.dependencies import get_db, get_write_user, get_current_user
from app.core.database import User
from app.services.folder_service import FolderService

router = APIRouter(prefix="/folders", tags=["Folders"])


class FolderResponse(BaseModel):
    id: str
    name: str
    parent_id: str | None
    document_count: int
    created_at: str


class CreateFolderRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    parent_id: Optional[str] = None


class RenameFolderRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)


class MoveDocumentRequest(BaseModel):
    folder_id: Optional[str] = None


def _serialize(folder, doc_counts: dict[str, int]) -> FolderResponse:
    return FolderResponse(
        id=str(folder.id),
        name=folder.name,
        parent_id=str(folder.parent_id) if folder.parent_id else None,
        document_count=doc_counts.get(str(folder.id), 0),
        created_at=folder.created_at.isoformat() if folder.created_at else "",
    )


@router.get("", response_model=list[FolderResponse])
async def list_folders(
    parent_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    folders = FolderService.list_folders(db, current_user, parent_id)
    counts = FolderService.folder_document_counts(db, current_user)
    return [_serialize(f, counts) for f in folders]


@router.post("", response_model=FolderResponse)
async def create_folder(
    body: CreateFolderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_write_user),
):
    try:
        folder = FolderService.create_folder(
            db, current_user, body.name, body.parent_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    counts = FolderService.folder_document_counts(db, current_user)
    return _serialize(folder, counts)


@router.patch("/{folder_id}", response_model=FolderResponse)
async def rename_folder(
    folder_id: str,
    body: RenameFolderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_write_user),
):
    try:
        folder = FolderService.rename_folder(db, current_user, folder_id, body.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    counts = FolderService.folder_document_counts(db, current_user)
    return _serialize(folder, counts)


@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_write_user),
):
    try:
        deleted = FolderService.delete_folder(db, current_user, folder_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not deleted:
        raise HTTPException(status_code=404, detail="Folder not found")
    return {"message": "Folder deleted"}


@router.patch("/documents/{document_id}/move")
async def move_document(
    document_id: str,
    body: MoveDocumentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_write_user),
):
    try:
        doc = FolderService.move_document(
            db, current_user, document_id, body.folder_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document moved", "document_id": str(doc.id)}
