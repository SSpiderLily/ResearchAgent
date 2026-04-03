from __future__ import annotations

from dataclasses import dataclass, field

from backend.core.embedder import embed_query
from backend.core.llm import chat_completion
from backend.storage.database import get_paper
from backend.storage.vectorstore import query_chunks
from config import CHAT_HISTORY_MAX_MESSAGES, RAG_TOP_K

_SYSTEM_PROMPT = (
    "你是一位专业的科研助手（Research Copilot）。"
    "请根据以下检索到的论文片段回答用户问题。\n"
    "要求：\n"
    "1. 回答应准确、简洁，优先使用中文。\n"
    "2. 必须在回答中标注引用来源，格式为 [论文标题, 第X页]。\n"
    "3. 如果检索内容不足以回答问题，请如实说明。\n"
    "4. 若存在历史对话，请结合追问与指代（如“那篇论文”“同上”）理解意图；"
    "回答仍须优先依据本轮提供的检索片段。\n"
)


@dataclass
class Reference:
    paper_id: str
    paper_title: str
    page: int
    snippet: str


@dataclass
class RAGResult:
    answer: str
    references: list[Reference] = field(default_factory=list)


def _normalize_history(
    history: list[dict] | None,
    max_messages: int = CHAT_HISTORY_MAX_MESSAGES,
) -> list[dict]:
    if not history:
        return []
    out: list[dict] = []
    for m in history:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        out.append({"role": role, "content": content})
    if len(out) > max_messages:
        out = out[-max_messages:]
    return out


def ask(
    question: str,
    history: list[dict] | None = None,
    top_k: int = RAG_TOP_K,
) -> RAGResult:
    trimmed = _normalize_history(history)
    query_emb = embed_query(question)
    results = query_chunks(query_emb, top_k=top_k)

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    if not documents:
        if not trimmed:
            return RAGResult(
                answer="当前知识库中没有找到与您问题相关的论文内容，请先上传相关文献。"
            )
        follow_up = (
            "（本轮知识库未检索到与当前问题直接相关的片段。"
            "请结合上文对话作答；若无法从对话中确定事实，请如实说明。）\n\n"
            f"{question}"
        )
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            *trimmed,
            {"role": "user", "content": follow_up},
        ]
        answer = chat_completion(messages)
        return RAGResult(answer=answer, references=[])

    context_parts: list[str] = []
    references: list[Reference] = []
    seen: set[tuple[str, int]] = set()

    for doc, meta in zip(documents, metadatas):
        paper_id = meta.get("paper_id", "")
        page = meta.get("page", 0)

        paper = get_paper(paper_id)
        paper_title = paper["title"] if paper else "未知论文"

        key = (paper_id, page)
        if key not in seen:
            seen.add(key)
            references.append(
                Reference(
                    paper_id=paper_id,
                    paper_title=paper_title,
                    page=page,
                    snippet=doc[:200],
                )
            )

        context_parts.append(
            f"[来源: {paper_title}, 第{page}页]\n{doc}"
        )

    context_block = "\n\n---\n\n".join(context_parts)

    user_turn = (
        f"以下是从知识库中检索到的论文片段：\n\n{context_block}\n\n"
        f"请根据以上内容回答：{question}"
    )

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        *trimmed,
        {"role": "user", "content": user_turn},
    ]

    answer = chat_completion(messages)
    return RAGResult(answer=answer, references=references)
