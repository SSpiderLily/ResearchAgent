import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import SQLITE_PATH


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _migrate_papers_schema(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(papers)").fetchall()}
    if "year" not in cols:
        conn.execute("ALTER TABLE papers ADD COLUMN year INTEGER")
    if "content_preview" not in cols:
        conn.execute("ALTER TABLE papers ADD COLUMN content_preview TEXT DEFAULT ''")


def init_db() -> None:
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id          TEXT PRIMARY KEY,
                title       TEXT NOT NULL,
                authors     TEXT DEFAULT '',
                abstract    TEXT DEFAULT '',
                file_path   TEXT NOT NULL,
                page_count  INTEGER DEFAULT 0,
                upload_time TEXT NOT NULL
            )
        """)
        _migrate_papers_schema(conn)


def insert_paper(
    title: str,
    authors: str,
    abstract: str,
    file_path: str,
    page_count: int,
    year: int | None = None,
    content_preview: str = "",
) -> str:
    paper_id = uuid.uuid4().hex[:12]
    now = datetime.now().isoformat()
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO papers (id, title, authors, abstract, file_path, page_count, "
            "upload_time, year, content_preview) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                paper_id,
                title,
                authors,
                abstract,
                file_path,
                page_count,
                now,
                year,
                content_preview,
            ),
        )
    return paper_id


def get_paper(paper_id: str) -> Optional[dict]:
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
    return dict(row) if row else None


def list_papers() -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM papers ORDER BY upload_time DESC").fetchall()
    return [dict(r) for r in rows]


def delete_paper(paper_id: str) -> bool:
    with _get_conn() as conn:
        cur = conn.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
    return cur.rowcount > 0


def update_paper_title(paper_id: str, title: str) -> bool:
    title = title.strip()
    if not title:
        return False
    with _get_conn() as conn:
        cur = conn.execute(
            "UPDATE papers SET title = ? WHERE id = ?",
            (title, paper_id),
        )
    return cur.rowcount > 0
