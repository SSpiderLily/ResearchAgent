from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF

# 常见非标题页眉（单行且全为大写时弱化）
_SKIP_HEADER_LINE = re.compile(
    r"^(arxiv|doi:|https?://|preprint|proceedings|ieee|acm|springer|elsevier|vol\.|pp\.|"
    r"copyright|page\s+\d|第\s*\d+\s*页|under review|anonymous)",
    re.I,
)


@dataclass
class ParsedPaper:
    title: str = ""
    authors: str = ""
    abstract: str = ""
    full_text: str = ""
    pages: list[str] = field(default_factory=list)
    page_count: int = 0
    year: int | None = None
    content_preview: str = ""


def build_content_preview(abstract: str, full_text: str, max_len: int = 2000) -> str:
    """无摘要时用正文开头作为展示用预览；有摘要则留空（由上层用 abstract 展示）。"""
    if abstract.strip():
        return ""
    body = re.sub(r"\s+", " ", full_text).strip()
    return body[:max_len] if body else ""


def extract_year(full_text: str) -> int | None:
    """从首页附近文本启发式提取发表年份（可能失败）。"""
    head = full_text[:8000]

    m = re.search(r"arxiv[:\s]*(\d{4})\.\d{4,5}v?\d*", head, re.I)
    if m:
        yy = int(m.group(1)[:2])
        if yy >= 90:
            y = 1900 + yy
        else:
            y = 2000 + yy
        if 1990 <= y <= 2035:
            return y

    m = re.search(r"\((19\d{2}|20\d{2})\)", head)
    if m:
        y = int(m.group(1))
        if 1990 <= y <= 2035:
            return y

    for m in re.finditer(r"\b(19\d{2}|20\d{2})\b", head):
        y = int(m.group(1))
        if 1990 <= y <= 2035:
            return y
    return None


def parse_pdf(
    file_path: str | Path,
    upload_filename_stem: str | None = None,
) -> ParsedPaper:
    doc = fitz.open(str(file_path))
    pages: list[str] = []
    for page in doc:
        pages.append(page.get_text("text"))

    full_text = "\n".join(pages)
    # 用用户上传时的文件名（非磁盘上的 UUID 存盘名）判断是否与正文「假标题」重合
    stem_for_compare = (
        upload_filename_stem if upload_filename_stem is not None else Path(file_path).stem
    )
    title = _extract_title(doc, pages[0] if pages else "", source_stem=stem_for_compare)
    authors = _extract_authors(pages[0] if pages else "")
    abstract = _extract_abstract(full_text)
    year = extract_year(full_text)
    preview = build_content_preview(abstract, full_text)

    doc.close()
    return ParsedPaper(
        title=title,
        authors=authors,
        abstract=abstract,
        full_text=full_text,
        pages=pages,
        page_count=len(pages),
        year=year,
        content_preview=preview,
    )


def _norm_for_compare(s: str) -> str:
    return re.sub(r"[\s_.\-]+", " ", s.lower()).strip()


def _stem_matches_title(source_stem: str, title: str) -> bool:
    """上传文件名（无扩展名）与标题过近时，视为不可靠（多为 PDF 内嵌文件名）。"""
    if not source_stem or not title:
        return False
    a, b = _norm_for_compare(source_stem), _norm_for_compare(title)
    if len(a) < 3:
        return False
    return a == b or (a in b and len(a) >= 8)


def _title_from_first_page_text(first_page_text: str) -> str:
    """从首页纯文本前几行取标题：跳过链接、期刊名行等。"""
    lines = [ln.strip() for ln in first_page_text.split("\n") if ln.strip()]
    collected: list[str] = []
    for line in lines[:18]:
        if _SKIP_HEADER_LINE.match(line):
            continue
        low = line.lower()
        if low in ("abstract", "introduction", "keywords", "index terms"):
            break
        if len(line) < 2:
            continue
        if len(line) > 280 and not collected:
            continue
        collected.append(line)
        if len(collected) >= 2 and len(" ".join(collected)) > 40:
            break
        if len(line) > 15:
            break
    if not collected:
        return ""
    out = " ".join(collected) if len(collected) > 1 else collected[0]
    return re.sub(r"\s+", " ", out).strip()


def _extract_title(
    doc: fitz.Document,
    first_page_plain: str,
    source_stem: str = "",
) -> str:
    """从正文第一页提取标题：合并最大字号档的多段文字，避免单段误选；必要时用行级回退。"""
    if len(doc) == 0:
        return "Untitled"

    page = doc[0]
    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

    spans: list[tuple[float, float, float, str]] = []
    max_sz = 0.0
    for block in blocks:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                t = span["text"].strip()
                if not t:
                    continue
                sz = float(span["size"])
                bbox = span["bbox"]
                max_sz = max(max_sz, sz)
                spans.append((bbox[1], bbox[0], sz, t))

    if not spans:
        alt = _title_from_first_page_text(first_page_plain)
        return alt or "Untitled"

    threshold = max(max_sz * 0.88, max_sz - 1.2)
    big = [s for s in spans if s[2] >= threshold]
    big.sort(key=lambda x: (x[0], x[1]))

    title = " ".join(s[3] for s in big)
    title = re.sub(r"\s+", " ", title).strip()

    low = title.lower()
    if len(title) < 4 or low in ("abstract", "introduction", "keywords"):
        title = ""

    if source_stem and title and _stem_matches_title(source_stem, title):
        title = ""

    if not title or len(title) < 6:
        alt = _title_from_first_page_text(first_page_plain)
        if alt:
            if not source_stem or not _stem_matches_title(source_stem, alt):
                title = alt

    if source_stem and title and _stem_matches_title(source_stem, title):
        alt = _title_from_first_page_text(first_page_plain)
        if alt and alt != title:
            title = alt

    return title if title else "Untitled"


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
