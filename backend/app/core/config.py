import os
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse
from dotenv import load_dotenv

load_dotenv()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} environment variable is required")
    return value


def _normalize_database_url(url: str) -> str:
    """Normalize Neon URLs for psycopg2 (drop channel_binding, enforce sslmode)."""
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.pop("channel_binding", None)
    query.setdefault("sslmode", "require")
    return urlunparse(parsed._replace(query=urlencode(query)))


def _resolve_redis_url():
    """Resolve Redis URL from REDIS_URL or Redis Cloud host/port/password."""
    url = os.getenv("REDIS_URL")
    if url:
        return url

    host = os.getenv("REDIS_HOST")
    password = os.getenv("REDIS_PASSWORD")
    port = os.getenv("REDIS_PORT", "6379")
    username = os.getenv("REDIS_USERNAME", "default")

    if host and password:
        safe_password = quote(password, safe="")
        use_ssl = (
            os.getenv("REDIS_USE_SSL", os.getenv("REDIS_SSL", "false")).lower()
            in {"1", "true", "yes"}
        )
        scheme = "rediss" if use_ssl else "redis"
        return f"{scheme}://{username}:{safe_password}@{host}:{port}"

    return None


class Config:
    # Groq API
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    # Database (Neon)
    DATABASE_URL = _normalize_database_url(_require_env("DATABASE_URL"))

    # Redis Cloud
    REDIS_URL = _resolve_redis_url()
    REDIS_HOST = os.getenv("REDIS_HOST")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
    REDIS_USERNAME = os.getenv("REDIS_USERNAME", "default")
    REDIS_USE_SSL = (
        os.getenv("REDIS_USE_SSL", os.getenv("REDIS_SSL", "false")).lower()
        in {"1", "true", "yes"}
    )
    REDIS_CACHE_TTL_SECONDS = int(os.getenv("REDIS_CACHE_TTL_SECONDS", 3600))

    # JWT
    JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-key-change-in-production")
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 7

    # CORS (support common typo CORS_ORGIN)
    _cors_raw = os.getenv("CORS_ORIGINS") or os.getenv("CORS_ORGIN", "http://localhost:5173,http://localhost:3000")
    CORS_ORIGINS = [origin.strip() for origin in _cors_raw.split(",") if origin.strip()]

    # App Settings
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 800))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 100))
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", 1024))
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", 384))
    RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", 100))
    RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", 60))
    ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".markdown"}

    # Object storage (local | s3)
    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")
    S3_ENDPOINT = os.getenv("S3_ENDPOINT")  # MinIO: http://localhost:9000
    S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
    S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
    S3_BUCKET = os.getenv("S3_BUCKET", "masidonia-documents")
    S3_REGION = os.getenv("S3_REGION", "us-east-1")
    S3_USE_SSL = os.getenv("S3_USE_SSL", "false").lower() in {"1", "true", "yes"}

    # Task queue (sync fallback when Celery disabled)
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL") or REDIS_URL
    CELERY_ENABLED = os.getenv("CELERY_ENABLED", "false").lower() in {"1", "true", "yes"}

    # RAG / LangChain
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", 6))
    RAG_SCORE_THRESHOLD = float(os.getenv("RAG_SCORE_THRESHOLD", 0.35))
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.1))
    LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", 3))

    # Optional Elasticsearch
    ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL")
    ELASTICSEARCH_ENABLED = bool(ELASTICSEARCH_URL)


config = Config()
