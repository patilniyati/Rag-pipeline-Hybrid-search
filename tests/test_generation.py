from src.generation.citations import extract_claims, verify_citations
from src.generation.confidence import composite, retrieval_confidence
from src.generation.settings import GenerationSettings


class FakeLLM:
    def __init__(self, reply):
        self.reply = reply

    def generate(self, prompt, system="", json_mode=False):
        return self.reply


def test_claims_split_and_citations_attach():
    claims = extract_claims("Retries use exponential backoff [1]. Jobs expire after 5 days [2][3].")
    assert claims[0] == {"claim": "Retries use exponential backoff.", "cites": [1]}
    assert claims[1]["cites"] == [2, 3]


def test_stranded_citation_joins_previous_claim():
    claims = extract_claims("Retries use exponential backoff. [1]")
    assert claims[0]["cites"] == [1]


def test_verification_statuses():
    chunks = [{"text": "Retries use exponential backoff.", "source": "a.md",
               "page": -1, "heading": "Retry"}]
    claims = extract_claims("Retries use exponential backoff [1]. Jobs expire after 5 days [3]. "
                            "Nothing here is cited at all.")
    out = verify_citations(claims, chunks, FakeLLM('{"verdict": "supported", "reason": "ok"}'))
    assert [c["status"] for c in out] == ["verified", "unsupported", "uncited"]


def test_retrieval_confidence_separates_good_from_bad():
    good = [{"rerank_score": 4.0}, {"rerank_score": 2.0}]
    bad = [{"rerank_score": -10.0}, {"rerank_score": -11.0}]
    assert retrieval_confidence(good) > 0.8 > 0.1 > retrieval_confidence(bad)


def test_composite_is_a_weighted_average():
    assert composite(1.0, 1.0, 1.0, GenerationSettings()) == 1.0
    assert composite(0.0, 0.0, 0.0, GenerationSettings()) == 0.0

def test_trailing_citation_covers_the_preceding_run():
    claims = extract_claims("First fact here. Second fact here. Third fact here [2].")
    assert [c["cites"] for c in claims] == [[2], [2], [2]]

def test_sentences_after_the_last_citation_stay_uncited():
    claims = extract_claims("First fact here [1]. Second fact here.")
    assert claims[1]["cites"] == []