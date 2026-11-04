# co_TA API Contract

**Status:** DRAFT v0.1, proposed by Intelligence. Needs sign-off from Human Interface and Inference before anyone builds against it as final.
**Implementation:** `Intelligence/rag/api.py` (runs today with `LLM_BACKEND=mock`).

This document is the handshake between the three subteams. If you need a change, open a PR against this file first and tag the other two subteams, then change the code.

```
 Human Interface ──HTTP──▶  Intelligence API  ──▶ Supabase (chunks, query_logs)
   (UI, sessions)          (RAG + guardrails)  ──▶ LLM server (Inference)
```

| Boundary | Owner (serves) | Consumer | Section |
|---|---|---|---|
| Ask a question | Intelligence | Human Interface | [1](#1-human-interface--intelligence) |
| Generate text | Inference | Intelligence | [2](#2-intelligence--inference) |
| Lab content and logs | Intelligence | Everyone (read) | [3](#3-shared-data-supabase) |

---

## 1. Human Interface → Intelligence

Base URL (local dev): `http://localhost:8000`. Version prefix: `/v1`. All bodies are JSON.

### `POST /v1/ask`

Send one student message, get one tutor reply.

**Request**

```json
{
  "lab_id": "lab_5",
  "message": "How do I pick R and C for prelab question 1?",
  "session_id": "b6f1c2e0-...",
  "history": [
    { "role": "user", "content": "What is a time constant?" },
    { "role": "assistant", "content": "It's how long the capacitor takes to ..." }
  ]
}
```

| Field | Type | Required | Rules |
|---|---|---|---|
| `lab_id` | string | yes | Matches `^lab_\d+$`, e.g. `lab_5`. Must be a lab that has been ingested. |
| `message` | string | yes | 1–2000 characters. |
| `session_id` | string | no | Opaque ID owned by Human Interface; echoed back. Will be used for the hint ladder (v0.2). |
| `history` | array | no | Previous turns, oldest first, max 20. `role` is `user` or `assistant`. Intelligence only uses the most recent 6. |

**Human Interface owns conversation state** in v0.1: send prior turns in `history`. Intelligence does not store transcripts beyond `query_logs`.

**Response `200`**

```json
{
  "request_id": "6f0e5c1a-...",
  "session_id": "b6f1c2e0-...",
  "reply": "Good question! Prelab 1 asks for over 99% charge in 5 s. How many time constants does it take to reach ~99%? (p. 3)",
  "sources": [
    { "chunk_id": 51, "page_start": 10, "page_end": 10, "section": "9", "type": "assessed_question", "similarity": 0.66 },
    { "chunk_id": 22, "page_start": 3, "page_end": 3, "section": "3", "type": "concept", "similarity": 0.48 }
  ],
  "flags": {
    "out_of_scope": false,
    "assessed_question_in_context": true,
    "escalate_to_ta": false,
    "emergency": false
  },
  "meta": { "llm_backend": "anthropic", "prompt_version": "tutor-v0.1", "latency_ms": 1840, "api_version": "0.1.0" }
}
```

| Field | Meaning | What the UI should do |
|---|---|---|
| `reply` | Markdown text for the student. | Render as markdown. |
| `sources[]` | Manual chunks used, best match first. `type` is `concept`, `procedure`, `safety`, `assessed_question`, or `null` (untagged lab). | Optional "from the manual, p. X" chips. Don't show raw chunk text for `assessed_question`. |
| `flags.out_of_scope` | Nothing in this lab's manual matched well enough. The reply says so; no LLM was called. | Show the "Ask a TA" / QueUp button prominently. |
| `flags.assessed_question_in_context` | The question touches graded pre-lab/in-lab work; the reply is guidance only. | Optional "Hint mode" badge. |
| `flags.escalate_to_ta` | A human should step in. True when out of scope or emergency. | Offer to add the student to the TA queue. |
| `flags.emergency` | Message mentioned fire, smoke, burns, shock, sparks, injury, etc. Reply tells the student to stop and get the TA. | Show it immediately and prominently; alert the TA if the session feature supports it. |
| `meta.*` | Debugging info. `request_id` matches the log row. | Include `request_id` in any "this answer was wrong" report. |

**Errors**

| Status | When | Body |
|---|---|---|
| `422` | Request failed validation (bad `lab_id`, empty message, ...) | FastAPI validation detail |
| `503` | Database, embedding model, or LLM unreachable | `{ "detail": "co_TA is unavailable: ..." }` |

The UI should show a friendly fallback ("co_TA is having trouble, please ask your TA") on any non-200.

### `GET /v1/health`

```json
{ "status": "ok", "api_version": "0.1.0", "embedding_model": "sentence-transformers/all-MiniLM-L6-v2", "llm_backend": "mock", "prompt_version": "tutor-v0.1" }
```

### Not in v0.1 (proposed for v0.2, needs discussion)

- **Streaming** (`POST /v1/ask/stream`, server-sent events) so long replies appear token by token.
- **Feedback** (`POST /v1/feedback` with `request_id`, `helpful: bool`, optional comment). This becomes eval data.
- **Course scoping.** Human Interface now supports multiple courses. Proposal: add `course_id` to the request and namespace labs as `{course_id}/lab_5`. Until then, `lab_id` assumes ECE 20007.
- **Auth.** The API currently trusts its caller. Before real students use it, it should sit behind the Human Interface backend (not called from the browser) with a shared service token.

---

## 2. Intelligence → Inference

Intelligence calls the LLM through one function (`Intelligence/rag/llm.py`), selected by environment variables. Inference can serve a model any way they like **as long as it speaks the OpenAI Chat Completions format**, which vLLM, Ollama, LM Studio, and TGI all support.

| Setting | Value |
|---|---|
| `LLM_BACKEND` | `openai_compatible` |
| `LLM_BASE_URL` | e.g. `http://<inference-host>:8001/v1` |
| `LLM_MODEL` | model name as the server reports it |

**What Intelligence sends:** `POST {LLM_BASE_URL}/chat/completions` with a `system` message (tutoring rules), up to 6 prior turns, and a final `user` message containing the retrieved manual excerpts and the question. `max_tokens: 600`. Non-streaming for v0.1.

**What Intelligence needs back:** `choices[0].message.content` as plain text.

**Requests to Inference:**
- Typical prompt size is about 1,500–3,000 tokens; please support at least an 8k context window.
- Target p95 latency under 5 s for a 300-token reply.
- Share the model name and version with every deployment so eval results can be tied to it.

Until Inference has a server up, Intelligence uses `LLM_BACKEND=anthropic` or `mock`.

---

## 3. Shared data (Supabase)

Owned by Intelligence. Others may read; **schema changes go through a migration and a PR**, never through the dashboard.

| Table / function | Purpose |
|---|---|
| `documents` | One row per ingested lab manual (`lab_id`, `filename`, `source_hash`). |
| `chunks` | Manual text chunks with 384-dim `embedding` (all-MiniLM-L6-v2), `lab_id`, pages, and `type`: `concept` · `procedure` · `safety` · `assessed_question` · `exclude`. |
| `match_chunks_v2(query_embedding, match_count, match_lab_id, min_similarity)` | Vector search. Skips `exclude` chunks. Returns `type`. |
| `query_logs` | One row per `/v1/ask` call: question, reply, retrieved chunk IDs, similarities, backend. **Contains student messages; treat as private.** |

The service-role key is used server-side only. It must never ship in frontend code.

---

## Roadmap (Intelligence)

| Version | Adds | Contract impact |
|---|---|---|
| v0.1 (now) | Retrieval, tutoring prompt, swappable LLM, emergency pre-check, logging | — |
| v0.2 | Leak judge (second-pass check that the reply doesn't give away graded answers), eval harness | None. Same response shape. |
| v0.3 | Intent classifier, hint ladder keyed on `session_id` | `session_id` becomes required |
| v0.4 | Streaming, feedback endpoint, `course_id` | New endpoints/fields (additive) |

## Change log

| Date | Version | Change |
|---|---|---|
| 2026-11-03 | 0.1-draft | Initial proposal. |
