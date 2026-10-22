import json
import re
import time

CITE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")

JUDGE_SYSTEM = """You are a strict fact-checker. You get a CLAIM and a SOURCE passage.
Decide whether the passage supports the claim, judging only from the passage.
Reply with JSON only: {"verdict": "supported" | "partial" | "unsupported", "reason": "<one short sentence>"}
supported = the passage states or directly implies everything in the claim.
partial = it supports only part of the claim.
unsupported = the claim is not in the passage, or the passage contradicts it."""


def _numbers(text: str) -> list[int]:
    return [int(n) for group in CITE.findall(text) for n in re.split(r"\s*,\s*", group)]

def _inherit_trailing_citations(claims: list[dict]) -> list[dict]:
    """A citation after a run of uncited sentences covers that run."""
    pending = []
    for c in claims:
        if c["cites"]:
            for p in pending:
                p["cites"] = list(c["cites"])
                p["inherited"] = True
            pending = []
        else:
            pending.append(c)
    return claims

def extract_claims(answer: str) -> list[dict]:
    """Each sentence becomes {"claim": text without markers, "cites": [block numbers]}."""
    claims = []
    for sent in SENTENCE.split(answer):
        sent = sent.strip().lstrip("-*• ").strip()
        if not sent:
            continue
        nums = _numbers(sent)
        text = re.sub(r"\s+([.,;:!?])", r"\1", CITE.sub("", sent)).strip()
        if len(text.split()) < 3:                  # a citation stranded on its own
            if nums and claims:
                claims[-1]["cites"] = list(dict.fromkeys(claims[-1]["cites"] + nums))
            continue
        claims.append({"claim": text, "cites": list(dict.fromkeys(nums))})
    return _inherit_trailing_citations(claims)


def parse_json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None


def _judge(claim: str, passage: str, llm) -> tuple[str, str]:
    raw = llm.generate(f"CLAIM: {claim}\n\nSOURCE:\n{passage}",
                       system=JUDGE_SYSTEM, json_mode=True)
    data = parse_json(raw)
    verdict = str((data or {}).get("verdict", "")).lower()
    if verdict not in ("supported", "partial", "unsupported"):
        return "unverified", "the judge returned unreadable output"
    return verdict, str(data.get("reason", ""))


def verify_citations(claims: list[dict], chunks: list[dict], llm, delay: float = 0.0):
    """Adds `checks` (one per cited block) and `status` to every claim.
    status: verified | partial | unsupported | uncited."""
    out = []
    for c in claims:
        checks = []
        for n in c["cites"]:
            if not 1 <= n <= len(chunks):          # the model cited a block that doesn't exist
                checks.append({"n": n, "verdict": "invalid", "reason": "no such context block"})
                continue
            chunk = chunks[n - 1]
            verdict, reason = _judge(c["claim"], chunk["text"], llm)
            checks.append({"n": n, "verdict": verdict, "reason": reason,
                           "source": chunk["source"], "page": chunk["page"],
                           "heading": chunk["heading"]})
            if delay:
                time.sleep(delay)
        verdicts = [k["verdict"] for k in checks]
        if not checks:
            status = "uncited"
        elif "supported" in verdicts:
            status = "verified"
        elif "partial" in verdicts:
            status = "partial"
        else:
            status = "unsupported"
        out.append({**c, "checks": checks, "status": status})
    return out