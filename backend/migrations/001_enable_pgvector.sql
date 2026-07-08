-- Enable pgvector extension and indexes for Masidonia RAG pipeline.
-- Run against Neon PostgreSQL: psql $DATABASE_URL -f migrations/001_enable_pgvector.sql

CREATE EXTENSION IF NOT EXISTS vector;

-- Add vector column to document_chunks table (384-dim for all-MiniLM-L6-v2)
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding vector(384);

-- IVFFlat index for fast cosine similarity search
CREATE INDEX IF NOT EXISTS idx_chunk_embedding ON document_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Query performance indexes
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_folder_id ON documents(folder_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);
