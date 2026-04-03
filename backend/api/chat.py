from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.core.rag import ask

router = APIRouter(prefix="/api", tags=["chat"])


class ChatMessageItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    question: str
    history: list[ChatMessageItem] = Field(default_factory=list)


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
    hist = [m.model_dump() for m in req.history]
    result = ask(req.question, history=hist)
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
