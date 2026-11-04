"""PDF text extraction using PyMuPDF."""

import re
from pathlib import Path
import fitz  # PyMuPDF


def parse_pdf(pdf_path: str | Path) -> list[dict]:
    """Extract text from a PDF, page by page.

    Returns a list of {"page": int, "text": str} dicts.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(str(pdf_path))
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        raw_text = page.get_text("text")
        cleaned = _clean_text(raw_text)
        if cleaned.strip():
            pages.append({"page": page_num + 1, "text": cleaned})

    doc.close()
    return pages


def _clean_text(text: str) -> str:
    """Clean extraction noise from raw PDF text."""
    # Remove NUL characters
    text = text.replace("\x00", "")
    # Collapse excessive whitespace (but keep single newlines for paragraphs)
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse 3+ consecutive newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove leading/trailing whitespace per line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    return text.strip()
