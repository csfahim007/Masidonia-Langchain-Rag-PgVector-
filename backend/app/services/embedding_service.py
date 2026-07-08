"""Embedding layer — delegates to LangChain HuggingFace embeddings."""

from app.rag.embeddings import embed_documents, embed_query, get_embedding_model

__all__ = ["embed_documents", "embed_query", "get_embedding_model"]
