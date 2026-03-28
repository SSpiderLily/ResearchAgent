from __future__ import annotations

import shutil

from fastapi import APIRouter, HTTPException, UploadFile

from backend.core.chunker import chunk_pages
from backend.core.embedder import embed_texts
from backend.core.parser import parse_pdf
from backend.storage.database import (
    delete_paper,
    get_paper,
    insert_paper,
    list_papers,
)
from backend.storage.vectorstore import add_chunks, delete_by_paper_id
from config import UPLOAD_DIR

router = APIRouter(prefix="/api/papers", tags=["papers"])


@router.post("/upload")
async def upload_paper(file: UploadFile):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")

    dest = UPLOAD_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    parsed = parse_pdf(dest)

    paper_id = insert_paper(
        title=parsed.title,
        authors=parsed.authors,
        abstract=parsed.abstract,
        file_path=str(dest),
        page_count=parsed.page_count,
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
        "abstract": parsed.abstract,
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


@router.delete("/{paper_id}")
async def remove_paper(paper_id: str):
    delete_by_paper_id(paper_id)
    deleted = delete_paper(paper_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="论文不存在")
    return {"detail": "已删除"}
