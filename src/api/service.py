import sqlite3
import time
import uuid
from contextlib import closing
from pathlib import Path

from src.indexing.settings import load_settings
from src.indexing.store import open_store
from src.ingestion.manifest import DB

from . import config
from .state import rag

JOBS: dict[str, dict] = {}


def wait_for_chroma(timeout: int = 90):
    s = load_settings()
    if not s.chroma_host:
        return
    import chromadb
    end = time.time() + timeout
    while True:
        try:
            chromadb.HttpClient(host=s.chroma_host, port=s.chroma_port).heartbeat()
            return
        except Exception:
            if time.time() > end:
                raise
            time.sleep(2)


def index_stats() -> dict[str, int | None]:
    s, out = load_settings(), {}
    for name in config.STRATEGIES:
        try:
            out[name] = open_store(name, s).col.count()
        except Exception:
            out[name] = None
    return out


_COLUMNS = ("doc_id, original_name AS name, format, sections, chars, "
            "loader_version, status, error, updated_at")


def list_documents(status=None, limit=100, offset=0, names=None):
    if not Path(DB).exists():
        return 0, []
    where, args = "", []
    if status:
        where, args = "WHERE status = ?", [status]
    if names:
        marks = ",".join("?" * len(names))
        where += (" AND " if where else "WHERE ") + f"original_name IN ({marks})"
        args += list(names)
    try:
        with closing(sqlite3.connect(f"file:{DB}?mode=ro", uri=True)) as c:
            c.row_factory = sqlite3.Row
            total = c.execute(f"SELECT COUNT(*) FROM docs {where}", args).fetchone()[0]
            rows = c.execute(f"SELECT {_COLUMNS} FROM docs {where} "
                             f"ORDER BY original_name LIMIT ? OFFSET ?",
                             [*args, limit, offset]).fetchall()
    except sqlite3.OperationalError:
        return 0, []
    return total, [dict(r) for r in rows]


def new_job(names: list[str]) -> str:
    job_id = uuid.uuid4().hex[:12]
    JOBS[job_id] = {"job_id": job_id, "status": "queued", "files": names,
                    "error": None, "index": None, "documents": []}
    return job_id


def run_job(job_id: str, folder: str):
    job = JOBS[job_id]
    job["status"] = "running"
    try:
        wait_for_chroma()
        job["index"] = rag.ingest(folder)            # RagApp serializes concurrent builds
        job["documents"] = list_documents(names=job["files"], limit=500)[1]
        job["status"] = "done"
    except Exception as e:
        job["status"], job["error"] = "failed", str(e)[:300]