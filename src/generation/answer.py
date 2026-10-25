from dataclasses import asdict, dataclass, field, replace

from src.retrieval.retriever import Retriever
from src.retrieval.settings import load_retrieval_settings

from . import confidence as conf
from .citations import extract_claims, verify_citations
from .llm import make_llm
from .prompt import NO_ANSWER, build_prompt
from .settings import load_generation_settings



@dataclass
class Answer:
    status: str                       # "answered" or "insufficient"
    text: str
    confidence: dict
    citations: list = field(default_factory=list)       # one entry per claim, with verdicts
    flags: list = field(default_factory=list)           # claims whose citations failed
    found: list = field(default_factory=list)           # "I don't know": what was retrieved
    not_found: str = ""                                 # "I don't know": what is missing
    suggested_documents: list = field(default_factory=list)
    contexts: list = field(default_factory=list)      # the chunks the model was shown
    

    def to_dict(self) -> dict:
        return asdict(self)


class Answerer:
    def __init__(self, strategy: str, settings=None):
        self.s = settings or load_generation_settings()
        # this layer owns the relevance threshold, so switch the retriever's own cutoff off
        no_cutoff = replace(load_retrieval_settings(), min_rerank_score=-1e9)
        self.retriever = Retriever(strategy, settings=no_cutoff)
        self._llm = None
    
    @property
    def llm(self):                       # created on first use, so /search works without an API key
        if self._llm is None:
            self._llm = make_llm(self.s)
        return self._llm

    def ask(self, question: str, mode: str = "hybrid") -> Answer:
        chunks = self.retriever.search(question, mode=mode)[: self.s.context_chunks]
        r_conf = conf.retrieval_confidence(chunks)
        if not chunks or r_conf < self.s.min_retrieval_confidence:
            return self._insufficient(question, chunks, r_conf)

        system, user = build_prompt(question, chunks)
        raw = self.llm.generate(user, system=system).strip()
        if raw.startswith(NO_ANSWER):
            reason = raw[len(NO_ANSWER):].strip(" -—:.")
            return self._insufficient(question, chunks, r_conf, reason)

        claims = verify_citations(extract_claims(raw), chunks, self.llm,
                                  self.s.judge_delay_s)
        coverage = conf.citation_coverage(claims)
        complete, missing = conf.completeness(question, raw, self.llm)
        return Answer(
            status="answered", text=raw, citations=claims,
            contexts=chunks,
            flags=[c for c in claims if c["status"] != "verified"],
            confidence={"retrieval": r_conf, "citation_coverage": coverage,
                        "completeness": complete, "missing_parts": missing,
                        "composite": conf.composite(r_conf, coverage, complete, self.s)})

    def _insufficient(self, question, chunks, r_conf, reason="") -> Answer:
        found = [{"source": c["source"], "page": c["page"], "heading": c["heading"],
                  "relevance": round(conf.sigmoid(c.get("rerank_score", -10)), 3),
                  "snippet": c["text"][:150]} for c in chunks[:3]]
        sources = list(dict.fromkeys(c["source"] for c in chunks))
        return Answer(
            status="insufficient",
            text="I don't have enough information in the indexed documents to answer this.",
            contexts=chunks,
            confidence={"retrieval": r_conf, "composite": r_conf},
            found=found,
            not_found=reason or f"None of the retrieved passages answer: {question!r}",
            suggested_documents=sources[:5])