"""Heading-aware, token-limited text chunking."""

import re
import tiktoken


# Heading patterns for the lab manual
_HEADING_RE = re.compile(
    r"^(\d+(?:\.\d+)*)\s+(.+)$", re.MULTILINE
)

TARGET_CHUNK_TOKENS = 600
MAX_CHUNK_TOKENS = 800
OVERLAP_TOKENS = 100

_enc = tiktoken.get_encoding("cl100k_base")


def _token_count(text: str) -> int:
    return len(_enc.encode(text))


def _split_into_sections(text: str) -> list[dict]:
    """Split text into sections based on numbered headings."""
    matches = list(_HEADING_RE.finditer(text))

    if not matches:
        return [{"heading": "Content", "text": text}]

    sections = []
    for i, match in enumerate(matches):
        heading = match.group(0).strip()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections.append({"heading": heading, "text": body})

    # Capture any text before the first heading
    if matches and matches[0].start() > 0:
        preamble = text[: matches[0].start()].strip()
        if preamble:
            sections.insert(0, {"heading": "Introduction", "text": preamble})

    return sections


def _split_long_text(text: str, heading: str) -> list[str]:
    """Split text that exceeds MAX_CHUNK_TOKENS into smaller pieces with overlap."""
    tokens = _enc.encode(text)
    if len(tokens) <= MAX_CHUNK_TOKENS:
        return [text]

    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + TARGET_CHUNK_TOKENS, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = _enc.decode(chunk_tokens)

        # Try to break at sentence boundary
        last_period = chunk_text.rfind(". ")
        if last_period > len(chunk_text) // 3:
            chunk_text = chunk_text[: last_period + 1]
            # Recalculate end based on actual text used
            end = start + len(_enc.encode(chunk_text))

        chunks.append(chunk_text.strip())

        # Move forward with overlap
        start = max(end - OVERLAP_TOKENS, start + 1)

    return chunks


def chunk_pages(pages: list[dict], lab_id: str = "lab_5") -> list[dict]:
    """Chunk parsed PDF pages into retrieval-sized pieces with metadata.

    Args:
        pages: list of {"page": int, "text": str}
        lab_id: identifier for the lab

    Returns:
        list of chunk dicts with metadata
    """
    # Combine all page text, tracking page boundaries
    full_text = ""
    page_offsets = []  # (start_offset, page_num)
    for p in pages:
        page_offsets.append((len(full_text), p["page"]))
        full_text += p["text"] + "\n\n"

    def _find_page(offset: int) -> int:
        """Find which page an offset belongs to."""
        page = 1
        for start, pnum in page_offsets:
            if offset >= start:
                page = pnum
        return page

    sections = _split_into_sections(full_text)
    chunks = []
    chunk_index = 0

    for section in sections:
        heading = section["heading"]
        text = section["text"]
        section_start = full_text.find(text)

        sub_chunks = _split_long_text(text, heading)

        for sub in sub_chunks:
            sub_start = full_text.find(sub, max(0, section_start - 10))
            if sub_start == -1:
                sub_start = section_start

            page_start = _find_page(sub_start)
            page_end = _find_page(sub_start + len(sub))

            chunks.append({
                "lab_id": lab_id,
                "chunk_index": chunk_index,
                "section": heading.split("\n")[0][:200],
                "page_start": page_start,
                "page_end": page_end,
                "content": sub.strip(),
            })
            chunk_index += 1

    return chunks
