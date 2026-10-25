import json
from pathlib import Path

import numpy as np

from . import keyword
from .dedup import find_duplicates
from .embedder import Embedder
from .settings import Settings
from .store import open_store


def load_chunks(folder: Path) -> list[dict]:
    chunks = []
    for f in sorted(folder.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            c = json.loads(line)
            if c["text"].strip():
                chunks.append(c)
    return chunks


def index_chunks(chunks: list[dict], s: Settings, name: str) -> dict:
    root = Path(s.index_root) / name
    root.mkdir(parents=True, exist_ok=True)
    store = open_store(name, s)

    current = {c["chunk_id"] for c in chunks}
    store.delete(store.ids() - current)                     # chunks that no longer exist

    log_path = root / "duplicates.json"
    skipped = json.loads(log_path.read_text()) if log_path.exists() else {}
    skipped = {k: v for k, v in skipped.items() if k in current}

    have = store.ids()
    new = [c for c in chunks if c["chunk_id"] not in have and c["chunk_id"] not in skipped]

    inserted = 0
    if new:
        vecs = np.asarray(Embedder(s).docs([c["text"] for c in new]), dtype=np.float32)
        keep, found = find_duplicates(new, vecs, store.everything(), s.dup_threshold)
        store.add([new[i] for i in keep], vecs[keep])
        skipped.update(found)
        inserted = len(keep)
    log_path.write_text(json.dumps(skipped, indent=2))

    rows = store.everything()                               # BM25 mirrors Chroma exactly
    if rows:
        keyword.build([r["id"] for r in rows], [r["text"] for r in rows], root / "bm25.pkl")

    return {"read": len(chunks), "new": len(new), "inserted": inserted,
            "duplicates": len(new) - inserted, "removed": len(have - current)}


def check_sync(s: Settings, name: str) -> bool:
    root = Path(s.index_root) / name
    chroma_ids = open_store(name, s).ids()
    path = root / "bm25.pkl"
    bm25_ids = set(keyword.load(path)["ids"]) if path.exists() else set()
    print(f"chroma={len(chroma_ids)} bm25={len(bm25_ids)} -> "
          f"{'IN SYNC' if chroma_ids == bm25_ids else 'OUT OF SYNC, run the build again'}")
    return chroma_ids == bm25_ids