# LabTA RAG Backend

RAG backend for the ECE 2k7 Lab 5 (RC Circuits and Timing) teaching assistant.
Retrieves manual excerpts from Supabase (Postgres + pgvector) and generates an
answer through a swappable LLM backend.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in:

| Variable | Meaning |
|---|---|
| `SUPABASE_URL` | Project URL |
| `SUPABASE_SERVICE_KEY` | Service or anon key. Never commit this. |
| `EMBEDDING_MODEL` | Must match the model used to embed stored chunks (`sentence-transformers/all-MiniLM-L6-v2`, 384-dim) |
| `EMBEDDING_DEVICE` | `cpu` or `cuda` |
| `DEFAULT_LAB_ID` | e.g. `lab_5` |
| `RETRIEVAL_TOP_K` | default k for retrieval |
| `MIN_SIMILARITY` | below this top-1 similarity, the pipeline returns the "not covered" response instead of calling the LLM |
| `LLM_BACKEND` | `mock` or `openai_compatible` |
| `LLM_API_BASE`, `LLM_API_KEY`, `LLM_MODEL` | used only when `LLM_BACKEND=openai_compatible` |

## Database migrations

SQL in `sql/` is **not applied automatically**. Run each file manually in the
Supabase SQL editor (or `psql`) after reviewing it:

- `sql/001_match_chunks_v2.sql` — adds a new RPC `match_chunks_v2` with a
  `min_similarity` cutoff and extra return columns. Does **not** touch the
  existing `match_chunks` function other teammates may depend on.
- `sql/002_query_logs.sql` — creates the `query_logs` table used to log every
  `/ask` request (question, retrieved chunk ids, similarity scores, answer).

**RLS note:** `query_logs` has Row Level Security enabled. The backend writes
to it (`app/query_log.py`) using `SUPABASE_SERVICE_KEY`, which bypasses RLS —
this is required for logging to work. If that key is ever swapped for an
anon/publishable key, inserts will start failing silently (logging failures
are caught and logged, not raised) unless a policy is added to allow it.

## Running the API

```bash
uvicorn app.main:app --reload
```

- `GET /health` — liveness check.
- `POST /ask` — body `{"question": "...", "lab": "lab_5", "k": 5}` (lab and k optional)
  returns `{"answer", "sources", "scores", "below_threshold"}`.

With `LLM_BACKEND=mock` (the default), `/ask` returns the retrieved context
instead of a real generated answer — this is what all development and eval
should use until the GPU backend is reachable again.

## Running the eval

```bash
python eval/eval_retrieval.py
```

Reports hit rate and MRR at k=1/3/5/10, plus the similarity distribution for
in-scope vs. out-of-scope questions (used to sanity-check `MIN_SIMILARITY`).

### Results (46 chunks, lab_5, all-MiniLM-L6-v2)

| k | hit rate | MRR |
|---|---|---|
| 1 | 0.625 | 0.625 |
| 3 | 0.969 | 0.781 |
| 5 | 1.000 | 0.789 |
| 10 | 1.000 | 0.789 |

Retrieval is solid from k=5 onward (every in-scope question's expected chunk
shows up); k=1 alone misses the expected chunk ~38% of the time because
several questions are answerable from more than one chunk and the "expected"
label only names one. `RETRIEVAL_TOP_K=5` (the default) is a good balance of
recall vs. prompt size.

**Threshold tuning:** swept `MIN_SIMILARITY` over the 37 eval questions
(top-1 similarity only):

| threshold | in-scope wrongly rejected | out-of-scope wrongly accepted |
|---|---|---|
| 0.30 | 0/32 | 2/5 |
| 0.35 | 1/32 | 2/5 |
| 0.37 | 2/32 | 1/5 |
| 0.40 | 3/32 | 0/5 |

There's a genuinely overlapping band (~0.34–0.40) where some in-scope and
some out-of-scope questions land — no single cutoff separates them cleanly
on this small question set. Raising the default from 0.3 to **0.4** trades 3
extra "ask a TA" responses (out of 32 in-scope questions) for zero confident
answers to out-of-scope questions, which is the right tradeoff for a TA bot:
an overly cautious "I don't know" is much cheaper than a hallucinated answer
to an off-topic question.

Chunking itself wasn't varied — the chunks are already embedded in Supabase
by an upstream process, and re-chunking would mean re-embedding and rewriting
`chunks`, which needs explicit sign-off (see Rules in the project brief).
With only 46 chunks for one lab, k and the similarity threshold were the
only knobs worth tuning at this stage.

## Smoke test (once the GPU backend is back)

```bash
python scripts/smoke_test.py
```

Hits `/health` and `/ask` with `LLM_BACKEND=openai_compatible` pointed at the
real server, and checks that a real (non-mock) answer comes back with
citations.

## Swapping in the real LLM

1. Set `LLM_BACKEND=openai_compatible` in `.env`.
2. Set `LLM_API_BASE` to the GPU server's (or Purdue GenAI Studio's)
   OpenAI-compatible base URL, `LLM_API_KEY` if required, and `LLM_MODEL` to
   the model name it serves.
3. Nothing else changes — retrieval, prompting, and logging are identical.
   `app/llm.py` is the only file that knows about the backend; add a new
   `LLM` subclass there if a future backend isn't OpenAI-compatible.

## Project layout

```
app/
  config.py      settings from env (no hardcoded secrets/table names)
  embedder.py    query embedding, swappable backend (local model or API)
  retriever.py   calls the match_chunks_v2 RPC, returns RetrievedChunk list
  prompt.py      builds system + context + question messages, page citations
  llm.py         MockLLM / OpenAICompatibleLLM
  pipeline.py    retrieve -> threshold check -> prompt -> generate -> log
  query_log.py   writes each request to query_logs
  main.py        FastAPI app: /health, /ask
sql/             migrations, reviewed and run manually
eval/            questions.json + eval_retrieval.py
scripts/         inspect_schema.py, smoke_test.py
```
