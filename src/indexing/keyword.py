import pickle
import re
from rank_bm25 import BM25Okapi


def tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())      # same function for indexing and querying


def build(ids: list[str], texts: list[str], path):
    with open(path, "wb") as f:
        pickle.dump({"ids": ids, "bm25": BM25Okapi([tokenize(t) for t in texts])}, f)


def load(path) -> dict:
    with open(path, "rb") as f:
        return pickle.load(f)


def search(index: dict, query: str, k: int = 5) -> list[str]:
    scores = index["bm25"].get_scores(tokenize(query))
    return [index["ids"][i] for i in scores.argsort()[::-1][:k] if scores[i] > 0]

def search_scored(index: dict, query: str, k: int = 10) -> list[tuple[str, float]]:
    scores = index["bm25"].get_scores(tokenize(query))
    top = scores.argsort()[::-1][:k]
    return [(index["ids"][i], float(scores[i])) for i in top if scores[i] > 0]