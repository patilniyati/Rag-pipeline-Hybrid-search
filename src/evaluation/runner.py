import json
import time
from dataclasses import replace
from pathlib import Path

from src.generation.answer import Answerer
from src.generation.citations import verify_citations
from src.generation.llm import make_llm
from src.generation.settings import load_generation_settings
from src.retrieval.retriever import Retriever
from src.retrieval.settings import load_retrieval_settings
from src.generation.llm import USAGE, DailyLimitError, make_llm

from .judges import judge_correctness, judge_faithfulness
from .retrieval_metrics import retrieval_scores
from .settings import load_eval_settings

KEEP = ("id", "source", "page", "heading", "text")


def _trim(chunks):
    return [{k: c.get(k) for k in KEEP} for c in chunks]


def make_judge(gs, es):
    """Returns (judge llm, is_separate_from_the_generator)."""
    if not (es.judge_provider or es.judge_model):
        return make_llm(gs), False
    s = replace(gs, provider=es.judge_provider or gs.provider,
                model=es.judge_model or gs.model,
                api_key_env=es.judge_api_key_env or gs.api_key_env, temperature=0.0)
    return make_llm(s), True


def citation_scores(citations):
    checks = [k for c in citations for k in c["checks"]]
    precision = None
    if checks:
        points = sum({"supported": 1.0, "partial": 0.5}.get(k["verdict"], 0.0) for k in checks)
        precision = round(points / len(checks), 3)
    coverage = (round(sum(c["status"] == "verified" for c in citations) / len(citations), 3)
                if citations else None)
    return precision, coverage


def _base(case):
    return {"id": case["id"], "type": case["type"], "question": case["question"]}


def retrieval_row(case, retriever):
    ctx = _trim(retriever.search(case["question"]))
    ret = retrieval_scores(ctx, case["evidence"]) if case["evidence"] else None
    return {**_base(case), "contexts": [c["source"] for c in ctx], "retrieval": ret}


def full_row(case, answerer, judge, separate):
    a = answerer.ask(case["question"])
    ctx = _trim(a.contexts)
    answered = a.status == "answered"
    claims = a.citations
    if answered and separate:       # re-check citations with the independent judge
        claims = verify_citations([{"claim": c["claim"], "cites": c["cites"]} for c in a.citations],
                                  ctx, judge)

    if case["type"] == "unanswerable":
        correctness, why = (0.0, "answered an unanswerable question") if answered else (1.0, "correctly refused")
    elif not answered:
        correctness, why = 0.0, "refused an answerable question"
    else:
        correctness, why = judge_correctness(case["question"], a.text, case["answer"], case["type"], judge)

    faith, unsupported = None, []
    if answered and claims:
        rest = [c["claim"] for c in claims if c["status"] != "verified"]
        if not rest:
            faith = 1.0                                   # every claim has a supporting cited block
        else:
            score, unsupported = judge_faithfulness(rest, ctx, judge)
            faith = None if score is None else round(1 - len(unsupported) / len(claims), 3)
            
    precision, coverage = citation_scores(claims) if answered else (None, None)
    return {**_base(case), "status": a.status, "answer": a.text, "contexts": ctx,
            "retrieval": retrieval_scores(ctx, case["evidence"]) if case["evidence"] else None,
            "correctness": correctness, "correctness_reason": why,
            "faithfulness": faith, "unsupported_claims": unsupported,
            "citation_precision": precision, "citation_coverage": coverage,
            "confidence": a.confidence.get("composite")}


def run_strategy(strategy: str, cases: list[dict], run_dir: Path, retrieval_only: bool = False):
    es, gs = load_eval_settings(), load_generation_settings()
    run_dir.mkdir(parents=True, exist_ok=True)
    out = run_dir / f"{strategy}.jsonl"
    done = ({json.loads(l)["id"] for l in out.read_text(encoding="utf-8").splitlines()}
            if out.exists() else set())                       # resume where a failed run stopped
    todo = [c for c in cases if c["id"] not in done]
    if not todo:
        print(f"[{strategy}] already complete")
        return

    if retrieval_only:
        retriever = Retriever(strategy, settings=replace(load_retrieval_settings(),
                                                         min_rerank_score=-1e9))
        make_row = lambda case: retrieval_row(case, retriever)
    else:
        answerer = Answerer(strategy, gs)
        judge, separate = make_judge(gs, es)
        make_row = lambda case: full_row(case, answerer, judge, separate)

    with out.open("a", encoding="utf-8") as f:

        for i, case in enumerate(todo, 1):
            before = USAGE["tokens"]
            try:
                row = make_row(case)
            except DailyLimitError as e:
                print(f"  STOPPED: {e}\n  Finished cases are saved; rerun with the same --label later.")
                raise
            except Exception as e:                            # bad JSON, transient error, etc.
                print(f"  FAILED {case['id']}: {e}")
                continue
            row["tokens"] = USAGE["tokens"] - before          # cost per case, saved with the row
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            print(f"  [{strategy}] {i}/{len(todo)} {case['id']} ({row['tokens']} tokens)")
            if es.case_delay_s and not retrieval_only:
                time.sleep(es.case_delay_s)
        