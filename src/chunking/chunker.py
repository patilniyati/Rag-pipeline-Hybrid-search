import argparse
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter

PROCESSED_DIR = Path("data/processed")
CHUNKS_DIR = Path("data/chunks")
CHUNK_SIZE = 1500          # characters, roughly 350-400 tokens
CHUNK_OVERLAP = 200
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SEMANTIC_PERCENTILE = 90   # higher = fewer, larger chunks


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    source: str
    text: str                    # what gets indexed (heading prefix + body, if used)
    strategy: str                # "fixed" | "recursive" | "semantic"
    strategy_params: str         # settings used, so experiments are reproducible
    heading_path: list[str] = field(default_factory=list)
    page: int | None = None
    format: str = ""

# ---------- the three strategies: text in, list of pieces out ----------

def fixed_split(text: str) -> list[str]:
    """Baseline: cut every CHUNK_SIZE characters, ignoring meaning."""
    splitter = CharacterTextSplitter(
        separator="", chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    return splitter.split_text(text)


def recursive_split(text: str) -> list[str]:
    """Prefer paragraph breaks, then lines, then sentences, then words."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""])
    return splitter.split_text(text)


_embeddings = None

def _get_embeddings():
    global _embeddings                      # load the model once, only if needed
    if _embeddings is None:
        from langchain_huggingface import HuggingFaceEmbeddings
        _embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    return _embeddings

MIN_SEMANTIC_CHARS = 200

def _merge_tiny(pieces, min_chars):
    out = []
    for p in pieces:
        if out and len(p) < min_chars:      # too small to stand alone
            out[-1] += " " + p
        else:
            out.append(p)
    if len(out) > 1 and len(out[0]) < min_chars:   # tiny first piece joins the next
        out[1] = out[0] + " " + out[1]
        out = out[1:]
    return out

def semantic_split(text: str) -> list[str]:
    """Cut where the topic changes (a jump in embedding distance between sentences)."""
    if len(text) <= CHUNK_SIZE:
        return [text]                       # nothing to split, saves embedding calls
    from langchain_experimental.text_splitter import SemanticChunker
    chunker = SemanticChunker(
        _get_embeddings(),
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=SEMANTIC_PERCENTILE)
    pieces = []
    for p in _merge_tiny(chunker.split_text(text), MIN_SEMANTIC_CHARS):
        pieces.extend(recursive_split(p) if len(p) > CHUNK_SIZE else [p])
    return pieces


# name -> (function, use heading prefix?, params description)
STRATEGIES = {
    "fixed": (fixed_split, False,
              f"size={CHUNK_SIZE},overlap={CHUNK_OVERLAP}"),
    "recursive": (recursive_split, True,
                  f"size={CHUNK_SIZE},overlap={CHUNK_OVERLAP}"),
    "semantic": (semantic_split, True,
                 f"percentile={SEMANTIC_PERCENTILE},model={EMBED_MODEL.split('/')[-1]},cap={CHUNK_SIZE}"),
}

MIN_SECTION_CHARS = CHUNK_SIZE // 5      # scales with chunk size: 300 when CHUNK_SIZE is 1500


def _parent(s):
    return s["heading_path"][:-1]


def _can_merge(group, s):
    first = group["first"]
    # never merge sections with different top-level topics
    safe = bool(_parent(s)) or first["heading_path"] == s["heading_path"]
    return (group["size"] < MIN_SECTION_CHARS
            and first["doc_id"] == s["doc_id"]
            and first["page"] == s["page"]
            and _parent(first) == _parent(s)
            and safe
            and group["size"] + len(s["text"]) <= CHUNK_SIZE)


def merge_small_sections(sections):
    """Merge tiny neighbouring sections that share a parent heading and page."""
    groups = []
    for s in sections:
        if groups and _can_merge(groups[-1], s):
            groups[-1]["items"].append(s)
            groups[-1]["size"] += len(s["text"])
        else:
            groups.append({"items": [s], "first": s, "size": len(s["text"])})

    merged = []
    for g in groups:
        if len(g["items"]) == 1:
            merged.append(g["items"][0])
            continue
        parent = _parent(g["first"])
        parts = []
        for s in g["items"]:
            label = " > ".join(s["heading_path"][len(parent):])   # the leaf heading
            parts.append(f"{label}\n{s['text']}" if label else s["text"])
        merged.append({**g["first"], "heading_path": parent,
                       "text": "\n\n".join(parts)})
    return merged

# ---------- reading sections, writing chunks ----------

def chunk_document(doc_dir: Path, strategy: str) -> list[Chunk]:
    split_fn, use_prefix, params = STRATEGIES[strategy]
    files = list(doc_dir.glob("*.jsonl"))
    if not files:
        return []
    latest = max(files, key=lambda p: p.stat().st_mtime)

    sections = [json.loads(line)
                for line in latest.read_text(encoding="utf-8").splitlines()]
    sections = merge_small_sections(sections)          # the new step

    chunks = []
    for s in sections:
        prefix = " > ".join(s["heading_path"]) if use_prefix else ""
        for piece in split_fn(s["text"]):
            text = f"{prefix}\n{piece}" if prefix else piece
            chunks.append(Chunk(
                chunk_id=f"{s['doc_id']}-{strategy}-{len(chunks)}",
                doc_id=s["doc_id"], source=s["source"], text=text,
                strategy=strategy, strategy_params=params,
                heading_path=s["heading_path"], page=s["page"], format=s["format"],
            ))
    return chunks


def chunk_all(strategy: str):
    out_dir = CHUNKS_DIR / strategy
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n== {strategy} ==")
    for doc_dir in sorted(PROCESSED_DIR.iterdir()):
        if not doc_dir.is_dir():
            continue
        chunks = chunk_document(doc_dir, strategy)
        if not chunks:
            continue
        with (out_dir / f"{doc_dir.name}.jsonl").open("w", encoding="utf-8") as f:
            for c in chunks:
                f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
        sizes = [len(c.text) for c in chunks]
        print(f"{chunks[0].source}: {len(chunks)} chunks, "
              f"min {min(sizes)} / avg {sum(sizes) // len(sizes)} / max {max(sizes)}")
        



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", default="all",
                        choices=[*STRATEGIES, "all"])
    args = parser.parse_args()
    for name in (STRATEGIES if args.strategy == "all" else [args.strategy]):
        chunk_all(name)