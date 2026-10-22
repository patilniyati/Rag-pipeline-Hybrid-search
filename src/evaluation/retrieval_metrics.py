from .matching import chunk_matches


def retrieval_scores(chunks: list[dict], evidence: list[dict]) -> dict:
    """chunks: retrieved, best first. Each evidence item is covered if some chunk matches it."""
    ranks = [next((i for i, c in enumerate(chunks, 1) if chunk_matches(c, ev)), None)
             for ev in evidence]
    found = [r for r in ranks if r]
    return {"hit": float(bool(found)),                  # any evidence retrieved
            "recall": len(found) / len(ranks),          # share of evidence items retrieved
            "all_found": float(len(found) == len(ranks)),
            "mrr": 1.0 / min(found) if found else 0.0}  # rank of the first relevant chunk