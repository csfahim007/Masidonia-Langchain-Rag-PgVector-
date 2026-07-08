import hashlib
import logging
from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import config
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_embedding_model() -> HuggingFaceEmbeddings:
    logger.info("Initializing LangChain HuggingFace embeddings: %s", config.EMBEDDING_MODEL)
    return HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def embed_documents(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return get_embedding_model().embed_documents(texts)


def embed_query(query: str) -> list[float]:
    normalized = query.strip().lower()
    cache_key = hashlib.sha256(normalized.encode()).hexdigest()
    cached = CacheService.get_embedding(cache_key)
    if cached:
        return cached
    vector = get_embedding_model().embed_query(query)
    CacheService.set_embedding(cache_key, vector)
    return vector
