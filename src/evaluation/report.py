import json
from pathlib import Path

FALSE_REFUSAL = "False refusals (answerable questions)"
LOWER_BETTER = {FALSE_REFUSAL}


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def summarize(rows: list[dict]) -> dict:
    ret = [r["retrieval"] for r in rows if r.get("retrieval")]
    multi = [r["retrieval"] for r in rows if r["type"] == "multi_hop" and r.get("retrieval")]
    answerable = [r for r in rows if r["type"] in ("lookup", "multi_hop")]
    unanswerable = [r for r in rows if r["type"] == "unanswerable"]
    return {
        "Retrieval hit@8": mean(x["hit"] for x in ret),
        "Retrieval MRR": mean(x["mrr"] for x in ret),
        "Multi-hop: all evidence retrieved": mean(x["all_found"] for x in multi),
        "Answer correctness": mean(r.get("correctness") for r in rows),
        "Faithfulness": mean(r.get("faithfulness") for r in rows),
        "Citation accuracy": mean(r.get("citation_precision") for r in rows),
        "Citation coverage": mean(r.get("citation_coverage") for r in rows),
        "Correct refusals (unanswerable)": mean(r.get("correctness") for r in unanswerable),
        FALSE_REFUSAL: mean((r["status"] == "insufficient") if r.get("status") else None
                            for r in answerable),
    }


def _fmt(v):
    return "n/a" if v is None else f"{v:.2f}"


def _marked(values: dict, lower_better=False) -> list[str]:
    nums = [round(v, 2) for v in values.values() if v is not None]
    best = (min if lower_better else max)(nums) if nums else None
    return [f"**{_fmt(v)}**" if v is not None and len(nums) > 1 and round(v, 2) == best else _fmt(v)
            for v in values.values()]


def _table(header, body):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return "\n".join(lines + ["| " + " | ".join(r) + " |" for r in body])


def _primary(r):
    if r.get("correctness") is not None:
        return r["correctness"]
    return r["retrieval"]["hit"] if r.get("retrieval") else None


def build_report(run_dir: Path, strategies: list[str], expected: int) -> str:
    rows = {}
    for s in strategies:
        p = Path(run_dir) / f"{s}.jsonl"
        rows[s] = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []
    sums = {s: summarize(r) for s, r in rows.items()}

    out = [f"# Chunking strategy comparison ({Path(run_dir).name})", "",
           "Bold = best in row. n/a = not measured in this run.", "",
           "## Overall", ""]
    body = [["Cases scored"] + [f"{len(rows[s])}/{expected}" for s in strategies]]
    for metric in sums[strategies[0]]:
        vals = {s: sums[s][metric] for s in strategies}
        body.append([metric] + _marked(vals, metric in LOWER_BETTER))
    out.append(_table(["Metric"] + strategies, body))

    types = sorted({r["type"] for rs in rows.values() for r in rs})
    out += ["", "## By question type (correctness, or retrieval hit@5 in a retrieval-only run)", ""]
    body = []
    for t in types:
        vals = {s: mean(_primary(r) for r in rows[s] if r["type"] == t) for s in strategies}
        body.append([t] + _marked(vals))
    out.append(_table(["Type"] + strategies, body))

    if all(rows.values()):
        by = {s: {r["id"]: r for r in rs} for s, rs in rows.items()}
        shared = set.intersection(*[set(b) for b in by.values()])
        diff = []
        for i in sorted(shared):
            vals = {s: _primary(by[s][i]) for s in strategies}
            if None not in vals.values() and len(set(vals.values())) > 1:
                diff.append(f"- {i}: " + ", ".join(f"{s} {v:.1f}" for s, v in vals.items()))
        out += ["", "## Cases where strategies disagree (read these first)", ""] + (diff or ["- none"])

    out += ["", "Each case moves a metric by about 1/n, so gaps of one or two cases are noise."]
    return "\n".join(out)