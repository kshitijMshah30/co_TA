"""Ingestion pipeline: parse PDF → chunk → embed → store in Supabase Postgres."""

import hashlib
from pathlib import Path

from src.parser import parse_pdf
from src.chunking import chunk_pages
from src.embeddings import EmbeddingProvider
from src.db import get_connection


def compute_file_hash(path: Path) -> str:
    """SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            h.update(block)
    return h.hexdigest()


def ingest_lab(pdf_path: str | Path, lab_id: str = "lab_5") -> dict:
    """Run the full ingestion pipeline for a lab manual.

    Returns a summary dict with counts.
    """
    pdf_path = Path(pdf_path)
    print(f"Loading: {pdf_path.name}")

    source_hash = compute_file_hash(pdf_path)

    # 1. Parse PDF
    pages = parse_pdf(pdf_path)
    print(f"Pages parsed: {len(pages)}")

    # 2. Chunk
    chunks = chunk_pages(pages, lab_id=lab_id)
    print(f"Chunks created: {len(chunks)}")

    # 3. Create embeddings
    embedder = EmbeddingProvider()
    texts = [c["content"] for c in chunks]
    embeddings = embedder.embed_documents(texts)
    print(f"Embeddings created: {len(embeddings)} (dim={embedder.dimension})")

    # 4. Store in Postgres
    conn = get_connection()
    try:
        cur = conn.cursor()

        # Delete existing data for this lab (idempotent re-ingestion)
        cur.execute("DELETE FROM chunks WHERE lab_id = %s", (lab_id,))
        cur.execute("DELETE FROM documents WHERE lab_id = %s", (lab_id,))

        # Insert document row
        cur.execute(
            """INSERT INTO documents (lab_id, filename, source_hash)
               VALUES (%s, %s, %s) RETURNING id""",
            (lab_id, pdf_path.name, source_hash),
        )
        doc_id = cur.fetchone()[0]

        # Insert chunks with embeddings
        for chunk, embedding in zip(chunks, embeddings):
            content_hash = hashlib.sha256(chunk["content"].encode()).hexdigest()
            cur.execute(
                """INSERT INTO chunks
                   (document_id, lab_id, chunk_index, page_start, page_end,
                    section, content, content_hash, embedding, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s)""",
                (
                    doc_id,
                    chunk["lab_id"],
                    chunk["chunk_index"],
                    chunk["page_start"],
                    chunk["page_end"],
                    chunk["section"],
                    chunk["content"],
                    content_hash,
                    str(embedding),
                    '{"source": "' + pdf_path.name + '"}',
                ),
            )

        conn.commit()
        print(f"Rows inserted: {len(chunks)}")
        print(f"Lab {lab_id} ingestion complete.")

        return {
            "filename": pdf_path.name,
            "pages": len(pages),
            "chunks": len(chunks),
            "embeddings": len(embeddings),
            "dimension": embedder.dimension,
            "model": embedder.model_name,
            "document_id": doc_id,
        }

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
