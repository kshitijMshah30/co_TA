"""Configuration for the AI TA intelligence pipeline."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent

DATABASE_URL = os.getenv("DATABASE_URL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
TOP_K = int(os.getenv("TOP_K", "5"))

# Local embedding fallback
LOCAL_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
LOCAL_EMBEDDING_DIMENSION = 384

def get_embedding_config() -> tuple[str, int]:
    """Return (model_name, dimension) based on available API keys."""
    if OPENAI_API_KEY:
        return EMBEDDING_MODEL, EMBEDDING_DIMENSION
    return LOCAL_EMBEDDING_MODEL, LOCAL_EMBEDDING_DIMENSION
