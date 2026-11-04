"""Ingest Lab 5 manual into Supabase pgvector."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingest import ingest_lab
from src.config import PROJECT_ROOT


def main():
    pdf_path = PROJECT_ROOT / "data" / "lab5_manual.pdf"
    if not pdf_path.exists():
        print(f"ERROR: Lab 5 PDF not found at {pdf_path}")
        print("Place lab5_manual.pdf in the data/ directory.")
        sys.exit(1)

    summary = ingest_lab(pdf_path, lab_id="lab_5")
    print(f"\nSummary:")
    print(f"  File:       {summary['filename']}")
    print(f"  Pages:      {summary['pages']}")
    print(f"  Chunks:     {summary['chunks']}")
    print(f"  Embeddings: {summary['embeddings']} (dim={summary['dimension']})")
    print(f"  Model:      {summary['model']}")
    print(f"  Doc ID:     {summary['document_id']}")


if __name__ == "__main__":
    main()
