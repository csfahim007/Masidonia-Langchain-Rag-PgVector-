import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.database import Document, DocumentChunk, User


class DocumentRepository:
    """PostgreSQL access for documents and chunks."""

    def __init__(self, db: Session):
        self.db = db

    def list_by_user(self, user: User, folder_id: str | None = None) -> list[Document]:
        query = self.db.query(Document).filter(Document.user_id == user.id)
        if folder_id:
            query = query.filter(Document.folder_id == uuid.UUID(folder_id))
        return query.order_by(Document.uploaded_at.desc()).all()

    def get_by_id(self, user: User, document_id: str) -> Document | None:
        return (
            self.db.query(Document)
            .filter(Document.id == uuid.UUID(document_id), Document.user_id == user.id)
            .first()
        )

    def find_by_hash(self, user: User, file_hash: str) -> Document | None:
        return (
            self.db.query(Document)
            .filter(Document.user_id == user.id, Document.file_hash == file_hash)
            .first()
        )

    def create(self, document: Document) -> Document:
        self.db.add(document)
        self.db.flush()
        return document

    def add_chunks(self, document_id: uuid.UUID, chunks: list[tuple[str, list[float]]]) -> int:
        for idx, (content, embedding) in enumerate(chunks):
            self.db.add(
                DocumentChunk(
                    document_id=document_id,
                    chunk_index=idx,
                    content=content,
                    token_count=len(content.split()),
                    embedding=embedding,
                )
            )
        return len(chunks)

    def mark_ready(self, document: Document, chunks_count: int) -> Document:
        document.chunks_count = chunks_count
        document.status = "ready"
        document.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(document)
        return document

    def delete(self, document: Document) -> None:
        self.db.delete(document)
        self.db.commit()

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, document: Document) -> Document:
        self.db.refresh(document)
        return document
