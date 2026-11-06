"""Builds the prompt sent to the LLM from retrieved chunks + the student question."""
from app.retriever import RetrievedChunk

SYSTEM_PROMPT = """You are a teaching assistant for ECE 2k7 (Lab 5: RC Circuits and Timing).
Answer ONLY using the manual excerpts provided below. Do not use outside knowledge.
When you use an excerpt, cite it by page, e.g. "(Lab 5 manual, p. 7)" or "(Lab 5 manual, p. 7-8)" \
if it spans pages. Use the section label only as a secondary hint, never as the citation itself.
If the excerpts do not contain the answer, say you don't know and suggest the student ask a TA. \
Do not guess or fill gaps with outside knowledge."""


def _format_page_citation(chunk: RetrievedChunk) -> str:
    if chunk.page_start is None:
        return "Lab 5 manual"
    if chunk.page_end and chunk.page_end != chunk.page_start:
        return f"Lab 5 manual, p. {chunk.page_start}-{chunk.page_end}"
    return f"Lab 5 manual, p. {chunk.page_start}"


def build_context_block(chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for chunk in chunks:
        citation = _format_page_citation(chunk)
        hint = f" [section hint: {chunk.section}]" if chunk.section else ""
        blocks.append(f"### Excerpt ({citation}){hint}\n{chunk.content}")
    return "\n\n".join(blocks)


def build_prompt(question: str, chunks: list[RetrievedChunk]) -> list[dict]:
    context_block = build_context_block(chunks)
    user_content = (
        f"Manual excerpts:\n\n{context_block}\n\n"
        f"Student question: {question}"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
