"""Ties retrieval, prompting, and generation together."""
from dataclasses import dataclass

from app.config import settings
from app.llm import get_llm
from app.prompt import build_prompt
from app.query_log import log_query
from app.retriever import RetrievedChunk, retrieve

NOT_COVERED_MESSAGE = (
    "That doesn't appear to be covered in the Lab 5 manual. Please ask a TA."
)


@dataclass
class AskResult:
    answer: str
    sources: list[dict]
    scores: list[float]
    below_threshold: bool


def ask(question: str, lab: str | int = 5, k: int | None = None) -> AskResult:
    top_k = k or settings.retrieval_top_k
    chunks: list[RetrievedChunk] = retrieve(question, lab=lab, k=top_k)

    lab_id = lab if isinstance(lab, str) else f"lab_{lab}"
    below_threshold = not chunks or chunks[0].similarity < settings.min_similarity

    if below_threshold:
        answer = NOT_COVERED_MESSAGE
    else:
        messages = build_prompt(question, chunks)
        answer = get_llm().generate(messages)

    sources = [
        {
            "chunk_id": c.id,
            "document_id": c.document_id,
            "section": c.section,
            "page_start": c.page_start,
            "page_end": c.page_end,
            "metadata": c.metadata,
        }
        for c in chunks
    ]
    scores = [c.similarity for c in chunks]

    log_query(lab_id, question, answer, chunks, below_threshold)

    return AskResult(
        answer=answer, sources=sources, scores=scores, below_threshold=below_threshold
    )
