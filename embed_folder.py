#!/usr/bin/env python3
"""Chunk selected lab PDFs and embed them with all-MiniLM-L6-v2."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent
OUT_PATH = ROOT / "embeddings.jsonl"
MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
# MiniLM-L6-v2 max sequence length is 256 tokens. Stay under it with overlap.
MAX_TOKENS = 220
OVERLAP_TOKENS = 40

PDF_PATHS = [
    ROOT / "Labs" / "Lab-1.pdf",
    ROOT / "Labs" / "Lab-2.pdf",
    ROOT / "Labs" / "Lab-3.pdf",
    ROOT / "Labs" / "Lab-6.pdf",
    ROOT / "Labs" / "Lab-7.pdf",
    ROOT / "Labs" / "lab-8.pdf",
    ROOT / "Labs" / "Lab-10.pdf",
]


def extract_pages(path: Path) -> list[tuple[int, str]]:
    reader = PdfReader(str(path))
    pages: list[tuple[int, str]] = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = " ".join(text.split())
        if text:
            pages.append((i, text))
    return pages


def chunk_tokens(text: str, tokenizer, max_tokens: int, overlap: int) -> list[str]:
    token_ids = tokenizer.encode(text, add_special_tokens=False)
    if not token_ids:
        return []
    if len(token_ids) <= max_tokens:
        return [text]

    chunks: list[str] = []
    start = 0
    step = max(1, max_tokens - overlap)
    while start < len(token_ids):
        end = min(len(token_ids), start + max_tokens)
        piece = tokenizer.decode(token_ids[start:end], skip_special_tokens=True).strip()
        if piece:
            chunks.append(piece)
        if end == len(token_ids):
            break
        start += step
    return chunks


def main() -> int:
    missing = [str(p) for p in PDF_PATHS if not p.exists()]
    if missing:
        print("Missing files:", *missing, sep="\n  ", file=sys.stderr)
        return 1

    print(f"Loading {MODEL_ID}...", flush=True)
    model = SentenceTransformer(MODEL_ID)
    tokenizer = model.tokenizer

    records: list[dict] = []
    for path in PDF_PATHS:
        pages = extract_pages(path)
        print(f"{path.name}: {len(pages)} text pages", flush=True)
        chunk_index = 0
        for page_num, page_text in pages:
            pieces = chunk_tokens(page_text, tokenizer, MAX_TOKENS, OVERLAP_TOKENS)
            for piece in pieces:
                chunk_index += 1
                records.append(
                    {
                        "id": f"{path.name}::page::{page_num}::chunk::{chunk_index}",
                        "source": path.name,
                        "path": str(path),
                        "kind": "pdf_text_chunk",
                        "page": page_num,
                        "chunk": chunk_index,
                        "text": piece,
                        "model": MODEL_ID,
                    }
                )

    if not records:
        print("No text extracted from the lab PDFs.", file=sys.stderr)
        return 1

    print(f"Embedding {len(records)} chunks...", flush=True)
    vectors = model.encode(
        [row["text"] for row in records],
        normalize_embeddings=True,
        show_progress_bar=True,
        convert_to_numpy=True,
    )

    with OUT_PATH.open("w") as f:
        for row, vector in zip(records, vectors):
            row["dimensions"] = int(vector.shape[0])
            row["embedding"] = vector.astype(float).tolist()
            f.write(json.dumps(row) + "\n")

    print(f"Wrote {len(records)} embeddings ({vectors.shape[1]}-d) to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
