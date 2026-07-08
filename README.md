# Masidonia Intelligent Platform

AI-powered document intelligence platform with RAG chat, hybrid search, folder organization, and analytics. Users upload PDF, DOCX, TXT, and Markdown files; the system chunks content, generates embeddings, stores vectors in PostgreSQL (pgvector), and answers questions via Groq LLM with source citations.

## Features

- Document upload (single + bulk) with PDF/DOCX/TXT/MD parsing
- Folder-based document organization
- RAG-powered AI chat with citations and SSE streaming
- Hybrid search (pgvector cosine similarity + keyword ILIKE + RRF fusion)
- Analytics dashboard and admin platform metrics
- JWT authentication with refresh token rotation and Redis blacklist
- Redis caching (responses, embeddings) and rate limiting
- Role-based access control (admin / user / viewer)

## Technology Stack

| Layer | Technologies |
|-------|-------------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Zustand, Axios |
| Backend | Python 3.14, FastAPI, SQLAlchemy 2.0, Pydantic v2 |
| RAG | LangChain 1.x, langchain-groq, langchain-huggingface, pgvector |
| LLM | Groq API (llama-3.1-8b-instant) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2, 384-dim) |
| Database | Neon PostgreSQL + pgvector |
| Cache | Redis Cloud (SSL) |
| Storage | Local filesystem or S3/MinIO |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  React SPA (Vite dev / nginx prod)                          │
│  Pages: Login, Documents, Chat, Search, Analytics           │
└───────────────────────────┬─────────────────────────────────┘
                            │ /api → FastAPI :8000
┌───────────────────────────▼─────────────────────────────────┐
│  FastAPI Application                                        │
│  Middleware: CORS, Redis rate limiting                      │
│  Routes: auth, documents, folders, chat, search, analytics  │
│  Services: Document, RAG, Search, Auth, Cache, Analytics    │
│  RAG: RAGOrchestrator → PgVectorHybridRetriever → Groq      │
│  Repositories: Document, Vector, Conversation, Search       │
└───────────┬─────────────────────┬───────────────────────────┘
            │                     │
   ┌────────▼────────┐   ┌───────▼────────┐
   │ Neon PostgreSQL │   │  Redis Cloud   │
   │ + pgvector      │   │  cache, auth,  │
   │                 │   │  rate limits   │
   └─────────────────┘   └────────────────┘
```

## Project Structure

```
Masidonia/
├── backend/
│   ├── app/
│   │   ├── api/           # REST route handlers
│   │   ├── rag/           # LangChain RAG pipeline
│   │   ├── repositories/  # Data access layer
│   │   ├── services/      # Business logic
│   │   ├── core/          # config, database, redis
│   │   └── middleware/    # Rate limiting
│   ├── migrations/        # SQL migrations (pgvector)
│   ├── test_*.py          # Verification scripts
│   └── pyproject.toml
├── frontend/
│   └── src/
│       ├── pages/         # UI pages
│       ├── services/api.ts
│       └── types/
├── deploy/nginx/          # Production nginx config
└── docker-compose.yml
```

## Setup

### Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Node.js 18+
- Neon PostgreSQL database
- Redis Cloud instance
- Groq API key

### Backend

```bash
cd backend
cp .env.example .env
# Edit .env with DATABASE_URL, GROQ_API_KEY, Redis credentials, JWT_SECRET

uv sync
# Or: pip install -e .

# Enable pgvector (if not auto-created on startup)
psql "$DATABASE_URL" -f migrations/001_enable_pgvector.sql

uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — Vite proxies `/api` to the backend.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Neon PostgreSQL connection string | required |
| `GROQ_API_KEY` | Groq API key | required |
| `GROQ_MODEL` | LLM model name | llama-3.1-8b-instant |
| `REDIS_URL` | Redis Cloud URL (use `rediss://` for SSL) | optional |
| `REDIS_USE_SSL` / `REDIS_SSL` | Enable TLS for Redis | true |
| `JWT_SECRET` | JWT signing secret | change in production |
| `CORS_ORIGINS` | Allowed frontend origins | localhost:5173,3000 |
| `CHUNK_SIZE` | Text chunk size | 800 |
| `CHUNK_OVERLAP` | Chunk overlap | 100 |
| `RAG_TOP_K` | Retrieval top-k | 6 |
| `RAG_SCORE_THRESHOLD` | Minimum relevance score | 0.35 |
| `EMBEDDING_MODEL` | Sentence-transformers model | all-MiniLM-L6-v2 |
| `EMBEDDING_DIM` | Embedding dimensions | 384 |
| `STORAGE_BACKEND` | `local` or `s3` | local |

See `backend/.env.example` for the full list.

## Verification Scripts

Run from the `backend/` directory:

```bash
uv run python test_redis.py       # Redis Cloud connection
uv run python test_database.py    # PostgreSQL + pgvector
uv run python test_embeddings.py  # HuggingFace embeddings
uv run python test_auth.py        # JWT auth flow
uv run python test_rag.py         # RAG retriever (add --invoke for LLM)
```

## API Overview

| Prefix | Endpoints |
|--------|-----------|
| `/api/auth` | register, login, refresh, logout, me |
| `/api/documents` | list, upload, bulk-upload, preview, patch, delete |
| `/api/folders` | CRUD + move document |
| `/api/chat` | sync chat, SSE stream, conversations |
| `/api/search` | hybrid/vector/keyword search, history |
| `/api/analytics` | overview, trends, topics, platform (admin) |

Full reference: `backend/plan3.txt` or `/docs` (Swagger UI).

## Deployment

Docker Compose and nginx configs are prepared under `deploy/` and `docker-compose.yml`. For production:

1. Set all secrets in environment (never commit `.env`)
2. Run pgvector migration against Neon
3. Use `rediss://` for Redis Cloud with SSL enabled
4. Build frontend (`npm run build`) and serve via nginx
5. Run backend with uvicorn/gunicorn behind nginx

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run verification scripts before submitting changes
4. Open a pull request with a clear description

## License

Private project — all rights reserved.
