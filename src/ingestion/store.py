import hashlib, json
from dataclasses import asdict
from pathlib import Path

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

def save_raw(path: Path) -> str:
    data = path.read_bytes()
    doc_id = hashlib.sha256(data).hexdigest()[:16]     # fingerprint of the file
    folder = RAW_DIR / doc_id
    if not folder.exists():                            # same file twice = skipped
        folder.mkdir(parents=True)
        (folder / f"original{path.suffix.lower()}").write_bytes(data)
        (folder / "meta.json").write_text(json.dumps({"original_name": path.name}))
    return doc_id

def save_processed(doc_id: str, sections, loader_version: str):
    out = PROCESSED_DIR / doc_id / f"{loader_version}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for s in sections:
            f.write(json.dumps(asdict(s), ensure_ascii=False) + "\n")