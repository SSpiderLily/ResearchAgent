from __future__ import annotations

from dataclasses import dataclass

from config import CHUNK_OVERLAP, CHUNK_SIZE


@dataclass
class Chunk:
    text: str
    paper_id: str
    page: int
    index: int  # chunk index within the paper


def chunk_pages(
    pages: list[str],
    paper_id: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[Chunk]:
    """Split page texts into overlapping character-level chunks.

    Each chunk records which page it originates from.
    """
    chunks: list[Chunk] = []
    idx = 0

    for page_num, page_text in enumerate(pages):
        page_text = page_text.strip()
        if not page_text:
            continue

        start = 0
        while start < len(page_text):
            end = start + chunk_size
            text = page_text[start:end].strip()
            if text:
                chunks.append(
                    Chunk(text=text, paper_id=paper_id, page=page_num + 1, index=idx)
                )
                idx += 1
            start += chunk_size - overlap

    return chunks
