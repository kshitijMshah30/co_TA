"""Semantic retrieval from Supabase pgvector."""

import sys
import os

# Fix Windows console encoding
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.embeddings import EmbeddingProvider
from src.db import get_connection
from src.config import TOP_K


def retrieve(question: str, lab_id: str = "lab_5", top_k: int | None = None) -> list[dict]:
    """Retrieve the top-k most relevant chunks for a question.

    Uses cosine similarity via pgvector's <=> operator.
    """
    top_k = top_k or TOP_K
    embedder = EmbeddingProvider()
    query_embedding = embedder.embed_query(question)

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT
                 content, section, page_start, page_end,
                 1 - (embedding <=> %s::vector) AS similarity
               FROM chunks
               WHERE lab_id = %s
               ORDER BY embedding <=> %s::vector
               LIMIT %s""",
            (str(query_embedding), lab_id, str(query_embedding), top_k),
        )
        columns = [desc[0] for desc in cur.description]
        results = [dict(zip(columns, row)) for row in cur.fetchall()]
        return results
    finally:
        conn.close()


def print_results(question: str, results: list[dict]):
    """Pretty-print retrieval results."""
    print(f"\nQuery:\n  {question}\n")
    print(f"Top {len(results)} results:\n")
    for i, r in enumerate(results, 1):
        sim = r["similarity"]
        print(f"  {i}. [{r['section'][:60]}]")
        print(f"     Pages {r['page_start']}-{r['page_end']}  |  Similarity: {sim:.4f}")
        preview = r["content"][:150].replace("\n", " ")
        print(f"     {preview}...")
        print()


# CLI entry point
if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What is an RC time constant?"
    results = retrieve(question)
    print_results(question, results)
