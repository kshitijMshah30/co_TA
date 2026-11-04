"""Settings for the RAG service, read from environment variables (or Intelligence/.env)."""

import os
from dataclasses import dataclass
from pathlib import Path

INTELLIGENCE_DIR = Path(__file__).resolve().parent.parent

# Must match the model used by embed_folder.py / upload_to_supabase.py.
# Questions embedded with a different model silently retrieve the wrong chunks.
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


def load_env(path: Path = INTELLIGENCE_DIR / ".env") -> None:
    """Minimal .env loader (same behavior as upload_to_supabase.py). Real env vars win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_key: str  # service-role key: tables have RLS with no policies
    llm_backend: str  # mock | anthropic | openai_compatible
    llm_model: str | None
    llm_base_url: str | None
    match_count: int
    min_similarity: float
    max_history_turns: int
    log_queries: bool

    @classmethod
    def from_env(cls) -> "Settings":
        load_env()
        return cls(
            supabase_url=os.environ.get("SUPABASE_URL", ""),
            supabase_key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
            llm_backend=os.environ.get("LLM_BACKEND", "mock"),
            llm_model=os.environ.get("LLM_MODEL") or None,
            llm_base_url=os.environ.get("LLM_BASE_URL") or None,
            match_count=int(os.environ.get("RAG_MATCH_COUNT", "5")),
            # Starting guess. MiniLM cosine scores run low; tune this with the eval set.
            min_similarity=float(os.environ.get("RAG_MIN_SIMILARITY", "0.3")),
            max_history_turns=int(os.environ.get("RAG_MAX_HISTORY_TURNS", "6")),
            log_queries=os.environ.get("RAG_LOG_QUERIES", "true").lower() == "true",
        )
