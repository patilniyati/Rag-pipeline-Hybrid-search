import argparse
import subprocess
import time
from pathlib import Path

from src.evaluation.dataset import check_evidence, describe, load_dataset
from src.evaluation.report import build_report
from src.evaluation.runner import run_strategy
from src.evaluation.settings import load_eval_settings
from src.evaluation.dataset import check_evidence, describe, load_dataset, stratified_sample
from src.generation.llm import USAGE, DailyLimitError


def default_label() -> str:
    git = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    return f"{time.strftime('%Y%m%d-%H%M')}-{git or 'nogit'}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--strategies", nargs="+", default=["fixed", "recursive", "semantic"])
    p.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    p.add_argument("--retrieval-only", action="store_true", help="no LLM calls, runs in seconds")
    p.add_argument("--label", help="reuse a label to resume an interrupted run")
    p.add_argument("--limit", type=int, help="first N cases only, for smoke tests")
    p.add_argument("--validate", action="store_true", help="check the golden set and exit")
    p.add_argument("--sample", type=int, help="stratified subset of N cases (same cases every time)")
    p.add_argument("--types", nargs="+", help="only run these question types, e.g. ambiguous lookup")
    a = p.parse_args()

    es = load_eval_settings()
    cases = load_dataset(es.golden_path, None if a.split == "all" else a.split)
    if a.validate:
        print(describe(cases))
        problems = check_evidence(cases)
        print("\n".join(problems) if problems else "evidence phrases all found in the corpus")
        return
    if a.types:
        cases = [c for c in cases if c["type"] in a.types]
    if a.sample:
        cases = stratified_sample(cases, a.sample)
    elif a.limit:
        cases = cases[:a.limit]

    label = a.label or default_label()
    if a.retrieval_only and not label.endswith("-retrieval"):
        label += "-retrieval"
    run_dir = Path(es.runs_dir) / label
    print(f"run: {label} | {describe(cases)}")

    try:
        for strategy in a.strategies:
            run_strategy(strategy, cases, run_dir, a.retrieval_only)
    except DailyLimitError:
        print(f"\nDaily limit hit. Resume later with: --label {run_dir.name}")
    
    print(f"\nLLM usage this run: {USAGE['calls']} calls, {USAGE['tokens']} tokens")
    report = build_report(run_dir, a.strategies, len(cases))
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    print("\n" + report)


if __name__ == "__main__":
    main()