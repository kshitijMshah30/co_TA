"""Initialize the database schema in Supabase.

Run this script to create tables and indexes.
Alternatively, run supabase_setup.sql in the Supabase SQL Editor.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_connection


def init_db():
    """Create tables, indexes, and pgvector extension."""
    conn = get_connection()
    conn.autocommit = True
    cur = conn.cursor()

    print("Enabling pgvector extension...")
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

    print("Creating documents table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id          BIGSERIAL PRIMARY KEY,
            lab_id      TEXT NOT NULL,
            filename    TEXT NOT NULL,
            source_hash TEXT NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    print("Creating chunks table...")
    cur.execute("""
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
        )
    """)

    print("Creating indexes...")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_lab_id ON chunks(lab_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_documents_lab_id ON documents(lab_id)")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks
        USING hnsw (embedding vector_cosine_ops)
    """)

    print("Creating match_chunks function...")
    cur.execute("""
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
                c.id, c.content, c.section, c.page_start, c.page_end,
                1 - (c.embedding <=> query_embedding) AS similarity
            FROM chunks c
            WHERE c.lab_id = match_lab_id
            ORDER BY c.embedding <=> query_embedding
            LIMIT match_count;
        END;
        $$
    """)

    conn.close()
    print("Database initialized successfully.")


if __name__ == "__main__":
    init_db()
