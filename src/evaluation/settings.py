import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EvalSettings:
    golden_path: str = "eval/golden.json"
    runs_dir: str = "eval/runs"
    # Optional separate judge. Empty = reuse the generation model.
    judge_provider: str = ""
    judge_model: str = ""
    judge_api_key_env: str = ""
    case_delay_s: float = 0.0       # pause between cases if the free tier rate-limits you


def load_eval_settings(path: str = "eval_config.json") -> EvalSettings:
    s = EvalSettings()
    p = Path(path)
    if p.exists():
        for key, value in json.loads(p.read_text()).items():
            if hasattr(s, key):
                setattr(s, key, value)
    return s