def cap_per_source(rows: list[dict], max_per_source: int, top_n: int) -> list[dict]:
    """rows: best first. Keep at most `max_per_source` chunks per document, up to top_n.
    If that leaves fewer than top_n, backfill with the skipped chunks, best first."""
    if max_per_source <= 0:
        return rows[:top_n]
    kept, skipped, count = [], [], {}
    for r in rows:
        n = count.get(r["source"], 0)
        if n < max_per_source:
            kept.append(r)
            count[r["source"]] = n + 1
        else:
            skipped.append(r)
        if len(kept) == top_n:
            return kept
    return kept + skipped[: top_n - len(kept)]