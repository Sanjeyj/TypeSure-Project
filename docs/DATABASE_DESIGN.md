# TypeSure — Database Design & Data Reliability Documentation

## 1. Schema Definitions & Entity Relationship

TypeSure utilizes an SQLite relational storage architecture configured with Write-Ahead Logging (`WAL`) mode and foreign key constraints enabled.

```sql
-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

-- 2. Checks (Writing Sessions) Table
CREATE TABLE IF NOT EXISTS checks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,                        -- References users(id) when authenticated
    session_id  TEXT NOT NULL DEFAULT 'default_session',
    created_at  TEXT NOT NULL,                  -- ISO-8601 UTC timestamp
    word_count  INTEGER NOT NULL,
    issue_count INTEGER NOT NULL,
    corrections INTEGER NOT NULL DEFAULT 0,
    store_text  INTEGER NOT NULL DEFAULT 0,      -- 1 if user explicitly opted in
    input_text  TEXT,                           -- NULL unless store_text = 1
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. Custom Vocabulary Table
CREATE TABLE IF NOT EXISTS custom_words (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    word        TEXT UNIQUE NOT NULL,
    created_at  TEXT NOT NULL
);

-- Indexes for Fast Query Retrieval
CREATE INDEX IF NOT EXISTS idx_checks_created_at ON checks(created_at);
CREATE INDEX IF NOT EXISTS idx_checks_user_id ON checks(user_id);
CREATE INDEX IF NOT EXISTS idx_checks_session_id ON checks(session_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
```

---

## 2. Serverless Storage Compatibility

On Vercel and AWS Lambda serverless deployments, the root directory filesystem is strictly **read-only**. Attempting to write to `data/typesure.db` causes an immediate `sqlite3.OperationalError: attempt to write a readonly database`.

TypeSure implements dynamic environment resolution in `typesure/database.py`:
```python
def _resolve_db_path():
    if os.environ.get("VERCEL"):
        db_dir = Path("/tmp")
    else:
        db_dir = Path(__file__).parent.parent / "data"
    return db_dir, db_dir / "typesure.db"
```
When running on Vercel, the database seamlessly routes to `/tmp/typesure.db`.

For permanent long-term production persistence beyond serverless container lifetimes, TypeSure is architected for drop-in migration to PostgreSQL (e.g. Supabase, Neon, or RDS) by switching the database connection string.
