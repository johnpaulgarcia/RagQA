from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChunkMeta:
    document_id: str
    chunk_index: int
    page_number: int
    text: str
    char_start: int
    char_end: int


def _split_text(text: str, max_chars: int, overlap: int) -> list[tuple[int, int]]:
    """Return (start, end) char offsets for overlapping chunks."""
    spans: list[tuple[int, int]] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))

        # Try to break at paragraph, then sentence, then word boundary
        if end < len(text):
            for sep in ["\n\n", "\n", ". ", " "]:
                idx = text.rfind(sep, start, end)
                if idx > start:
                    end = idx + len(sep)
                    break

        spans.append((start, end))
        start = end - overlap if end < len(text) else len(text)

    return spans


def chunk_pages(
    pages: list[tuple[int, str]],
    document_id: str,
    chunk_size: int = 1500,
    chunk_overlap: int = 150,
) -> list[ChunkMeta]:
    """Split pages into overlapping chunks with metadata.

    Args:
        pages: list of (page_number, text) tuples.
        chunk_size: target chunk size in characters (~500 tokens at ~3 chars/token).
        chunk_overlap: overlap between chunks in characters.
    """
    chunks: list[ChunkMeta] = []
    idx = 0

    for page_number, text in pages:
        spans = _split_text(text, max_chars=chunk_size, overlap=chunk_overlap)
        for start, end in spans:
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(
                    ChunkMeta(
                        document_id=document_id,
                        chunk_index=idx,
                        page_number=page_number,
                        text=chunk_text,
                        char_start=start,
                        char_end=end,
                    )
                )
                idx += 1

    return chunks
