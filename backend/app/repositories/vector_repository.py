import re
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import Document, DocumentChunk, User
from app.rag.embeddings import embed_query

RRF_K = 60
# Cosine similarity floor for vector-only search (not applied to RRF-ranked chat results)
VECTOR_SEARCH_MIN_SCORE = 0.15


def reciprocal_rank_fusion(
    vector_hits: list[dict],
    keyword_hits: list[dict],
    limit: int,
    score_threshold: float | None = None,
) -> list[dict]:
    """Merge vector and keyword results using Reciprocal Rank Fusion.

    When score_threshold is None (chat/hybrid default), return top-ranked hits
    without filtering — RRF scores are rank-based (~0.01) and must not be
    compared to cosine similarity thresholds.
    """
    rrf_scores: dict[str, float] = {}
    hit_map: dict[str, dict] = {}

    for rank, hit in enumerate(vector_hits):
        key = hit["chunk_id"]
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (RRF_K + rank + 1)
        hit_map[key] = hit

    for rank, hit in enumerate(keyword_hits):
        key = hit["chunk_id"]
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (RRF_K + rank + 1)
        hit = {**hit, "keyword_match": True}
        if key not in hit_map or hit.get("score", 0) > hit_map[key].get("score", 0):
            hit_map[key] = hit

    ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    results: list[dict] = []
    for chunk_id, rrf_score in ranked:
        hit = hit_map[chunk_id].copy()
        original_score = float(hit.get("score", 0.0))
        hit["score"] = max(original_score, rrf_score)

        if score_threshold is not None:
            is_keyword = hit.get("keyword_match") or original_score == 0.5
            if not is_keyword and original_score < score_threshold:
                continue

        results.append(hit)
        if len(results) >= limit:
            break

    return results


def _tokenize_query(query: str) -> list[str]:
    """Split query into terms for keyword matching (min 2 chars)."""
    return [t for t in re.findall(r"[a-zA-Z0-9]+", query.lower()) if len(t) >= 2]


class VectorRepository:
    """pgvector similarity and keyword search."""

    def __init__(self, db: Session):
        self.db = db

    def similarity_search(
        self,
        user: User,
        query: str,
        document_id: str | None = None,
        limit: int = 5,
        min_score: float | None = None,
    ) -> list[dict]:
        query_embedding = embed_query(query)
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        sql = """
            SELECT dc.id, dc.content, dc.chunk_index, d.filename, d.id as document_id,
                   1 - (dc.embedding <=> CAST(:embedding AS vector)) AS score
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE d.user_id = CAST(:user_id AS uuid) AND d.status = 'ready'
        """
        params: dict = {
            "embedding": embedding_str,
            "user_id": str(user.id),
            "limit": limit * 3 if min_score else limit,
        }

        if document_id:
            sql += " AND d.id = CAST(:document_id AS uuid)"
            params["document_id"] = document_id

        sql += " ORDER BY dc.embedding <=> CAST(:embedding AS vector) LIMIT :limit"

        rows = self.db.execute(text(sql), params).mappings().all()
        results = [self._row_to_result(row) for row in rows]

        if min_score is not None:
            results = [r for r in results if r["score"] >= min_score]

        return results[:limit]

    def keyword_search(
        self,
        user: User,
        query: str,
        document_id: str | None = None,
        limit: int = 5,
    ) -> list[dict]:
        terms = _tokenize_query(query)
        if not terms:
            return []

        q = (
            self.db.query(DocumentChunk, Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .filter(Document.user_id == user.id, Document.status == "ready")
        )
        for term in terms:
            q = q.filter(DocumentChunk.content.ilike(f"%{term}%"))

        if document_id:
            q = q.filter(Document.id == uuid.UUID(document_id))

        results = q.order_by(DocumentChunk.chunk_index).limit(limit).all()
        return [
            {
                "chunk_id": str(chunk.id),
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "filename": doc.filename,
                "document_id": str(doc.id),
                "score": 1.0,
                "keyword_match": True,
            }
            for chunk, doc in results
        ]

    def fetch_document_chunks(
        self,
        user: User,
        document_id: str,
        limit: int = 6,
    ) -> list[dict]:
        """Return representative chunks from a document (for meta-queries / fallback)."""
        total = (
            self.db.query(DocumentChunk)
            .join(Document, Document.id == DocumentChunk.document_id)
            .filter(
                Document.user_id == user.id,
                Document.id == uuid.UUID(document_id),
                Document.status == "ready",
            )
            .count()
        )
        if total == 0:
            return []

        # Spread samples across the document for summaries
        if total <= limit:
            offsets = list(range(total))
        else:
            step = max(1, total // limit)
            offsets = [min(i * step, total - 1) for i in range(limit)]

        hits: list[dict] = []
        for offset in offsets:
            row = (
                self.db.query(DocumentChunk, Document)
                .join(Document, Document.id == DocumentChunk.document_id)
                .filter(
                    Document.user_id == user.id,
                    Document.id == uuid.UUID(document_id),
                    Document.status == "ready",
                )
                .order_by(DocumentChunk.chunk_index)
                .offset(offset)
                .limit(1)
                .first()
            )
            if row:
                chunk, doc = row
                hits.append({
                    "chunk_id": str(chunk.id),
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index,
                    "filename": doc.filename,
                    "document_id": str(doc.id),
                    "score": 1.0,
                })
        return hits

    @staticmethod
    def _row_to_result(row) -> dict:
        return {
            "chunk_id": str(row["id"]),
            "content": row["content"],
            "chunk_index": row["chunk_index"],
            "filename": row["filename"],
            "document_id": str(row["document_id"]),
            "score": float(row["score"]),
        }

    def hybrid_search(
        self,
        user: User,
        query: str,
        document_id: str | None = None,
        limit: int = 5,
        score_threshold: float | None = None,
    ) -> list[dict]:
        """Combine vector similarity and keyword search via RRF."""
        vector_hits = self.similarity_search(user, query, document_id, limit)
        keyword_hits = self.keyword_search(user, query, document_id, limit)
        merged = reciprocal_rank_fusion(
            vector_hits, keyword_hits, limit, score_threshold
        )

        if not merged and document_id:
            merged = self.fetch_document_chunks(user, document_id, limit)

        return merged
