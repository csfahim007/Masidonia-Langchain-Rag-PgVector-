"""Query helpers for retrieval — expand meta/instruction queries for better recall."""

_META_TERMS = frozenset({
    "summarize",
    "summary",
    "summarise",
    "overview",
    "describe",
    "explain",
    "outline",
    "review",
    "analyze",
    "analyse",
    "tell",
    "about",
    "what",
    "key",
    "points",
    "highlights",
})


def is_meta_query(query: str) -> bool:
    """True for short instructional queries like 'summarize' or 'tell me about this'."""
    normalized = query.strip().lower()
    if not normalized:
        return False
    words = normalized.split()
    if len(words) <= 4 and any(w.rstrip("?.!,") in _META_TERMS for w in words):
        return True
    if normalized in {"summarize", "summary", "overview", "summarise"}:
        return True
    return False


def expand_retrieval_query(query: str, document_id: str | None = None) -> str:
    """Expand short/meta queries so embeddings retrieve actual document content."""
    normalized = query.strip()
    if not normalized:
        return query

    if document_id and is_meta_query(normalized):
        return (
            f"{normalized} — extract and present the main topics, key facts, "
            "important details, and overall content from the selected document"
        )

    if document_id and len(normalized.split()) <= 3:
        return f"{normalized} in the document content"

    return normalized
