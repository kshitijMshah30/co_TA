"""Chunk and embed every PDF in this folder with sentence-transformers/all-MiniLM-L6-v2.

Usage:
    .venv/bin/python embed_labs.py                 # build embeddings
    .venv/bin/python embed_labs.py --query "..."   # search the saved embeddings

Outputs (in ./embeddings/):
    embeddings.npy  float32 array [n_chunks, 384], L2-normalized
    chunks.jsonl    one JSON object per row of embeddings.npy (source, pages, text, ...)
"""

import argparse
import json
import re
from pathlib import Path

import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "embeddings"

# all-MiniLM-L6-v2 truncates input at 256 word pieces, so keep chunks under that.
CHUNK_TOKENS = 200
OVERLAP_TOKENS = 40


def clean(text: str) -> str:
    # Drop control chars (e.g. \x00/\x01 from PDF equation brackets); Postgres text can't store \x00.
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # re-join words hyphenated across lines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    return text.strip()


def load_pdf(path: Path) -> tuple[str, list[int]]:
    """Return the document's full text and the char offset where each page starts."""
    parts, starts, pos = [], [], 0
    for page in PdfReader(path).pages:
        page_text = clean(page.extract_text() or "")
        starts.append(pos)
        parts.append(page_text)
        pos += len(page_text) + 1  # +1 for the joining newline
    return "\n".join(parts), starts


def page_of(char_idx: int, page_starts: list[int]) -> int:
    page = 0
    for i, start in enumerate(page_starts):
        if start <= char_idx:
            page = i
    return page + 1


def chunk_document(text: str, page_starts: list[int], tokenizer) -> list[dict]:
    enc = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True, verbose=False)
    offsets = enc["offset_mapping"]
    chunks, step = [], CHUNK_TOKENS - OVERLAP_TOKENS
    for start in range(0, len(offsets), step):
        window = offsets[start : start + CHUNK_TOKENS]
        char_start, char_end = window[0][0], window[-1][1]
        chunks.append(
            {
                "text": text[char_start:char_end],
                "page_start": page_of(char_start, page_starts),
                "page_end": page_of(char_end - 1, page_starts),
                "token_count": len(window),
            }
        )
        if start + CHUNK_TOKENS >= len(offsets):
            break
    return chunks


def build(model: SentenceTransformer) -> None:
    records = []
    for pdf in sorted(HERE.glob("*.pdf"), key=lambda p: p.name.lower()):
        text, page_starts = load_pdf(pdf)
        doc_chunks = chunk_document(text, page_starts, model.tokenizer)
        for i, c in enumerate(doc_chunks):
            records.append({"id": f"{pdf.stem}-{i:03d}", "source": pdf.name, "chunk_index": i, **c})
        print(f"{pdf.name}: {len(page_starts)} pages -> {len(doc_chunks)} chunks")

    embeddings = model.encode(
        [r["text"] for r in records],
        batch_size=64,
        normalize_embeddings=True,
        show_progress_bar=True,
        convert_to_numpy=True,
    ).astype(np.float32)

    OUT_DIR.mkdir(exist_ok=True)
    np.save(OUT_DIR / "embeddings.npy", embeddings)
    with open(OUT_DIR / "chunks.jsonl", "w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Saved {embeddings.shape[0]} embeddings of dim {embeddings.shape[1]} to {OUT_DIR}")


def search(model: SentenceTransformer, query: str, k: int) -> None:
    embeddings = np.load(OUT_DIR / "embeddings.npy")
    records = [json.loads(line) for line in open(OUT_DIR / "chunks.jsonl")]
    q = model.encode(query, normalize_embeddings=True)
    scores = embeddings @ q
    for idx in np.argsort(-scores)[:k]:
        r = records[idx]
        snippet = r["text"][:200].replace("\n", " ")
        print(f"{scores[idx]:.3f}  {r['source']} p{r['page_start']}-{r['page_end']}  {snippet}...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--query", help="search the saved embeddings instead of rebuilding them")
    parser.add_argument("-k", type=int, default=5, help="number of results for --query")
    args = parser.parse_args()

    model = SentenceTransformer(MODEL_NAME)
    if args.query:
        search(model, args.query, args.k)
    else:
        build(model)
