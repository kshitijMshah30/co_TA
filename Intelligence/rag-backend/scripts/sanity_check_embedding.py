"""Confirms EMBEDDING_MODEL matches what produced the stored embeddings:
re-embeds 3 stored chunks' content and compares cosine similarity against
the stored vector. Expect ~0.99+ if it's the right model."""
import os

import httpx
import numpy as np
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
MODEL_NAME = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
}


def cosine_sim(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def parse_vector(s: str) -> list[float]:
    return [float(x) for x in s.strip("[]").split(",")]


def fetch_sample_chunks(n=3):
    url = f"{SUPABASE_URL}/rest/v1/chunks"
    resp = httpx.get(
        url,
        headers=HEADERS,
        params={"select": "id,content,embedding", "limit": str(n), "order": "id.asc"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    from sentence_transformers import SentenceTransformer

    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME, device="cpu")

    chunks = fetch_sample_chunks(3)
    print(f"\nSanity-checking {len(chunks)} stored chunks against {MODEL_NAME}\n")

    results = []
    for chunk in chunks:
        stored_vec = parse_vector(chunk["embedding"])
        recomputed_vec = model.encode(chunk["content"], normalize_embeddings=False).tolist()
        sim = cosine_sim(stored_vec, recomputed_vec)
        results.append((chunk["id"], sim))
        print(f"chunk id={chunk['id']}: cosine similarity = {sim:.5f}")

    low = [r for r in results if r[1] < 0.98]
    if low:
        print(f"\nWARNING: {len(low)} chunk(s) scored below 0.98 — model may not match. {low}")
    else:
        print("\nAll 3 chunks scored >=0.98 — model confirmed.")


if __name__ == "__main__":
    main()
