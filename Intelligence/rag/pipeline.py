"""The full question -> answer loop. Steps 6-10 of the RAG architecture.

    6. embed question  ->  7. retrieve chunks  ->  8. build prompt  ->  9. generate  ->  10. log

Not built yet (see API_CONTRACT.md "Roadmap"): intent classifier, leak judge, hint ladder.
"""

import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable

from . import prompts
from .config import Settings
from .llm import LLM, make_llm
from .retrieval import Chunk, SupabaseClient, embed_question, retrieve

# Cheap pre-check so an emergency never waits on (or gets filtered by) the LLM.
_EMERGENCY = re.compile(
    r"\b(fire|smoke|smoking|burn(ed|t|ing)?|shock(ed)?|electrocut\w*|spark(ing|s)?|"
    r"explod\w*|bleeding|injur\w*)\b",
    re.IGNORECASE,
)


@dataclass
class Source:
    chunk_id: int
    page_start: int | None
    page_end: int | None
    section: str | None
    type: str | None
    similarity: float


@dataclass
class Answer:
    request_id: str
    reply: str
    sources: list[Source] = field(default_factory=list)
    out_of_scope: bool = False
    assessed_question_in_context: bool = False
    escalate_to_ta: bool = False
    emergency: bool = False
    llm_backend: str = ""
    prompt_version: str = prompts.PROMPT_VERSION
    latency_ms: int = 0


class Pipeline:
    def __init__(
        self,
        settings: Settings,
        llm: LLM | None = None,
        embed_fn: Callable[[str], list[float]] = embed_question,
        retrieve_fn: Callable[..., list[Chunk]] | None = None,
        log_fn: Callable[[dict], None] | None = None,
    ):
        self.settings = settings
        self.llm = llm or make_llm(settings)
        self.embed_fn = embed_fn
        if retrieve_fn is None or (log_fn is None and settings.log_queries):
            db = SupabaseClient(settings.supabase_url, settings.supabase_key)
            retrieve_fn = retrieve_fn or (lambda vec, lab_id, n, m: retrieve(db, vec, lab_id, n, m))
            if log_fn is None and settings.log_queries:
                log_fn = lambda row: db.insert("query_logs", row)
        self.retrieve_fn = retrieve_fn
        self.log_fn = log_fn

    def ask(self, lab_id: str, message: str, history: list[dict] | None = None) -> Answer:
        start = time.perf_counter()
        answer = Answer(request_id=str(uuid.uuid4()), reply="", llm_backend=self.llm.name)

        if _EMERGENCY.search(message):
            answer.reply = prompts.EMERGENCY_REPLY
            answer.emergency = answer.escalate_to_ta = True
            return self._finish(answer, lab_id, message, [], start)

        # Steps 6 + 7
        chunks = self.retrieve_fn(
            self.embed_fn(message), lab_id, self.settings.match_count, self.settings.min_similarity
        )
        answer.sources = [
            Source(c.id, c.page_start, c.page_end, c.section, c.type, round(c.similarity, 4))
            for c in chunks
        ]

        if not chunks:
            answer.reply = prompts.OUT_OF_SCOPE_REPLY
            answer.out_of_scope = answer.escalate_to_ta = True
            return self._finish(answer, lab_id, message, chunks, start)

        answer.assessed_question_in_context = any(c.type == "assessed_question" for c in chunks)

        # Step 8: prior turns as plain text; only the newest message carries the excerpts.
        turns = (history or [])[-self.settings.max_history_turns:]
        messages = [{"role": t["role"], "content": t["content"]} for t in turns]
        messages.append({"role": "user", "content": prompts.build_user_message(message, chunks)})

        # Step 9
        answer.reply = self.llm.generate(prompts.TUTOR_RULES, messages).strip()
        return self._finish(answer, lab_id, message, chunks, start)

    # Step 10
    def _finish(self, answer: Answer, lab_id: str, message: str,
                chunks: list[Chunk], start: float) -> Answer:
        answer.latency_ms = int((time.perf_counter() - start) * 1000)
        if self.log_fn:
            try:
                self.log_fn({
                    "lab_id": lab_id,
                    "question": message,
                    "answer": answer.reply,
                    "retrieved_chunk_ids": [c.id for c in chunks],
                    "similarities": [c.similarity for c in chunks],
                    "below_threshold": answer.out_of_scope,
                    "llm_backend": answer.llm_backend,
                })
            except Exception as exc:  # logging must never break a student's answer
                print(f"[co_TA] query log failed: {exc}")
        return answer
