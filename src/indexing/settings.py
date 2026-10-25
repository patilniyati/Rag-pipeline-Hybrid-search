import json
import os
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
    chroma_host: str = ""        # empty = on-disk Chroma; set = Chroma server
    chroma_port: int = 8000


def load_settings(path: str = "index_config.json") -> Settings:
    s = Settings()
    p = Path(path)
    if p.exists():
        for key, value in json.loads(p.read_text()).items():
            if hasattr(s, key):
                setattr(s, key, value)
    if os.getenv("CHROMA_HOST"):
        s.chroma_host = os.environ["CHROMA_HOST"]
    if os.getenv("CHROMA_PORT"):
        s.chroma_port = int(os.environ["CHROMA_PORT"])
    return s