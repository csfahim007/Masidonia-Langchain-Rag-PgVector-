import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.database import DocumentChunk, SearchHistory, User


class SearchRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_history(
        self, user: User, query: str, mode: str, results_count: int
    ) -> SearchHistory:
        entry = SearchHistory(
            user_id=user.id,
            query=query.strip(),
            mode=mode,
            results_count=results_count,
            created_at=datetime.utcnow(),
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def list_history(self, user: User, limit: int = 20) -> list[SearchHistory]:
        return (
            self.db.query(SearchHistory)
            .filter(SearchHistory.user_id == user.id)
            .order_by(SearchHistory.created_at.desc())
            .limit(limit)
            .all()
        )

    def clear_history(self, user: User) -> int:
        count = (
            self.db.query(SearchHistory)
            .filter(SearchHistory.user_id == user.id)
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return count

    def get_document_preview(self, user: User, document_id: str, max_chars: int = 4000) -> dict | None:
        from app.repositories.document_repository import DocumentRepository

        doc = DocumentRepository(self.db).get_by_id(user, document_id)
        if not doc:
            return None

        chunks = (
            self.db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == doc.id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )
        full_text = "\n\n".join(c.content for c in chunks)
        preview = full_text[:max_chars] + ("..." if len(full_text) > max_chars else "")

        return {
            "document_id": str(doc.id),
            "filename": doc.filename,
            "title": doc.title,
            "category": doc.category,
            "tags": doc.tags or [],
            "version": doc.version,
            "chunks_count": doc.chunks_count,
            "word_count": doc.metadata_json.get("word_count", 0) if doc.metadata_json else 0,
            "preview": preview,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else "",
        }
