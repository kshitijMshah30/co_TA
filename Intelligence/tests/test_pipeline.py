"""Offline tests: no Supabase, no model download, no LLM API. Run from Intelligence/:

    python -m pytest tests -q
"""

from fastapi.testclient import TestClient

from rag import api
from rag.config import Settings
from rag.pipeline import Pipeline
from rag.prompts import EMERGENCY_REPLY, OUT_OF_SCOPE_REPLY
from rag.retrieval import Chunk

SETTINGS = Settings(
    supabase_url="", supabase_key="", llm_backend="mock", llm_model=None, llm_base_url=None,
    match_count=5, min_similarity=0.3, max_history_turns=6, log_queries=False,
)

CONCEPT = Chunk(10, "tau = R*C. After one time constant the capacitor reaches 63.2%.", "4.3", 3, 3, "concept", 0.71)
PRELAB = Chunk(40, "1. Choose R and C so the RC circuit fully charges in 5 seconds.", "9", 10, 10, "assessed_question", 0.66)


class RecordingLLM:
    name = "fake"

    def __init__(self):
        self.calls = []

    def generate(self, system, messages):
        self.calls.append((system, messages))
        return "  Think about what tau means.  "


def make(chunks, llm=None, logs=None):
    return Pipeline(
        SETTINGS,
        llm=llm or RecordingLLM(),
        embed_fn=lambda q: [0.0] * 384,
        retrieve_fn=lambda vec, lab, n, m: chunks,
        log_fn=(logs.append if logs is not None else None),
    )


def test_answers_with_sources_and_strips_reply():
    ans = make([CONCEPT]).ask("lab_5", "What is the time constant?")
    assert ans.reply == "Think about what tau means."
    assert [s.chunk_id for s in ans.sources] == [10]
    assert not ans.out_of_scope and not ans.assessed_question_in_context


def test_graded_chunks_are_labeled_guide_only_in_prompt():
    llm = RecordingLLM()
    ans = make([CONCEPT, PRELAB], llm=llm).ask("lab_5", "what R and C should I use for prelab 1")
    system, messages = llm.calls[0]
    assert ans.assessed_question_in_context
    assert "GRADED QUESTION - guide only" in messages[-1]["content"]
    assert "NEVER give the final value" in system


def test_no_chunks_means_out_of_scope_without_calling_llm():
    llm = RecordingLLM()
    ans = make([], llm=llm).ask("lab_5", "How big is the Great Barrier Reef?")
    assert ans.reply == OUT_OF_SCOPE_REPLY
    assert ans.out_of_scope and ans.escalate_to_ta
    assert llm.calls == []


def test_emergency_skips_retrieval_and_llm():
    llm = RecordingLLM()
    pipe = make([CONCEPT], llm=llm)
    pipe.retrieve_fn = lambda *a: (_ for _ in ()).throw(AssertionError("should not retrieve"))
    ans = pipe.ask("lab_5", "my resistor is smoking what do i do")
    assert ans.reply == EMERGENCY_REPLY and ans.emergency and ans.escalate_to_ta
    assert llm.calls == []


def test_history_is_trimmed_and_passed_through():
    llm = RecordingLLM()
    history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"t{i}"} for i in range(10)]
    make([CONCEPT], llm=llm).ask("lab_5", "and step 4?", history)
    messages = llm.calls[0][1]
    assert [m["content"] for m in messages[:-1]] == [f"t{i}" for i in range(4, 10)]


def test_logs_row_matches_query_logs_columns():
    logs = []
    make([CONCEPT], logs=logs).ask("lab_5", "What is tau?")
    assert set(logs[0]) == {"lab_id", "question", "answer", "retrieved_chunk_ids",
                            "similarities", "below_threshold", "llm_backend"}
    assert logs[0]["retrieved_chunk_ids"] == [10]


def test_logging_failure_does_not_break_answer():
    pipe = make([CONCEPT])
    pipe.log_fn = lambda row: (_ for _ in ()).throw(RuntimeError("db down"))
    assert pipe.ask("lab_5", "What is tau?").reply


def test_api_contract_shape():
    api.get_pipeline.cache_clear()
    api.app.dependency_overrides = {}
    original = api.get_pipeline
    api.get_pipeline = lambda: make([CONCEPT, PRELAB])
    try:
        client = TestClient(api.app)
        r = client.post("/v1/ask", json={"lab_id": "lab_5", "message": "help with prelab 1", "session_id": "s1"})
        assert r.status_code == 200
        body = r.json()
        assert set(body) == {"request_id", "session_id", "reply", "sources", "flags", "meta"}
        assert body["flags"]["assessed_question_in_context"] is True
        assert set(body["sources"][0]) == {"chunk_id", "page_start", "page_end", "section", "type", "similarity"}
        assert client.post("/v1/ask", json={"lab_id": "five", "message": "x"}).status_code == 422
        assert client.post("/v1/ask", json={"lab_id": "lab_5", "message": ""}).status_code == 422
    finally:
        api.get_pipeline = original
