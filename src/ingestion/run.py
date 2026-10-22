import json,sys

from dataclasses import asdict
from pathlib import Path

from .loaders import load_txt, load_md, load_html, load_pdf
from .normalisation import normalise
from .store import RAW_DIR, save_raw, save_processed
from .manifest import record


LOADERS = {".txt": load_txt, ".md": load_md, ".html": load_html, ".pdf": load_pdf}     # we'll add .md, .html, .pdf here later
LOADER_VERSION = "v1"        # bump to "v2" after you improve a loader

def process(raw_file: Path, doc_id: str, source: str):
    loader = LOADERS.get(raw_file.suffix.lower())
    if loader is None:
        print(f"SKIP  {source} (no loader)")
        return
    try:
        sections = loader(raw_file)
        for s in sections:
            s.text = normalise(s.text)
            s.source = source            # original filename, not "original.pdf"
            s.doc_id = doc_id
        sections = [s for s in sections if s.text]
        save_processed(doc_id, sections, LOADER_VERSION)
        chars = sum(len(s.text) for s in sections)
        record(doc_id, source, raw_file.suffix.lstrip("."), len(sections),
               chars, LOADER_VERSION, "ok")
        print(f"OK    {source}: {len(sections)} sections, {chars} chars")
    except Exception as e:
        record(doc_id, source, raw_file.suffix.lstrip("."), 0, 0,
               LOADER_VERSION, "failed", str(e))
        print(f"FAIL  {source}: {e}")

def add(folder: str):
    for path in sorted(Path(folder).iterdir()):
        if path.name.startswith(".") or path.is_dir():
            continue
        doc_id = save_raw(path)
        process(RAW_DIR / doc_id / f"original{path.suffix.lower()}", doc_id, path.name)

def reindex():
    for d in sorted(RAW_DIR.iterdir()):
        raw_file = next(d.glob("original.*"))
        source = json.loads((d / "meta.json").read_text())["original_name"]
        process(raw_file, d.name, source)

if __name__ == "__main__":
    if sys.argv[1] == "reindex":
        reindex()
    else:
        add(sys.argv[1])