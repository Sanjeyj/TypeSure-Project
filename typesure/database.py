"""
database.py — SQLite persistence for TypeSure check history.

Schema
------
checks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,          -- ISO-8601 UTC timestamp
    word_count  INTEGER NOT NULL,
    issue_count INTEGER NOT NULL,
    corrections INTEGER NOT NULL DEFAULT 0,
    store_text  INTEGER NOT NULL DEFAULT 0,  -- 1 if user opted in
    input_text  TEXT                    -- NULL unless store_text = 1
)

Privacy note:
  Full input text is only stored when the user explicitly opts in
  (store_text = 1). The default is to store only statistics.

Security:
  All SQL statements use parameterized queries (? placeholders) to
  prevent SQL injection.
"""

import sqlite3
import os
from datetime import datetime, timezone
from pathlib import Path


def _resolve_db_path() -> Path:
    """
    Determine the database file location.

    On Vercel (and similar serverless platforms), the project directory is
    read-only.  Only /tmp is writable.  When the VERCEL environment variable
    is set, the database is placed under /tmp so that init_db() can create
    the schema without raising an OperationalError.
    """
    if os.environ.get("VERCEL"):
        db_dir = Path("/tmp")
    else:
        db_dir = Path(__file__).parent.parent / "data"
    return db_dir, db_dir / "typesure.db"


_DB_DIR, _DB_PATH = _resolve_db_path()

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS checks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT    NOT NULL,
    word_count  INTEGER NOT NULL,
    issue_count INTEGER NOT NULL,
    corrections INTEGER NOT NULL DEFAULT 0,
    store_text  INTEGER NOT NULL DEFAULT 0,
    input_text  TEXT
);
"""


def _get_connection() -> sqlite3.Connection:
    """Open (and configure) a connection to the SQLite database."""
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    # Use WAL journal mode for better concurrency (ignored if /tmp resets)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except sqlite3.OperationalError:
        pass  # WAL not available on all filesystems
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db():
    """Create tables if they do not already exist."""
    with _get_connection() as conn:
        conn.execute(_CREATE_TABLE_SQL)
        conn.commit()


def save_check(
    word_count: int,
    issue_count: int,
    corrections: int = 0,
    input_text: str = None,
    store_text: bool = False,
) -> int:
    """
    Persist a spell-check session to the database.

    Parameters
    ----------
    word_count  : total Tamil words scanned.
    issue_count : number of potential issues found.
    corrections : number of corrections accepted by the user.
    input_text  : the original text (only stored when store_text=True).
    store_text  : whether to store the full input text.

    Returns
    -------
    The row id of the inserted record.
    """
    now = datetime.now(timezone.utc).isoformat()
    text_to_store = input_text if store_text else None
    with _get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO checks
                (created_at, word_count, issue_count, corrections,
                 store_text, input_text)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (now, word_count, issue_count, corrections,
             1 if store_text else 0, text_to_store),
        )
        conn.commit()
        return cur.lastrowid


def get_history(limit: int = 20) -> list:
    """
    Return the most recent `limit` check records.

    Returns a list of dicts (safe for JSON serialization).
    """
    limit = max(1, min(limit, 200))
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, word_count, issue_count,
                   corrections, store_text,
                   CASE WHEN store_text = 1 THEN input_text ELSE NULL END AS input_text
            FROM checks
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_history() -> int:
    """
    Delete all check records.
    Returns the number of rows deleted.
    """
    with _get_connection() as conn:
        cur = conn.execute("DELETE FROM checks")
        conn.commit()
        return cur.rowcount


def get_summary_stats() -> dict:
    """Return aggregate statistics across all stored checks."""
    with _get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*)          AS total_checks,
                COALESCE(SUM(word_count), 0)  AS total_words,
                COALESCE(SUM(issue_count), 0) AS total_issues,
                COALESCE(SUM(corrections), 0) AS total_corrections
            FROM checks
            """
        ).fetchone()
    return dict(row) if row else {}
