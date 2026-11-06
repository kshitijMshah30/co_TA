"""Writes each /ask request to the query_logs table (see sql/002_query_logs.sql).
Logging failures never break the request — they're swallowed and reported via logger."""
import logging

from app.config import settings
from app.retriever import RetrievedChunk, get_supabase

logger = logging.getLogger("labta_rag.query_log")


def log_query(
    lab_id: str,
    question: str,
    answer: str,
    chunks: list[RetrievedChunk],
    below_threshold: bool,
) -> None:
    try:
        get_supabase().table("query_logs").insert(
            {
                "lab_id": lab_id,
                "question": question,
                "answer": answer,
                "retrieved_chunk_ids": [c.id for c in chunks],
                "similarities": [c.similarity for c in chunks],
                "below_threshold": below_threshold,
                "llm_backend": settings.llm_backend,
            }
        ).execute()
    except Exception:
        logger.exception("Failed to write query log")
