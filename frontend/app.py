import sys
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import requests
import streamlit as st
from config import BACKEND_URL

st.set_page_config(page_title="Research Copilot", page_icon="📚", layout="wide")

# ── sidebar navigation ──────────────────────────────────────────────

page = st.sidebar.radio("导航", ["上传文献", "智能问答"], index=0)

# ── helpers ──────────────────────────────────────────────────────────

API = BACKEND_URL


def _api_ok() -> bool:
    try:
        r = requests.get(f"{API}/health", timeout=3)
        return r.status_code == 200
    except requests.ConnectionError:
        return False


def _paper_main_content(p: dict) -> str:
    abstract = (p.get("abstract") or "").strip()
    if abstract:
        return abstract
    preview = (p.get("content_preview") or "").strip()
    return preview


def _paper_year_label(p: dict) -> str:
    y = p.get("year")
    if y is None:
        return "未识别"
    return str(y)


# ── upload page ──────────────────────────────────────────────────────

if page == "上传文献":
    if "pending_delete_id" not in st.session_state:
        st.session_state.pending_delete_id = None

    st.title("📄 上传文献")
    st.markdown(
        "上传 PDF 论文，系统将自动解析并存入知识库。"
        "解析出的标题可能不准或与文件名不一致，请在下方 **已入库文献** 中更正标题，"
        "智能问答中的引用将使用该标题。"
    )

    if not _api_ok():
        st.error("后端服务未启动，请先运行 FastAPI 后端。")
        st.stop()

    uploaded = st.file_uploader("选择 PDF 文件", type=["pdf"])

    if uploaded is not None:
        if st.button("开始解析", type="primary"):
            with st.spinner("正在解析论文并构建向量索引，请稍候..."):
                resp = requests.post(
                    f"{API}/api/papers/upload",
                    files={"file": (uploaded.name, uploaded.getvalue(), "application/pdf")},
                    timeout=120,
                )

            if resp.status_code == 200:
                data = resp.json()
                st.success("论文解析完成！")
                u1, u2 = st.columns(2)
                with u1:
                    st.markdown(
                        f"**标题**\n\n{(data.get('title') or '—')}"
                    )
                    st.markdown(
                        f"**作者**\n\n{(data.get('authors') or '').strip() or '未识别'}"
                    )
                with u2:
                    st.markdown(f"**页数**\n\n{data.get('page_count', 0)}")
                    yr = data.get("year")
                    st.markdown(
                        f"**年份**\n\n{yr if yr is not None else '未识别'}"
                    )
                st.caption(f"文本块数：{data.get('chunk_count', 0)}")
                st.markdown("**主要内容**")
                _mc = (data.get("abstract") or "").strip() or (data.get("content_preview") or "").strip()
                st.write(_mc or "（暂无摘要且未能生成正文预览）")
            else:
                st.error(f"解析失败：{resp.text}")

    st.divider()
    st.subheader("已入库文献")
    st.caption(
        "点击条目左侧可展开/折叠详情；摘要与正文预览见展开区。"
        "优先展示摘要，无摘要时显示正文开头预览。"
    )
    try:
        papers = requests.get(f"{API}/api/papers/", timeout=5).json()
    except Exception:
        papers = []

    if not papers:
        st.info("知识库暂无文献，请先上传。")
    else:
        st.caption(f"共 **{len(papers)}** 篇文献（默认折叠，便于快速浏览）。")
        expand_all = st.checkbox(
            "一次性展开全部文献详情",
            value=False,
            key="expand_all_papers",
        )
        for p in papers:
            pid = p["id"]
            main = _paper_main_content(p)
            raw_title = (p.get("title") or "（无标题）").strip()
            title_1line = raw_title if len(raw_title) <= 72 else raw_title[:69] + "…"
            _auth_short = (p.get("authors") or "").strip() or "—"
            if len(_auth_short) > 36:
                _auth_short = _auth_short[:33] + "…"
            expand_label = f"📑 {title_1line}　·　{_paper_year_label(p)}　·　{_auth_short}"
            # 删除确认中自动展开该条；勾选「展开全部」时全部展开
            _open = (
                st.session_state.pending_delete_id == pid or expand_all
            )

            with st.expander(expand_label, expanded=_open):
                st.markdown(f"##### {raw_title}")
                a1, a2, a3 = st.columns((2.2, 2.2, 1.0))
                with a1:
                    _auth = (p.get("authors") or "").strip() or "—"
                    st.markdown(f"**作者**\n\n{_auth}")
                with a2:
                    st.markdown(f"**年份**\n\n{_paper_year_label(p)}")
                with a3:
                    _ut = (p.get("upload_time") or "")[:10]
                    st.caption(f"上传 {_ut or '—'}")
                st.markdown("**主要内容**")
                if main:
                    st.write(main)
                else:
                    st.caption("暂无摘要与正文预览（较早入库记录可能没有预览字段，可重新上传或后续扩展解析）")

                with st.expander("编辑标题（问答引用名）", expanded=False):
                    st.caption(f"文献 ID：`{pid}`")
                    new_title = st.text_input(
                        "文献标题（用于列表与问答引用）",
                        value=p["title"],
                        key=f"paper_title_{pid}",
                        label_visibility="collapsed",
                    )
                    if st.button("保存标题", key=f"save_title_{pid}"):
                        nt = (new_title or "").strip()
                        if not nt:
                            st.warning("标题不能为空。")
                        else:
                            pr = requests.patch(
                                f"{API}/api/papers/{pid}",
                                json={"title": nt},
                                timeout=10,
                            )
                            if pr.status_code == 200:
                                st.success("标题已更新。")
                                st.rerun()
                            else:
                                st.error(f"更新失败：{pr.text}")

                if st.session_state.pending_delete_id == pid:
                    st.warning("确认从知识库删除该文献？将同时移除向量索引与本地 PDF，且不可恢复。")
                    d1, d2 = st.columns(2)
                    with d1:
                        if st.button("确认删除", key=f"confirm_del_{pid}", type="primary"):
                            dr = requests.delete(f"{API}/api/papers/{pid}", timeout=30)
                            if dr.status_code == 200:
                                st.session_state.pending_delete_id = None
                                st.success("已删除。")
                                st.rerun()
                            else:
                                st.error(f"删除失败：{dr.text}")
                    with d2:
                        if st.button("取消", key=f"cancel_del_{pid}"):
                            st.session_state.pending_delete_id = None
                            st.rerun()
                else:
                    if st.button("🗑️ 删除该文献", key=f"del_{pid}"):
                        st.session_state.pending_delete_id = pid
                        st.rerun()


# ── chat page ────────────────────────────────────────────────────────

elif page == "智能问答":
    st.title("💬 跨论文智能问答")
    st.markdown("基于已上传的论文知识库，提出你的研究问题。")

    if not _api_ok():
        st.error("后端服务未启动，请先运行 FastAPI 后端。")
        st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("references"):
                with st.expander("📎 引用来源"):
                    for ref in msg["references"]:
                        st.write(f"- **{ref['paper_title']}** 第{ref['page']}页")
                        st.caption(ref["snippet"])

    if prompt := st.chat_input("输入你的问题，例如：对比论文A与B在训练策略上的差异"):
        history_payload = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages
        ]

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                try:
                    resp = requests.post(
                        f"{API}/api/chat",
                        json={"question": prompt, "history": history_payload},
                        timeout=120,
                    )
                    data = resp.json()
                    answer = data.get("answer", "抱歉，发生了错误。")
                    references = data.get("references", [])
                except Exception as e:
                    answer = f"请求失败：{e}"
                    references = []

            st.markdown(answer)
            if references:
                with st.expander("📎 引用来源"):
                    for ref in references:
                        st.write(f"- **{ref['paper_title']}** 第{ref['page']}页")
                        st.caption(ref["snippet"])

        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "references": references}
        )
