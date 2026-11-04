"""Steps 6 and 7: embed the student's question and fetch the closest manual chunks."""

from dataclasses import dataclass
from functools import lru_cache

import requests

from .config import EMBEDDING_DIM, EMBEDDING_MODEL


@dataclass
class Chunk:
    id: int
    content: str
    section: str | None
    page_start: int | None
    page_end: int | None
    type: str | None  # concept | procedure | safety | assessed_question (exclude never comes back)
    similarity: float


# ---------- Step 6: embed the question ----------

@lru_cache(maxsize=1)
def _model():
    # Imported lazily so tests and the mock path don't need torch installed.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL)


def embed_question(question: str) -> list[float]:
    # normalize_embeddings=True to match how the chunks were embedded in embed_folder.py.
    vector = _model().encode(question, normalize_embeddings=True)
    assert len(vector) == EMBEDDING_DIM, f"expected {EMBEDDING_DIM} dims, got {len(vector)}"
    return vector.tolist()


# ---------- Step 7: retrieve ----------

class SupabaseClient:
    """Thin PostgREST client, same approach as upload_to_supabase.py (no extra SDK)."""

    def __init__(self, url: str, key: str):
        if not url or not key:
            raise RuntimeError("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in Intelligence/.env")
        self.base = url.rstrip("/") + "/rest/v1"
        self.session = requests.Session()
        self.session.headers.update({"apikey": key, "Authorization": f"Bearer {key}"})

    def rpc(self, fn: str, params: dict) -> list[dict]:
        r = self.session.post(f"{self.base}/rpc/{fn}", json=params, timeout=30)
        if not r.ok:
            raise RuntimeError(f"rpc {fn} failed ({r.status_code}): {r.text}")
        return r.json()

    def insert(self, table: str, row: dict) -> None:
        r = self.session.post(
            f"{self.base}/{table}", json=row, headers={"Prefer": "return=minimal"}, timeout=30
        )
        if not r.ok:
            raise RuntimeError(f"insert into {table} failed ({r.status_code}): {r.text}")


def retrieve(db: SupabaseClient, query_vector: list[float], lab_id: str,
             match_count: int, min_similarity: float) -> list[Chunk]:
    # match_chunks_v2 filters by lab, drops chunks tagged `exclude`, and applies the cutoff.
    rows = db.rpc(
        "match_chunks_v2",
        {
            "query_embedding": "[" + ",".join(f"{x:.8g}" for x in query_vector) + "]",
            "match_count": match_count,
            "match_lab_id": lab_id,
            "min_similarity": min_similarity,
        },
    )
    return [
        Chunk(
            id=r["id"], content=r["content"], section=r.get("section"),
            page_start=r.get("page_start"), page_end=r.get("page_end"),
            type=r.get("type"), similarity=float(r["similarity"]),
        )
        for r in rows
    ]
