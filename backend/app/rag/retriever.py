from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.database import User
from app.rag.config import RAG_TOP_K
from app.rag.query_utils import expand_retrieval_query, is_meta_query
from app.repositories.vector_repository import VectorRepository, reciprocal_rank_fusion


class PgVectorHybridRetriever(BaseRetriever):
    """LangChain retriever backed by pgvector + keyword hybrid search with RRF."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    db: Session = Field(exclude=True)
    user: User = Field(exclude=True)
    document_id: str | None = None
    k: int = RAG_TOP_K

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        repo = VectorRepository(self.db)
        retrieval_query = expand_retrieval_query(query, self.document_id)

        # Meta-queries on a selected document: load representative chunks directly
        if self.document_id and is_meta_query(query):
            hits = repo.fetch_document_chunks(self.user, self.document_id, self.k)
            if hits:
                return [_hit_to_document(hit) for hit in hits]

        vector_hits = repo.similarity_search(
            self.user, retrieval_query, self.document_id, self.k
        )
        keyword_hits = repo.keyword_search(
            self.user, retrieval_query, self.document_id, self.k
        )
        # No score threshold for chat — RRF ranks top-k; threshold was blocking valid hits
        hits = reciprocal_rank_fusion(
            vector_hits, keyword_hits, self.k, score_threshold=None
        )

        # Fallback when scoped to a document but retrieval still empty
        if not hits and self.document_id:
            hits = repo.fetch_document_chunks(self.user, self.document_id, self.k)

        return [_hit_to_document(hit) for hit in hits]


def _hit_to_document(hit: dict[str, Any]) -> Document:
    return Document(
        page_content=hit["content"],
        metadata={
            "chunk_id": hit["chunk_id"],
            "document_id": hit["document_id"],
            "filename": hit["filename"],
            "chunk_index": hit["chunk_index"],
            "score": hit["score"],
        },
    )


def hits_from_documents(docs: list[Document]) -> list[dict]:
    return [
        {
            "chunk_id": d.metadata.get("chunk_id", ""),
            "content": d.page_content,
            "chunk_index": d.metadata.get("chunk_index", 0),
            "filename": d.metadata.get("filename", "unknown"),
            "document_id": d.metadata.get("document_id", ""),
            "score": float(d.metadata.get("score", 0)),
        }
        for d in docs
    ]


def format_source_citations(docs: list[Document]) -> list[str]:
    return [
        f"{d.metadata.get('filename', 'unknown')} "
        f"(chunk {int(d.metadata.get('chunk_index', 0)) + 1}, "
        f"score {float(d.metadata.get('score', 0)):.2f})"
        for d in docs
    ]
