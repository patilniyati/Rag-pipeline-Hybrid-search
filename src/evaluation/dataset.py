import hashlib
import json
from collections import Counter
from pathlib import Path
from .matching import has_phrase, norm, source_matches


TYPES = ("lookup", "multi_hop", "unanswerable", "ambiguous")
MAX_WORDS = 8          # evidence is cut to its first words so it can't straddle two chunks
TEST_SHARE = 4         # out of 10 cases go to the test split when no split is given
SCORED_ROLES = {"supporting", "primary", ""}     # any other role is context, not a quote

# Spellings of question_type that map to each internal type. Add your own here.
ALIASES = {
    "lookup": ["lookup", "factual", "single_hop", "simple", "direct", "fact_lookup"],
    "multi_hop": ["multi_hop", "multihop", "multi", "cross_document", "multi_document"],
    "unanswerable": ["unanswerable", "no_answer", "not_answerable", "out_of_scope", "negative"],
    "ambiguous": ["ambiguous", "underspecified", "unclear", "needs_clarification"],
}
TYPE_OF = {alias: t for t, names in ALIASES.items() for alias in names}
NO_ANSWER_TEXT = "The documents do not contain this information."


def _key(value) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _phrase(text) -> str:
    if isinstance(text, list):
        text = " ".join(str(t) for t in text)
    return " ".join(str(text or "").split()[:MAX_WORDS])


def _default_split(case_id: str) -> str:
    # stable: depends only on the id, so adding cases never moves existing ones
    h = int(hashlib.md5(case_id.encode()).hexdigest(), 16)
    return "test" if h % 10 < TEST_SHARE else "dev"


def normalize_case(raw: dict, index: int) -> dict:
    """Turn one line of your golden file into the form the framework uses."""
    cid = raw.get("id") or f"q{index:03d}"
    qtype = TYPE_OF.get(_key(raw.get("question_type")))
    if raw.get("answerable") is False and qtype in (None, "lookup", "multi_hop"):
        qtype = "unanswerable"

    evidence, related = [], []
    for s in raw.get("source_sections") or []:
        if not s.get("source"):
            continue
        item = {"source": s["source"], "contains": _phrase(s.get("evidence")),
                "role": s.get("role"), "section": s.get("section")}
        scored = qtype not in ("unanswerable", "ambiguous") and _key(s.get("role")) in SCORED_ROLES
        (evidence if scored else related).append(item)

    answer = raw.get("expected_answer") or ""
    if qtype == "unanswerable" and not answer:
        answer = NO_ANSWER_TEXT
    if qtype == "ambiguous" and raw.get("expected_behavior"):
        answer = f"{answer}\nExpected behavior: {raw['expected_behavior']}".strip()

    return {"id": cid, "type": qtype, "_raw_type": raw.get("question_type"),
            "split": raw.get("split") or _default_split(cid),
            "question": raw.get("question", ""), "answer": answer,
            "evidence": evidence, "related": related,
            "rationale": raw.get("rationale"), "tags": raw.get("tags")}


def validate(cases: list[dict]) -> list[str]:
    problems, seen = [], set()
    for c in cases:
        cid = c.get("id", "?")
        if cid in seen:
            problems.append(f"{cid}: duplicate id")
        seen.add(cid)
        if c.get("type") not in TYPES:
            raw = c.get("_raw_type")
            problems.append(f"{cid}: unknown question_type {raw!r}; add it to ALIASES in dataset.py")
        if not c.get("question") or not c.get("answer"):
            problems.append(f"{cid}: needs a question and an expected_answer")
        ev = c.get("evidence", [])
        if c.get("type") in ("lookup", "multi_hop") and not ev:
            problems.append(f"{cid}: needs source_sections with evidence")
        if c.get("type") == "multi_hop" and len({e.get("source") for e in ev}) < 2:
            problems.append(f"{cid}: multi_hop needs sources from 2+ documents")
    return problems


def load_dataset(path: str, split: str | None = None) -> list[dict]:
    text = Path(path).read_text(encoding="utf-8")
    if path.endswith(".jsonl"):
        raw = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        raw = json.loads(text)
    cases = [normalize_case(r, i) for i, r in enumerate(raw, 1)]
    problems = validate(cases)
    if problems:
        raise ValueError("Golden set problems:\n" + "\n".join(problems))
    return [c for c in cases if split is None or c["split"] == split]


def _corpus_text(processed_dir: str = "data/processed") -> dict[str, str]:
    text = {}
    for d in Path(processed_dir).iterdir():
        files = list(d.glob("*.jsonl")) if d.is_dir() else []
        if not files:
            continue
        latest = max(files, key=lambda p: p.stat().st_mtime)
        for line in latest.read_text(encoding="utf-8").splitlines():
            s = json.loads(line)
            text[s["source"]] = text.get(s["source"], "") + " " + s["text"]
    return {k: norm(v) for k, v in text.items()}


def check_evidence(cases: list[dict]) -> list[str]:
    """Every evidence phrase must really exist in the named document."""
    corpus = _corpus_text()
    problems = []
    for c in cases:
        for e in c.get("evidence", []):
            hits = [t for src, t in corpus.items() if source_matches(src, e["source"])]
            if not hits:
                problems.append(f"{c['id']}: no document named {e['source']!r}")
            elif not e.get("contains"):
                problems.append(f"{c['id']}: empty evidence for {e['source']} "
                                f"(it would match any chunk of that file)")
            elif not any(has_phrase(e["contains"], t) for t in hits):
                problems.append(f"{c['id']}: phrase not found in {e['source']}: {e['contains']!r}")
    return problems


def describe(cases: list[dict]) -> str:
    by_type = Counter(c["type"] for c in cases)
    by_split = Counter(c["split"] for c in cases)
    return f"{len(cases)} cases | types {dict(by_type)} | splits {dict(by_split)}"

def stratified_sample(cases: list[dict], n: int) -> list[dict]:
    """About n cases, in proportion to each type. Deterministic."""
    import random
    by_type: dict[str, list[dict]] = {}
    for c in cases:
        by_type.setdefault(c["type"], []).append(c)
    rng, picked = random.Random(7), []
    for t in sorted(by_type):
        group = sorted(by_type[t], key=lambda c: c["id"])
        k = max(1, round(n * len(group) / len(cases)))
        picked += rng.sample(group, min(k, len(group)))
    return sorted(picked, key=lambda c: c["id"])