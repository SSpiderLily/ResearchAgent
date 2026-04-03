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


# ── upload page ──────────────────────────────────────────────────────

if page == "上传文献":
    st.title("📄 上传文献")
    st.markdown("上传 PDF 论文，系统将自动解析并存入知识库。")

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
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("标题", data.get("title", ""))
                    st.metric("页数", data.get("page_count", 0))
                with col2:
                    st.metric("作者", data.get("authors", "") or "未识别")
                    st.metric("文本块数", data.get("chunk_count", 0))

                if data.get("abstract"):
                    st.subheader("摘要")
                    st.write(data["abstract"])
            else:
                st.error(f"解析失败：{resp.text}")

    st.divider()
    st.subheader("已入库文献")
    try:
        papers = requests.get(f"{API}/api/papers/", timeout=5).json()
    except Exception:
        papers = []

    if not papers:
        st.info("知识库暂无文献，请先上传。")
    else:
        for p in papers:
            with st.expander(f"📑 {p['title']}"):
                st.write(f"**作者：** {p.get('authors') or '未识别'}")
                st.write(f"**页数：** {p.get('page_count', '?')}")
                st.write(f"**上传时间：** {p.get('upload_time', '')}")
                if p.get("abstract"):
                    st.caption(p["abstract"][:300])


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
