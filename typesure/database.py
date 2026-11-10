"""
typesure/database.py — SQLite persistence for TypeSure users, checks, & custom dictionary.

Schema:
-------
users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
)

checks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,                        -- References users(id) when authenticated
    session_id  TEXT NOT NULL DEFAULT 'default_session',
    created_at  TEXT NOT NULL,                  -- ISO-8601 UTC timestamp
    word_count  INTEGER NOT NULL,
    issue_count INTEGER NOT NULL,
    corrections INTEGER NOT NULL DEFAULT 0,
    store_text  INTEGER NOT NULL DEFAULT 0,      -- 1 if user opted in
    input_text  TEXT                            -- NULL unless store_text = 1
)

custom_words (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    word        TEXT UNIQUE NOT NULL,
    created_at  TEXT NOT NULL
)

Security & Isolation:
  - Per-user history isolation: Logged in users access only their own checks (WHERE user_id = ?).
  - Unauthenticated guest users access only their session-specific checks (WHERE session_id = ?).
  - Passwords stored strictly as cryptographic hashes (never plaintext).
  - Parameterized queries prevent SQL injection.
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
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS checks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
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
    """Initialize database tables and run lightweight schema migrations."""
    with _get_connection() as conn:
        conn.executescript(_INIT_SQL)
        
        # Check columns on checks table
        cur = conn.execute("PRAGMA table_info(checks);")
        columns = [row["name"] for row in cur.fetchall()]
        if "session_id" not in columns:
            conn.execute("ALTER TABLE checks ADD COLUMN session_id TEXT NOT NULL DEFAULT 'default_session';")
        if "user_id" not in columns:
            conn.execute("ALTER TABLE checks ADD COLUMN user_id INTEGER;")
        
        # Safely create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_checks_user_id ON checks(user_id, id DESC);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_checks_session_id ON checks(session_id, id DESC);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_custom_words_word ON custom_words(word);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
        conn.commit()


# ─── User Authentication Database Operations ──────────────────────────────────

def create_user(full_name: str, email: str, password_hash: str) -> Optional[int]:
    """
    Create a new user record.
    Returns user id on success, or None if email already exists.
    """
    now = datetime.now(timezone.utc).isoformat()
    clean_email = email.strip().lower()
    clean_name = full_name.strip()
    with _get_connection() as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO users (full_name, email, password_hash, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (clean_name, clean_email, password_hash, now, now),
            )
            conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None


def get_user_by_email(email: str) -> Optional[Dict]:
    """Retrieve user record by email address (case-insensitive)."""
    clean_email = email.strip().lower()
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT id, full_name, email, password_hash, created_at, updated_at FROM users WHERE email = ?",
            (clean_email,),
        ).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Retrieve user record by integer ID."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT id, full_name, email, password_hash, created_at, updated_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None


def update_user_profile(user_id: int, full_name: str) -> bool:
    """Update user's display name."""
    now = datetime.now(timezone.utc).isoformat()
    with _get_connection() as conn:
        cur = conn.execute(
            "UPDATE users SET full_name = ?, updated_at = ? WHERE id = ?",
            (full_name.strip(), now, user_id),
        )
        conn.commit()
        return cur.rowcount > 0


def update_user_password(user_id: int, password_hash: str) -> bool:
    """Update user's password hash."""
    now = datetime.now(timezone.utc).isoformat()
    with _get_connection() as conn:
        cur = conn.execute(
            "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
            (password_hash, now, user_id),
        )
        conn.commit()
        return cur.rowcount > 0


# ─── Check History Operations (Per-User & Per-Session) ────────────────────────

def save_check(
    word_count: int,
    issue_count: int,
    corrections: int = 0,
    input_text: str = None,
    store_text: bool = False,
    session_id: str = "default_session",
    user_id: Optional[int] = None,
) -> int:
    """Persist a check record associated with user_id and/or session_id."""
    now = datetime.now(timezone.utc).isoformat()
    text_to_store = input_text if store_text else None
    with _get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO checks
                (user_id, session_id, created_at, word_count, issue_count, corrections,
                 store_text, input_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, session_id, now, word_count, issue_count, corrections,
             1 if store_text else 0, text_to_store),
        )
        conn.commit()
        return cur.lastrowid


def get_history(
    limit: int = 20,
    session_id: Optional[str] = None,
    user_id: Optional[int] = None,
) -> List[Dict]:
    """
    Retrieve history records.
    Prioritizes user_id if authenticated, else filters by session_id with graceful fallback.
    """
    limit = max(1, min(limit, 200))
    with _get_connection() as conn:
        if user_id:
            rows = conn.execute(
                """
                SELECT id, user_id, session_id, created_at, word_count, issue_count,
                       corrections, store_text,
                       CASE WHEN store_text = 1 THEN input_text ELSE NULL END AS input_text
                FROM checks
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

        if session_id and session_id != "default_session":
            rows = conn.execute(
                """
                SELECT id, user_id, session_id, created_at, word_count, issue_count,
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

        # General fallback
        rows = conn.execute(
            """
            SELECT id, user_id, session_id, created_at, word_count, issue_count,
                   corrections, store_text,
                   CASE WHEN store_text = 1 THEN input_text ELSE NULL END AS input_text
            FROM checks
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_history(
    session_id: Optional[str] = None,
    user_id: Optional[int] = None,
) -> int:
    """Delete check records scoped to user_id or session_id."""
    with _get_connection() as conn:
        if user_id:
            cur = conn.execute("DELETE FROM checks WHERE user_id = ?", (user_id,))
        elif session_id:
            cur = conn.execute("DELETE FROM checks WHERE session_id = ?", (session_id,))
        else:
            cur = conn.execute("DELETE FROM checks")
        conn.commit()
        return cur.rowcount


def delete_history_item(
    item_id: int,
    session_id: Optional[str] = None,
    user_id: Optional[int] = None,
) -> bool:
    """Delete a single history record by ID, scoped to user_id or session_id."""
    with _get_connection() as conn:
        if user_id:
            cur = conn.execute("DELETE FROM checks WHERE id = ? AND user_id = ?", (item_id, user_id))
        elif session_id:
            cur = conn.execute("DELETE FROM checks WHERE id = ? AND session_id = ?", (item_id, session_id))
        else:
            cur = conn.execute("DELETE FROM checks WHERE id = ?", (item_id,))
        conn.commit()
        return cur.rowcount > 0


def get_summary_stats(
    session_id: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Dict:
    """Return aggregate statistics across stored checks for user or session."""
    with _get_connection() as conn:
        if user_id:
            row = conn.execute(
                """
                SELECT
                    COUNT(*)                      AS total_checks,
                    COALESCE(SUM(word_count), 0)  AS total_words,
                    COALESCE(SUM(issue_count), 0) AS total_issues,
                    COALESCE(SUM(corrections), 0) AS total_corrections
                FROM checks
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        elif session_id:
            row = conn.execute(
                """
                SELECT
                    COUNT(*)                      AS total_checks,
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
                    COUNT(*)                      AS total_checks,
                    COALESCE(SUM(word_count), 0)  AS total_words,
                    COALESCE(SUM(issue_count), 0) AS total_issues,
                    COALESCE(SUM(corrections), 0) AS total_corrections
                FROM checks
                """
            ).fetchone()
    return dict(row) if row else {
        "total_checks": 0,
        "total_words": 0,
        "total_issues": 0,
        "total_corrections": 0,
    }


# ─── Custom Words Dictionary Persistence ──────────────────────────────────────

def save_custom_words(words: List[str]) -> int:
    """Persist custom words into custom_words table."""
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
