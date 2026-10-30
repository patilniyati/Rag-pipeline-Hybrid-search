from src.retrieval.fusion import weighted_rrf
from src.retrieval.diversify import cap_per_source

def test_agreement_beats_a_single_first_place():
    ranked = weighted_rrf({"dense": ["a", "b"], "sparse": ["c", "b"]},
                          {"dense": 1, "sparse": 1})
    assert ranked[0][0] == "b"


def test_weights_decide_who_wins_a_disagreement():
    lists = {"dense": ["a", "b"], "sparse": ["b", "a"]}
    assert weighted_rrf(lists, {"dense": 0.7, "sparse": 0.3})[0][0] == "a"
    assert weighted_rrf(lists, {"dense": 0.3, "sparse": 0.7})[0][0] == "b"

def _r(i, src):
    return {"id": i, "source": src}

def test_cap_frees_slots_for_other_documents():
    rows = [_r(1, "a"), _r(2, "a"), _r(3, "a"), _r(4, "b"), _r(5, "c")]
    out = cap_per_source(rows, 2, 4)
    assert [r["id"] for r in out] == [1, 2, 4, 5]

def test_backfills_when_too_few_documents():
    rows = [_r(1, "a"), _r(2, "a"), _r(3, "a")]
    assert [r["id"] for r in cap_per_source(rows, 1, 3)] == [1, 2, 3]

def test_zero_means_no_cap():
    rows = [_r(1, "a"), _r(2, "a"), _r(3, "a")]
    assert len(cap_per_source(rows, 0, 2)) == 2