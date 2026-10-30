import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RetrievalSettings:
    dense_k: int = 10
    sparse_k: int = 10
    dense_weight: float = 0.7
    sparse_weight: float = 0.3
    rrf_k: int = 60
    rerank_candidates: int = 20
    final_k: int = 5
    min_rerank_score: float = -5.0     # drop chunks the reranker judges irrelevant
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    max_per_source: int = 0       # 0 = no cap; 2 means at most 2 chunks per document


def load_retrieval_settings(path: str = "retrieval_config.json") -> RetrievalSettings:
    s = RetrievalSettings()
    p = Path(path)
    if p.exists():
        for key, value in json.loads(p.read_text()).items():
            if hasattr(s, key):
                setattr(s, key, value)
    return s