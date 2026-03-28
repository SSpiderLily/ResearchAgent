from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.core.rag import ask

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    question: str


class ReferenceItem(BaseModel):
    paper_id: str
    paper_title: str
    page: int
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    references: list[ReferenceItem]


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    result = ask(req.question)
    return ChatResponse(
        answer=result.answer,
        references=[
            ReferenceItem(
                paper_id=r.paper_id,
                paper_title=r.paper_title,
                page=r.page,
                snippet=r.snippet,
            )
            for r in result.references
        ],
    )
