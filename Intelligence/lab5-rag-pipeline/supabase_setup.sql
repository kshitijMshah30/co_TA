-- ============================================================
-- AI TA Intelligence — Supabase pgvector Setup
-- Run this in: Supabase Dashboard → SQL Editor → New Query
-- ============================================================

-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Documents table
CREATE TABLE IF NOT EXISTS documents (
    id          BIGSERIAL PRIMARY KEY,
    lab_id      TEXT NOT NULL,
    filename    TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. Chunks table (stores text + embeddings)
--    Using vector(384) for local sentence-transformers model.
--    Change to vector(1536) if using OpenAI text-embedding-3-small.
CREATE TABLE IF NOT EXISTS chunks (
    id           BIGSERIAL PRIMARY KEY,
    document_id  BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    lab_id       TEXT NOT NULL,
    chunk_index  INTEGER NOT NULL,
    page_start   INTEGER,
    page_end     INTEGER,
    section      TEXT,
    content      TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    embedding    vector(384),
    metadata     JSONB DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. Indexes
CREATE INDEX IF NOT EXISTS idx_chunks_lab_id ON chunks(lab_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_documents_lab_id ON documents(lab_id);

-- 5. HNSW index for fast cosine similarity search
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks
    USING hnsw (embedding vector_cosine_ops);

-- 6. Similarity search function (optional, for RPC calls)
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding vector(384),
    match_lab_id TEXT DEFAULT 'lab_5',
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id BIGINT,
    content TEXT,
    section TEXT,
    page_start INTEGER,
    page_end INTEGER,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.content,
        c.section,
        c.page_start,
        c.page_end,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM chunks c
    WHERE c.lab_id = match_lab_id
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
