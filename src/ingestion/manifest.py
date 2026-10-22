import sqlite3
from datetime import datetime
from pathlib import Path

DB = Path("data/manifest.db")

def _conn():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS docs (
        doc_id TEXT PRIMARY KEY, original_name TEXT, format TEXT,
        sections INTEGER, chars INTEGER, loader_version TEXT,
        status TEXT, error TEXT, updated_at TEXT)""")
    return c

def record(doc_id, name, fmt, sections, chars, version, status, error=""):
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO docs VALUES (?,?,?,?,?,?,?,?,?)",
                  (doc_id, name, fmt, sections, chars, version, status,
                   error, datetime.now().isoformat(timespec="seconds")))