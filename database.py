import sqlite3
from datetime import datetime

DB_PATH = "runs.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            variant_name TEXT,
            temperature REAL,
            task TEXT,
            clause_text TEXT,
            response TEXT,
            score INTEGER,
            latency_seconds REAL,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_run(run_id, variant_name, temperature, task, clause_text, response, score, latency_seconds):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO runs (run_id, variant_name, temperature, task, clause_text, response, score, latency_seconds, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (run_id, variant_name, temperature, task, clause_text, response, score, latency_seconds, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_runs_by_run_id(run_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT * FROM runs WHERE run_id = ? ORDER BY score DESC
    """, (run_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_run_ids():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT DISTINCT run_id, task, created_at FROM runs ORDER BY created_at DESC
    """).fetchall()
    conn.close()
    return rows