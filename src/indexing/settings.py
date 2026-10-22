import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    model: str = "BAAI/bge-small-en-v1.5"
    # Prefixes are model-specific. Check the model card when you change `model`.
    query_prefix: str = "Represent this sentence for searching relevant passages: "
    doc_prefix: str = ""
    dup_threshold: float = 0.95
    index_root: str = "data/index"


def load_settings(path: str = "index_config.json") -> Settings:
    s = Settings()
    p = Path(path)
    if p.exists():
        for key, value in json.loads(p.read_text()).items():
            if hasattr(s, key):
                setattr(s, key, value)
    return s