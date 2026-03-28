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


def insert_paper(
    title: str,
    authors: str,
    abstract: str,
    file_path: str,
    page_count: int,
) -> str:
    paper_id = uuid.uuid4().hex[:12]
    now = datetime.now().isoformat()
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO papers (id, title, authors, abstract, file_path, page_count, upload_time) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (paper_id, title, authors, abstract, file_path, page_count, now),
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
