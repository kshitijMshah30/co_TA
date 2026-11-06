import asyncio

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.pipeline import ask

app = FastAPI(title="LabTA RAG Backend")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    lab: str | int = settings.default_lab_id
    k: int | None = Field(default=None, ge=1, le=20)


class AskResponse(BaseModel):
    answer: str
    sources: list[dict]
    scores: list[float]
    below_threshold: bool


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
async def ask_endpoint(req: AskRequest):
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(ask, req.question, lab=req.lab, k=req.k),
            timeout=settings.api_request_timeout_seconds,
        )
    except asyncio.TimeoutError as e:
        raise HTTPException(status_code=504, detail="Request timed out") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return AskResponse(
        answer=result.answer,
        sources=result.sources,
        scores=result.scores,
        below_threshold=result.below_threshold,
    )
