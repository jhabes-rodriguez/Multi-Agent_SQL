import sqlite3
import os

DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/multiagent.db")
DATASETS_DIR  = os.getenv("DATASETS_DIR",  "./data/datasets")


def get_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Crea todas las tablas si no existen."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS datasets (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT    UNIQUE NOT NULL,
            description    TEXT    DEFAULT '',
            source_url     TEXT    DEFAULT '',
            votes          INTEGER DEFAULT 0,
            rows_count     INTEGER DEFAULT 0,
            columns_count  INTEGER DEFAULT 0,
            file_path      TEXT,
            created_at     TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS queries (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id       INTEGER,
            natural_language TEXT,
            sql_query        TEXT,
            result_json      TEXT,
            execution_time   REAL    DEFAULT 0.0,
            created_at       TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (dataset_id) REFERENCES datasets(id)
        );

        CREATE TABLE IF NOT EXISTS insights (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_id INTEGER,
            query_id   INTEGER,
            title      TEXT,
            content    TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (dataset_id) REFERENCES datasets(id),
            FOREIGN KEY (query_id)   REFERENCES queries(id)
        );

        CREATE TABLE IF NOT EXISTS query_cache (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            cache_key     TEXT UNIQUE,
            sql_query     TEXT,
            result_json   TEXT,
            hit_count     INTEGER DEFAULT 1,
            created_at    TEXT DEFAULT (datetime('now')),
            last_accessed TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()
