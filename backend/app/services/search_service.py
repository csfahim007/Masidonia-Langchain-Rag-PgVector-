from sqlalchemy.orm import Session

from app.core.config import config
from app.core.database import Document, User
from app.repositories.vector_repository import (
    VECTOR_SEARCH_MIN_SCORE,
    VectorRepository,
)
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.repositories.search_repository import SearchRepository


class SearchService:
    """Hybrid search with optional LLM query enhancement and history tracking."""

    @staticmethod
    def _enhance_query(query: str, mode: str) -> str:
        if mode != "hybrid":
            return query
        # Only enhance natural-language queries (avoid LLM latency on short keyword searches)
        if len(query.split()) >= 4 or len(query) > 40:
            return LLMService.enhance_search_query(query)
        return query

    @staticmethod
    def search(
        db: Session,
        user: User,
        query: str,
        document_id: str | None = None,
        mode: str = "hybrid",
        limit: int = 10,
    ) -> list[dict]:
        search_query = SearchService._enhance_query(query, mode)
        repo = VectorRepository(db)

        if mode == "vector":
            results = repo.similarity_search(
                user,
                search_query,
                document_id,
                limit,
                min_score=VECTOR_SEARCH_MIN_SCORE,
            )
        elif mode == "keyword":
            results = repo.keyword_search(user, search_query, document_id, limit)
        else:
            results = repo.hybrid_search(
                user,
                search_query,
                document_id,
                limit,
                score_threshold=config.RAG_SCORE_THRESHOLD,
            )

        formatted = [
            {
                "chunk_id": r["chunk_id"],
                "document_id": r["document_id"],
                "filename": r["filename"],
                "snippet": r["content"][:300] + ("..." if len(r["content"]) > 300 else ""),
                "score": round(r["score"], 4),
                "chunk_index": r["chunk_index"],
            }
            for r in results
        ]

        SearchRepository(db).save_history(user, query, mode, len(formatted))
        return formatted

    @staticmethod
    def get_history(db: Session, user: User, limit: int = 20) -> list[dict]:
        entries = SearchRepository(db).list_history(user, limit)
        return [
            {
                "id": str(e.id),
                "query": e.query,
                "mode": e.mode,
                "results_count": e.results_count,
                "created_at": e.created_at.isoformat() if e.created_at else "",
            }
            for e in entries
        ]

    @staticmethod
    def clear_history(db: Session, user: User) -> int:
        return SearchRepository(db).clear_history(user)

    @staticmethod
    def get_document_preview(db: Session, user: User, document_id: str) -> dict | None:
        return SearchRepository(db).get_document_preview(user, document_id)

    @staticmethod
    def autocomplete(db: Session, user: User, prefix: str, limit: int = 5) -> list[str]:
        if len(prefix.strip()) < 2:
            return []
        rows = (
            db.query(Document.title)
            .filter(Document.user_id == user.id, Document.title.ilike(f"%{prefix}%"))
            .limit(limit)
            .all()
        )
        return [row.title for row in rows if row.title]

    @staticmethod
    def list_documents_filtered(
        db: Session,
        user: User,
        category: str | None = None,
        tag: str | None = None,
    ) -> list[Document]:
        q = db.query(Document).filter(Document.user_id == user.id)
        if category:
            q = q.filter(Document.category == category)
        if tag:
            q = q.filter(Document.tags.contains([tag]))
        return q.order_by(Document.uploaded_at.desc()).all()
