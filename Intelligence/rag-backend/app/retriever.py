"""Retrieval over the chunks table via the match_chunks_v2 RPC."""
from dataclasses import dataclass
from functools import lru_cache

from supabase import Client, create_client

from app.config import settings
from app.embedder import get_embedder


@dataclass
class RetrievedChunk:
    id: int
    document_id: int
    content: str
    section: str | None
    page_start: int | None
    page_end: int | None
    metadata: dict
    similarity: float


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_key)


def retrieve(
    question: str,
    lab: str | int = 5,
    k: int = 5,
    min_similarity: float | None = None,
) -> list[RetrievedChunk]:
    """Embed `question` and return the top-k most similar chunks for the given lab."""
    lab_id = lab if isinstance(lab, str) else f"lab_{lab}"
    threshold = settings.min_similarity if min_similarity is None else min_similarity

    query_embedding = get_embedder().embed(question)

    resp = get_supabase().rpc(
        "match_chunks_v2",
        {
            "query_embedding": query_embedding,
            "match_count": k,
            "match_lab_id": lab_id,
            "min_similarity": threshold,
        },
    ).execute()

    return [
        RetrievedChunk(
            id=row["id"],
            document_id=row["document_id"],
            content=row["content"],
            section=row.get("section"),
            page_start=row.get("page_start"),
            page_end=row.get("page_end"),
            metadata=row.get("metadata") or {},
            similarity=row["similarity"],
        )
        for row in resp.data
    ]
