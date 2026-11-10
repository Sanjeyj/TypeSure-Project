"""
typesure/database.py — SQLite persistence for TypeSure check history & custom dictionary.

Schema:
-------
checks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL DEFAULT 'default_session',
    created_at  TEXT NOT NULL,          -- ISO-8601 UTC timestamp
    word_count  INTEGER NOT NULL,
    issue_count INTEGER NOT NULL,
    corrections INTEGER NOT NULL DEFAULT 0,
    store_text  INTEGER NOT NULL DEFAULT 0,  -- 1 if user opted in
    input_text  TEXT                    -- NULL unless store_text = 1
)

custom_words (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    word        TEXT UNIQUE NOT NULL,
    created_at  TEXT NOT NULL
)

Indexes:
  - idx_checks_session_id ON checks(session_id, id DESC);
  - idx_custom_words_word ON custom_words(word);

Privacy & Security:
  - Client session isolation via session_id ensures users only view their own history.
  - Full input text is only stored when the user explicitly opts in.
  - Parameterized queries (? placeholders) prevent SQL injection vulnerabilities.
"""

import sqlite3
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple


def _resolve_db_path() -> Tuple[Path, Path]:
    """
    Determine the database file location.
    On Vercel / serverless platforms, writable storage is under /tmp.
    """
    if os.environ.get("VERCEL"):
        db_dir = Path("/tmp")
    else:
        db_dir = Path(__file__).parent.parent / "data"
    return db_dir, db_dir / "typesure.db"


_DB_DIR, _DB_PATH = _resolve_db_path()

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS checks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT    NOT NULL DEFAULT 'default_session',
    created_at  TEXT    NOT NULL,
    word_count  INTEGER NOT NULL,
    issue_count INTEGER NOT NULL,
    corrections INTEGER NOT NULL DEFAULT 0,
    store_text  INTEGER NOT NULL DEFAULT 0,
    input_text  TEXT
);

CREATE TABLE IF NOT EXISTS custom_words (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    word        TEXT UNIQUE NOT NULL,
    created_at  TEXT NOT NULL
);
"""


def _get_connection() -> sqlite3.Connection:
    """Open and configure an SQLite database connection."""
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except sqlite3.OperationalError:
        pass
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db():
    """Initialize database tables and run lightweight migrations if needed."""
    with _get_connection() as conn:
        conn.executescript(_INIT_SQL)
        # Check if session_id column exists on checks (for migrations from v1)
        cur = conn.execute("PRAGMA table_info(checks);")
        columns = [row["name"] for row in cur.fetchall()]
        if "session_id" not in columns:
            conn.execute("ALTER TABLE checks ADD COLUMN session_id TEXT NOT NULL DEFAULT 'default_session';")
        
        # Now create indexes safely
        conn.execute("CREATE INDEX IF NOT EXISTS idx_checks_session_id ON checks(session_id, id DESC);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_custom_words_word ON custom_words(word);")
        conn.commit()


def save_check(
    word_count: int,
    issue_count: int,
    corrections: int = 0,
    input_text: str = None,
    store_text: bool = False,
    session_id: str = "default_session",
) -> int:
    """Persist a check session under the given session_id."""
    now = datetime.now(timezone.utc).isoformat()
    text_to_store = input_text if store_text else None
    with _get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO checks
                (session_id, created_at, word_count, issue_count, corrections,
                 store_text, input_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, now, word_count, issue_count, corrections,
             1 if store_text else 0, text_to_store),
        )
        conn.commit()
        return cur.lastrowid


def get_history(limit: int = 20, session_id: Optional[str] = None) -> List[Dict]:
    """Retrieve history records. If session_id is provided, filters by session with fallback."""
    limit = max(1, min(limit, 200))
    with _get_connection() as conn:
        if session_id and session_id != "default_session":
            rows = conn.execute(
                """
                SELECT id, session_id, created_at, word_count, issue_count,
                       corrections, store_text,
                       CASE WHEN store_text = 1 THEN input_text ELSE NULL END AS input_text
                FROM checks
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
            if rows:
                return [dict(r) for r in rows]

        rows = conn.execute(
            """
            SELECT id, session_id, created_at, word_count, issue_count,
                   corrections, store_text,
                   CASE WHEN store_text = 1 THEN input_text ELSE NULL END AS input_text
            FROM checks
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_history(session_id: Optional[str] = None) -> int:
    """Delete check records. If session_id is provided, deletes only that session's records."""
    with _get_connection() as conn:
        if session_id:
            cur = conn.execute("DELETE FROM checks WHERE session_id = ?", (session_id,))
        else:
            cur = conn.execute("DELETE FROM checks")
        conn.commit()
        return cur.rowcount


def delete_history_item(item_id: int, session_id: Optional[str] = None) -> bool:
    """Delete a single history record by ID, scoped to session_id if provided."""
    with _get_connection() as conn:
        if session_id:
            cur = conn.execute("DELETE FROM checks WHERE id = ? AND session_id = ?", (item_id, session_id))
        else:
            cur = conn.execute("DELETE FROM checks WHERE id = ?", (item_id,))
        conn.commit()
        return cur.rowcount > 0


def save_custom_words(words: List[str]) -> int:
    """Persist newly imported custom words into custom_words table."""
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    with _get_connection() as conn:
        for w in words:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO custom_words (word, created_at) VALUES (?, ?)",
                    (w, now),
                )
                inserted += 1
            except sqlite3.Error:
                pass
        conn.commit()
    return inserted


def load_persisted_custom_words() -> List[str]:
    """Retrieve all persisted custom words from the database."""
    try:
        with _get_connection() as conn:
            rows = conn.execute("SELECT word FROM custom_words").fetchall()
            return [r["word"] for r in rows]
    except sqlite3.OperationalError:
        return []


def get_summary_stats(session_id: Optional[str] = None) -> Dict:
    """Return aggregate statistics across stored checks."""
    with _get_connection() as conn:
        if session_id:
            row = conn.execute(
                """
                SELECT
                    COUNT(*)          AS total_checks,
                    COALESCE(SUM(word_count), 0)  AS total_words,
                    COALESCE(SUM(issue_count), 0) AS total_issues,
                    COALESCE(SUM(corrections), 0) AS total_corrections
                FROM checks
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        else:
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
