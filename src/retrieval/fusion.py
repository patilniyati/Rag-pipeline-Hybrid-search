def weighted_rrf(rankings: dict[str, list[str]], weights: dict[str, float],
                 k: int = 60) -> list[tuple[str, float]]:
    """rankings: {"dense": [ids best first], "sparse": [...]}.
    Each list adds weight / (k + rank) to every chunk it contains."""
    scores: dict[str, float] = {}
    for name, ids in rankings.items():
        w = weights.get(name, 1.0)
        for rank, chunk_id in enumerate(ids, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + w / (k + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)