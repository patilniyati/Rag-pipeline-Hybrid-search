from src.evaluation.dataset import validate
from src.evaluation.matching import chunk_matches
from src.evaluation.report import FALSE_REFUSAL, summarize
from src.evaluation.retrieval_metrics import retrieval_scores
from src.evaluation.dataset import normalize_case, validate
from src.evaluation.matching import source_matches


def _c(source, text):
    return {"source": source, "text": text}


def test_matching_ignores_case_spacing_and_fancy_hyphens():
    ev = {"source": "a.md", "contains": "X-Northstar-Key header"}
    assert chunk_matches(_c("a.md", "send the x\u2011northstar\u2011key   Header"), ev)
    assert not chunk_matches(_c("b.md", "x-northstar-key header"), ev)


def test_retrieval_scores_for_multi_hop():
    chunks = [_c("a.md", "alpha fact"), _c("z.md", "noise"), _c("b.md", "beta fact")]
    ev = [{"source": "a.md", "contains": "alpha"}, {"source": "b.md", "contains": "beta"}]
    assert retrieval_scores(chunks, ev) == {"hit": 1.0, "recall": 1.0, "all_found": 1.0, "mrr": 1.0}
    partial = retrieval_scores(chunks[1:], ev)
    assert partial["recall"] == 0.5 and partial["all_found"] == 0.0 and partial["mrr"] == 0.5


def test_multi_hop_needs_two_documents():
    case = {"id": "q1", "type": "multi_hop", "question": "q", "answer": "a",
            "evidence": [{"source": "a.md", "contains": "x"}]}
    assert any("2+" in p for p in validate([case]))


def test_unanswerable_needs_no_evidence():
    case = {"id": "q2", "type": "unanswerable", "question": "q", "answer": "a", "evidence": []}
    assert validate([case]) == []


def test_false_refusals_are_counted():
    rows = [{"type": "lookup", "status": "insufficient"},
            {"type": "lookup", "status": "answered", "correctness": 1.0}]
    assert summarize(rows)[FALSE_REFUSAL] == 0.5


def test_native_format_is_normalized():
    raw = {"id": "q1", "question_type": "factual", "question": "Q?", "expected_answer": "A",
           "answerable": True,
           "source_sections": [{"source": "a.md", "section": "S",
                                "evidence": "one two three four five six seven eight nine ten",
                                "role": "primary"}]}
    case = normalize_case(raw, 1)
    assert case["type"] == "lookup"
    assert case["evidence"][0]["contains"] == "one two three four five six seven eight"
    assert validate([case]) == []


def test_unanswerable_flag_wins_and_keeps_no_evidence():
    raw = {"id": "q2", "question_type": "factual", "question": "Q?", "expected_answer": "",
           "answerable": False, "source_sections": [{"source": "a.md", "evidence": "x"}]}
    case = normalize_case(raw, 2)
    assert case["type"] == "unanswerable" and case["evidence"] == []
    assert validate([case]) == []


def test_source_match_ignores_folder_prefix():
    assert source_matches("a.pdf", "pdf/a.pdf")
    assert source_matches("pdfs/a.pdf", "pdf/a.pdf")
    assert not source_matches("b.pdf", "pdf/a.pdf")