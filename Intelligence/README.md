# Intelligence

Vector database, RAG pipeline, prompting, guardrails, and evals for co_TA.
The API we expose to Human Interface and Inference is specified in [`../API_CONTRACT.md`](../API_CONTRACT.md).

## How it fits together

```
OFFLINE (once per lab manual)                ONLINE (every student question)            rag/
  PDF ─▶ embed_folder.py ─▶ upload_to_supabase.py    6. embed question (MiniLM)          retrieval.py
        chunk + embed        documents / chunks       7. match_chunks_v2 (Supabase)       retrieval.py
                                    │                 8. tutoring prompt + excerpts      prompts.py
                                    ▼                 9. LLM (mock / Claude / Inference)  llm.py
                         Supabase (pgvector)  ◀────  10. log to query_logs                pipeline.py
```

Every chunk in `chunks` has a `type` that tells the pipeline how to treat it:

| `type` | Bot behavior |
|---|---|
| `concept`, `procedure` | Explain directly |
| `safety` | Always state plainly |
| `assessed_question` | Graded pre-lab/in-lab work. Hint only, never the answer |
| `exclude` | Parser junk (e.g. figure axis labels). Never retrieved |

Only **lab 5** is tagged so far. Untagged labs still work, but the bot can't tell which chunks are graded.

## Setup

```bash
cd Intelligence
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY
```

The first run downloads all-MiniLM-L6-v2 (~90 MB).

## Use it

```bash
# Ask from the terminal (mock LLM by default: shows what would be sent to the model)
python -m rag.cli --show-sources "What does the time constant mean?"

# Use a real model
LLM_BACKEND=anthropic ANTHROPIC_API_KEY=... python -m rag.cli "How do I set the trigger?"

# Run the API for Human Interface
uvicorn rag.api:app --reload --port 8000     # docs at http://localhost:8000/docs

# Offline tests (no database, model, or API key needed)
python -m pytest tests -q
```

To use the Inference team's server, set `LLM_BACKEND=openai_compatible`, `LLM_BASE_URL`, and `LLM_MODEL` (see API_CONTRACT.md §2).

## Known limitations of v0.1

- **The prompt is the only answer-leak protection.** A determined student can still talk the model into giving answers. The leak judge (v0.2) closes this.
- **`RAG_MIN_SIMILARITY=0.3` is untuned.** Too high and real questions get "not in the manual"; too low and off-topic questions get answered from weak matches. Tune it with the eval set.
- **The emergency check is a keyword list** (fire, smoke, burn, shock, spark, injury, ...). It errs toward escalating, so "will this resistor burn out?" also triggers it.
- **Section labels are unreliable** because the PDF parser treats stray numbers as headings. Don't depend on `section`.
- **Re-ingesting:** `upload_to_supabase.py` skips a manual whose file hash is already uploaded, so tags survive re-runs. If a manual PDF changes, its chunks are re-inserted untagged and need tagging again.

## Next up

1. Lab 5 eval set: ~40 cases (direct questions, attempts to get graded answers, jailbreaks).
2. Leak judge in `pipeline.py` between steps 9 and 10.
3. Tag the remaining labs.
