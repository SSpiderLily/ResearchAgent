from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class ParsedPaper:
    title: str = ""
    authors: str = ""
    abstract: str = ""
    full_text: str = ""
    pages: list[str] = field(default_factory=list)
    page_count: int = 0


def parse_pdf(file_path: str | Path) -> ParsedPaper:
    doc = fitz.open(str(file_path))
    pages: list[str] = []
    for page in doc:
        pages.append(page.get_text("text"))

    full_text = "\n".join(pages)
    title = _extract_title(doc)
    authors = _extract_authors(pages[0] if pages else "")
    abstract = _extract_abstract(full_text)

    doc.close()
    return ParsedPaper(
        title=title,
        authors=authors,
        abstract=abstract,
        full_text=full_text,
        pages=pages,
        page_count=len(pages),
    )


def _extract_title(doc: fitz.Document) -> str:
    """Heuristic: pick the largest-font text span on the first page."""
    if len(doc) == 0:
        return "Untitled"

    page = doc[0]
    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

    best_text = ""
    best_size = 0.0
    for block in blocks:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if span["size"] > best_size and span["text"].strip():
                    best_size = span["size"]
                    best_text = span["text"].strip()

    return best_text or "Untitled"


def _extract_authors(first_page_text: str) -> str:
    """Heuristic: lines between the title-ish area and the abstract."""
    lines = first_page_text.split("\n")
    candidates: list[str] = []
    for line in lines[1:10]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith("abstract"):
            break
        if re.search(r"[A-Z][a-z]+ [A-Z][a-z]+", stripped):
            candidates.append(stripped)
    return "; ".join(candidates[:5])


def _extract_abstract(full_text: str) -> str:
    """Heuristic: grab text between 'Abstract' header and the next section."""
    match = re.search(
        r"(?i)\babstract\b[:\s]*\n?(.*?)(?:\n\s*\n|\n\d+\.?\s+[A-Z]|\n[A-Z][a-z]+\n)",
        full_text,
        re.DOTALL,
    )
    if match:
        return match.group(1).strip()[:2000]
    return ""
