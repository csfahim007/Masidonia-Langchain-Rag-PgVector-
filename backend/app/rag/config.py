"""RAG pipeline configuration — mirrors env vars from app.core.config."""

from app.core.config import config

CHUNK_SIZE = config.CHUNK_SIZE
CHUNK_OVERLAP = config.CHUNK_OVERLAP
RAG_TOP_K = config.RAG_TOP_K
RAG_SCORE_THRESHOLD = config.RAG_SCORE_THRESHOLD
EMBEDDING_MODEL = config.EMBEDDING_MODEL
EMBEDDING_DIM = config.EMBEDDING_DIM
