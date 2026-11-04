"""Upload embeddings/ (from embed_labs.py) into the Supabase `documents` and `chunks` tables.

Reads SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY from ./.env. The service-role key is
needed because the tables have RLS enabled with no policies.

Re-running is safe: a PDF whose lab_id + source_hash is already in `documents` is skipped.

Usage:
    .venv/bin/python upload_to_supabase.py
"""

import hashlib
import json
import os
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import requests

HERE = Path(__file__).resolve().parent
EMB_DIR = HERE / "embeddings"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 50


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def lab_id_for(filename: str) -> str:
    """Lab-10.pdf -> lab_10, matching the existing `lab_5` convention."""
    match = re.search(r"lab-?(\d+)", filename, re.IGNORECASE)
    if not match:
        raise ValueError(f"can't derive lab_id from {filename}")
    return f"lab_{int(match.group(1))}"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Rest:
    def __init__(self, url: str, key: str):
        self.base = url.rstrip("/") + "/rest/v1"
        self.session = requests.Session()
        self.session.headers.update({"apikey": key, "Authorization": f"Bearer {key}"})

    def get(self, table: str, params: dict) -> list:
        r = self.session.get(f"{self.base}/{table}", params=params, timeout=60)
        r.raise_for_status()
        return r.json()

    def insert(self, table: str, rows: list, returning: bool = False) -> list:
        headers = {"Prefer": "return=representation" if returning else "return=minimal"}
        r = self.session.post(f"{self.base}/{table}", json=rows, headers=headers, timeout=120)
        if not r.ok:
            raise RuntimeError(f"insert into {table} failed ({r.status_code}): {r.text}")
        return r.json() if returning else []

    def delete(self, table: str, params: dict) -> None:
        r = self.session.delete(f"{self.base}/{table}", params=params, timeout=60)
        r.raise_for_status()


def main() -> None:
    load_env(HERE / ".env")
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise SystemExit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in Labs/.env first.")
    db = Rest(url, key)

    embeddings = np.load(EMB_DIR / "embeddings.npy")
    records = [json.loads(line) for line in open(EMB_DIR / "chunks.jsonl")]
    assert len(records) == len(embeddings), "chunks.jsonl and embeddings.npy are out of sync"

    by_source = defaultdict(list)
    for record, vector in zip(records, embeddings):
        by_source[record["source"]].append((record, vector))

    for filename, items in by_source.items():
        lab_id = lab_id_for(filename)
        source_hash = sha256((HERE / filename).read_bytes())

        existing = db.get("documents", {"lab_id": f"eq.{lab_id}", "source_hash": f"eq.{source_hash}", "select": "id"})
        if existing:
            print(f"{filename}: already uploaded as document {existing[0]['id']}, skipping")
            continue

        doc = db.insert("documents", [{"lab_id": lab_id, "filename": filename, "source_hash": source_hash}], returning=True)[0]
        rows = [
            {
                "document_id": doc["id"],
                "lab_id": lab_id,
                "chunk_index": r["chunk_index"],
                "page_start": r["page_start"],
                "page_end": r["page_end"],
                "section": None,
                "content": r["text"],
                "content_hash": sha256(r["text"].encode()),
                "embedding": "[" + ",".join(f"{x:.8g}" for x in vector) + "]",
                "metadata": {"source": filename, "token_count": r["token_count"], "model": MODEL_NAME},
            }
            for r, vector in items
        ]
        try:
            for start in range(0, len(rows), BATCH_SIZE):
                db.insert("chunks", rows[start : start + BATCH_SIZE])
        except Exception:
            # Roll back this PDF so a re-run doesn't skip a half-uploaded document.
            db.delete("chunks", {"document_id": f"eq.{doc['id']}"})
            db.delete("documents", {"id": f"eq.{doc['id']}"})
            raise
        print(f"{filename}: document {doc['id']} ({lab_id}) + {len(rows)} chunks")


if __name__ == "__main__":
    main()
