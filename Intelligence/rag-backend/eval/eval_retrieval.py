"""Evaluates retrieval quality against eval/questions.json.

Reports hit rate and MRR at k=1/3/5/10, and the similarity distribution for
in-scope vs out-of-scope questions (to help choose MIN_SIMILARITY).

Run from the repo root: python eval/eval_retrieval.py
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.retriever import retrieve

QUESTIONS_PATH = Path(__file__).parent / "questions.json"
K_VALUES = [1, 3, 5, 10]
MAX_K = max(K_VALUES)


def load_questions():
    return json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))


def evaluate(lab_id: str = None, top_k: int = MAX_K):
    lab_id = lab_id or settings.default_lab_id
    questions = load_questions()
    in_scope_qs = [q for q in questions if q["in_scope"]]
    out_scope_qs = [q for q in questions if not q["in_scope"]]

    per_question = []
    for q in in_scope_qs:
        chunks = retrieve(q["question"], lab=lab_id, k=top_k, min_similarity=0.0)
        retrieved_ids = [c.id for c in chunks]
        expected = set(q["expected_chunk_ids"])

        rank = None
        for i, cid in enumerate(retrieved_ids, start=1):
            if cid in expected:
                rank = i
                break

        per_question.append(
            {
                "id": q["id"],
                "rank": rank,
                "top_similarity": chunks[0].similarity if chunks else None,
            }
        )

    out_scope_sims = []
    for q in out_scope_qs:
        chunks = retrieve(q["question"], lab=lab_id, k=1, min_similarity=0.0)
        out_scope_sims.append(chunks[0].similarity if chunks else 0.0)

    in_scope_sims = [pq["top_similarity"] for pq in per_question if pq["top_similarity"] is not None]

    print(f"=== Retrieval eval (lab={lab_id}, top_k={top_k}) ===")
    print(f"{len(in_scope_qs)} in-scope questions, {len(out_scope_qs)} out-of-scope questions\n")

    print("Hit rate / MRR by k:")
    for k in K_VALUES:
        hits = sum(1 for pq in per_question if pq["rank"] is not None and pq["rank"] <= k)
        hit_rate = hits / len(per_question)
        mrr = sum((1 / pq["rank"]) if pq["rank"] is not None and pq["rank"] <= k else 0 for pq in per_question) / len(per_question)
        print(f"  k={k:>2}: hit_rate={hit_rate:.3f}  mrr={mrr:.3f}")

    misses = [pq["id"] for pq in per_question if pq["rank"] is None or pq["rank"] > MAX_K]
    if misses:
        print(f"\nMissed (expected chunk not in top {MAX_K}): {misses}")

    print("\nSimilarity distribution:")
    if in_scope_sims:
        print(
            f"  in-scope  : mean={statistics.mean(in_scope_sims):.3f} "
            f"min={min(in_scope_sims):.3f} max={max(in_scope_sims):.3f}"
        )
    if out_scope_sims:
        print(
            f"  out-scope : mean={statistics.mean(out_scope_sims):.3f} "
            f"min={min(out_scope_sims):.3f} max={max(out_scope_sims):.3f}"
        )

    if in_scope_sims and out_scope_sims:
        suggested = (min(in_scope_sims) + max(out_scope_sims)) / 2
        print(
            f"\n  Current MIN_SIMILARITY={settings.min_similarity}. "
            f"Midpoint between in-scope min and out-scope max: {suggested:.3f}"
        )

    return per_question, in_scope_sims, out_scope_sims


if __name__ == "__main__":
    evaluate()
