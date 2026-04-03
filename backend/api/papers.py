from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.core.chunker import chunk_pages
from backend.core.embedder import embed_texts
from backend.core.parser import parse_pdf
from backend.storage.database import (
    delete_paper,
    get_paper,
    insert_paper,
    list_papers,
    update_paper_title,
)
from backend.storage.vectorstore import add_chunks, delete_by_paper_id
from config import UPLOAD_DIR

router = APIRouter(prefix="/api/papers", tags=["papers"])


class PaperTitleUpdate(BaseModel):
    title: str = Field(..., description="用于展示与问答引用的文献标题")


@router.post("/upload")
async def upload_paper(file: UploadFile):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")

    # 存盘名与上传文件名脱钩，避免展示/调试时与「正文标题」混淆
    dest = UPLOAD_DIR / f"{uuid.uuid4().hex}.pdf"
    upload_stem = Path(file.filename).stem
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    parsed = parse_pdf(dest, upload_filename_stem=upload_stem)

    paper_id = insert_paper(
        title=parsed.title,
        authors=parsed.authors,
        abstract=parsed.abstract,
        file_path=str(dest),
        page_count=parsed.page_count,
        year=parsed.year,
        content_preview=parsed.content_preview,
    )

    chunks = chunk_pages(parsed.pages, paper_id=paper_id)

    if chunks:
        texts = [c.text for c in chunks]
        embeddings = embed_texts(texts)
        add_chunks(
            ids=[f"{paper_id}_{c.index}" for c in chunks],
            documents=texts,
            embeddings=embeddings,
            metadatas=[
                {"paper_id": c.paper_id, "page": c.page, "index": c.index}
                for c in chunks
            ],
        )

    return {
        "paper_id": paper_id,
        "title": parsed.title,
        "authors": parsed.authors,
        "year": parsed.year,
        "abstract": parsed.abstract,
        "content_preview": parsed.content_preview,
        "page_count": parsed.page_count,
        "chunk_count": len(chunks),
    }


@router.get("/")
async def get_papers():
    return list_papers()


@router.get("/{paper_id}")
async def get_paper_detail(paper_id: str):
    paper = get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    return paper


@router.patch("/{paper_id}")
async def patch_paper(paper_id: str, body: PaperTitleUpdate):
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="标题不能为空")
    ok = update_paper_title(paper_id, title)
    if not ok:
        raise HTTPException(status_code=404, detail="论文不存在")
    paper = get_paper(paper_id)
    if paper is None:
        raise HTTPException(status_code=500, detail="内部错误")
    return paper


@router.delete("/{paper_id}")
async def remove_paper(paper_id: str):
    paper = get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="论文不存在")
    fp = paper.get("file_path")
    delete_by_paper_id(paper_id)
    delete_paper(paper_id)
    if fp:
        try:
            Path(fp).unlink(missing_ok=True)
        except OSError:
            pass
    return {"detail": "已删除"}
