import math

from .citations import parse_json

COMPLETENESS_SYSTEM = """You check whether an ANSWER addresses every part of a QUESTION.
Reply with JSON only: {"score": <0.0 to 1.0>, "missing": ["<part of the question not addressed>", ...]}
1.0 = every part is addressed, 0.5 = some parts are missing, 0.0 = the question is not addressed.
An answer that clearly says some part cannot be answered from the documents still counts
as addressing that part."""


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def retrieval_confidence(chunks: list[dict]) -> float:
    """Cross-encoder scores are logits, so a sigmoid maps them to 0-1.
    Weighted toward the best chunk, with the top three as support."""
    scores = [c["rerank_score"] for c in chunks if "rerank_score" in c][:3]
    if not scores:
        return 0.0
    probs = [sigmoid(s) for s in scores]
    return round(0.7 * probs[0] + 0.3 * sum(probs) / len(probs), 3)


def citation_coverage(verified_claims: list[dict]) -> float:
    if not verified_claims:
        return 0.0
    ok = sum(c["status"] == "verified" for c in verified_claims)
    return round(ok / len(verified_claims), 3)


def completeness(question: str, answer: str, llm) -> tuple[float, list[str]]:
    raw = llm.generate(f"QUESTION: {question}\n\nANSWER: {answer}",
                       system=COMPLETENESS_SYSTEM, json_mode=True)
    data = parse_json(raw) or {}
    try:
        score = min(1.0, max(0.0, float(data.get("score", 0.0))))
    except (TypeError, ValueError):
        score = 0.0
    return round(score, 3), list(data.get("missing") or [])


def composite(retrieval: float, coverage: float, complete: float, s) -> float:
    total = s.w_retrieval + s.w_coverage + s.w_completeness
    return round((s.w_retrieval * retrieval + s.w_coverage * coverage
                  + s.w_completeness * complete) / total, 3)