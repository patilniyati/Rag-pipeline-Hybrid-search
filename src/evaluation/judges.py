from src.generation.citations import parse_json

CORRECTNESS_SYSTEM = """You grade an ANSWER to a QUESTION against a GOLDEN answer written by an expert.
Judge meaning, not wording. Reply with JSON only: {"verdict": "correct" | "partial" | "incorrect", "reason": "<one short sentence>"}
correct = states everything essential in the golden answer and contradicts nothing in it.
partial = states some essential facts but misses others.
incorrect = misses the main point, contradicts the golden answer, or says the information is unavailable."""

AMBIGUOUS_NOTE = """
This question is ambiguous. The golden answer lists the reasonable interpretations.
correct = the answer covers each interpretation, or clearly says the question is ambiguous.
partial = it silently covers only one interpretation."""

FAITHFULNESS_SYSTEM = """You check whether each numbered CLAIM is supported by the CONTEXT passages.
Use only the context, and ignore whether the claim is true in the real world.
Reply with JSON only: {"verdicts": [{"n": 1, "verdict": "supported" | "unsupported"}, ...]} with one entry per claim."""


def judge_correctness(question, answer, golden, qtype, llm):
    system = CORRECTNESS_SYSTEM + (AMBIGUOUS_NOTE if qtype == "ambiguous" else "")
    raw = llm.generate(f"QUESTION: {question}\n\nGOLDEN ANSWER: {golden}\n\nANSWER: {answer}",
                       system=system, json_mode=True)
    data = parse_json(raw) or {}
    score = {"correct": 1.0, "partial": 0.5, "incorrect": 0.0}.get(str(data.get("verdict", "")).lower())
    if score is None:
        return None, "judge returned unreadable output"
    return score, str(data.get("reason", ""))


def judge_faithfulness(claims: list[str], contexts: list[dict], llm):
    """One call for all claims. Returns (share supported, list of unsupported claims)."""
    if not claims:
        return None, []
    context = "\n\n".join(f"[{i}] {c['text']}" for i, c in enumerate(contexts, 1))
    listed = "\n".join(f"{i}. {c}" for i, c in enumerate(claims, 1))
    raw = llm.generate(f"CONTEXT:\n\n{context}\n\nCLAIMS:\n{listed}",
                       system=FAITHFULNESS_SYSTEM, json_mode=True)
    data = parse_json(raw) or {}
    got = {v.get("n"): str(v.get("verdict", "")).lower()
           for v in data.get("verdicts", []) if isinstance(v, dict)}
    results = [got.get(i) for i in range(1, len(claims) + 1)]
    if any(r not in ("supported", "unsupported") for r in results):
        return None, []                                  # unreadable: excluded, not counted as 0
    unsupported = [c for c, r in zip(claims, results) if r == "unsupported"]
    return round(1 - len(unsupported) / len(claims), 3), unsupported