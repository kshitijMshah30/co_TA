"""HTTP API for the Human Interface team. Spec: API_CONTRACT.md at the repo root.

Run (from the Intelligence folder):
    uvicorn rag.api:app --reload --port 8000
"""

import os
from dataclasses import asdict
from functools import lru_cache
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import EMBEDDING_MODEL, Settings
from .pipeline import Pipeline
from .prompts import PROMPT_VERSION

API_VERSION = "0.1.0"

app = FastAPI(title="co_TA Intelligence API", version=API_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class AskRequest(BaseModel):
    lab_id: str = Field(pattern=r"^lab_\d+$", examples=["lab_5"])
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None
    history: list[Turn] = Field(default_factory=list, max_length=20)


@lru_cache(maxsize=1)
def get_pipeline() -> Pipeline:
    return Pipeline(Settings.from_env())


@app.get("/v1/health")
def health():
    s = Settings.from_env()
    return {
        "status": "ok",
        "api_version": API_VERSION,
        "embedding_model": EMBEDDING_MODEL,
        "llm_backend": s.llm_backend,
        "prompt_version": PROMPT_VERSION,
    }


@app.post("/v1/ask")
def ask(req: AskRequest):
    try:
        ans = get_pipeline().ask(req.lab_id, req.message, [t.model_dump() for t in req.history])
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"co_TA is unavailable: {exc}") from exc
    return {
        "request_id": ans.request_id,
        "session_id": req.session_id,
        "reply": ans.reply,
        "sources": [asdict(s) for s in ans.sources],
        "flags": {
            "out_of_scope": ans.out_of_scope,
            "assessed_question_in_context": ans.assessed_question_in_context,
            "escalate_to_ta": ans.escalate_to_ta,
            "emergency": ans.emergency,
        },
        "meta": {
            "llm_backend": ans.llm_backend,
            "prompt_version": ans.prompt_version,
            "latency_ms": ans.latency_ms,
            "api_version": API_VERSION,
        },
    }
