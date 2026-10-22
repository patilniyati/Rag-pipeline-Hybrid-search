import re
import numpy as np

_NUMBERS = re.compile(r"\d+(?:[.,]\d+)*")


def _numbers(text: str) -> set:
    return set(_NUMBERS.findall(text))


def find_duplicates(new: list[dict], vecs: np.ndarray, existing: list[dict],
                    threshold: float):
    """new: dicts with chunk_id, doc_id, text. existing: dicts with id, doc_id, text, vec.
    Returns (indices of `new` to keep, {skipped_chunk_id: {duplicate_of, similarity}})."""
    ref_vecs = np.array([e["vec"] for e in existing]).reshape(-1, vecs.shape[1])
    kept, dups = [], {}

    for i, (chunk, v) in enumerate(zip(new, vecs)):
        candidates = []                                    # (score, id, doc_id, text)
        for j in np.where(ref_vecs @ v > threshold)[0]:
            e = existing[j]
            candidates.append((float(ref_vecs[j] @ v), e["id"], e["doc_id"], e["text"]))
        if kept:                                           # also compare with earlier new chunks
            for j in np.where(vecs[kept] @ v > threshold)[0]:
                k = new[kept[j]]
                candidates.append((float(vecs[kept[j]] @ v), k["chunk_id"],
                                   k["doc_id"], k["text"]))

        for score, ref_id, ref_doc, ref_text in sorted(candidates, reverse=True):
            if ref_doc != chunk["doc_id"] and _numbers(ref_text) == _numbers(chunk["text"]):
                dups[chunk["chunk_id"]] = {"duplicate_of": ref_id,
                                           "similarity": round(score, 4)}
                break
        else:
            kept.append(i)
    return kept, dups