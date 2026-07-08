from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import auth
from app.api import documents, chat, search, analytics, folders
from app.core.database import init_db
from app.core.config import config
from app.core.redis_client import connect_redis, disconnect_redis, is_redis_available
from app.middleware.rate_limit import RateLimitMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error("❌ Database initialization failed: %s", e)

    connect_redis()
    yield
    disconnect_redis()


app = FastAPI(
    title="Masidonia Intelligent Platform API",
    description="AI-powered document management, RAG chat, search, and analytics",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(folders.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "message": "Welcome to Masidonia Intelligent Platform",
        "docs": "/docs",
        "status": "running",
        "features": [
            "Document upload & processing (PDF, DOCX, TXT, MD)",
            "Bulk upload with per-file results",
            "Folder organization for documents",
            "AI chat with RAG, citations & streaming",
            "Hybrid search (vector + keyword)",
            "Analytics dashboard",
            "Redis caching & rate limiting",
            "JWT auth with RBAC roles",
        ],
    }


@app.get("/health")
async def health_check():
    from app.core.config import config as app_config

    return {
        "status": "healthy",
        "architecture": {
            "client": "React SPA",
            "gateway": "nginx (deploy/nginx) / Vite proxy (dev)",
            "application": "FastAPI monolith",
            "services": [
                "auth", "document", "langchain-rag", "embedding", "llm-groq",
                "search", "cache", "analytics", "task_queue",
            ],
            "data_layer": {
                "postgresql": "connected",
                "pgvector": "enabled",
                "redis": "connected" if is_redis_available() else "not configured",
                "object_storage": app_config.STORAGE_BACKEND,
                "elasticsearch": "enabled" if app_config.ELASTICSEARCH_ENABLED else "disabled",
                "celery": "enabled" if app_config.CELERY_ENABLED else "sync_executor",
            },
        },
        "database": "connected",
        "redis": "connected" if is_redis_available() else "not configured",
    }
