from src.retrieval.fusion import weighted_rrf


def test_agreement_beats_a_single_first_place():
    ranked = weighted_rrf({"dense": ["a", "b"], "sparse": ["c", "b"]},
                          {"dense": 1, "sparse": 1})
    assert ranked[0][0] == "b"


def test_weights_decide_who_wins_a_disagreement():
    lists = {"dense": ["a", "b"], "sparse": ["b", "a"]}
    assert weighted_rrf(lists, {"dense": 0.7, "sparse": 0.3})[0][0] == "a"
    assert weighted_rrf(lists, {"dense": 0.3, "sparse": 0.7})[0][0] == "b"