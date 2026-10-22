import re
import unicodedata
from pathlib import PurePosixPath


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return " ".join(re.findall(r"\w+", text.lower()))     # words only


def has_phrase(phrase: str, text: str) -> bool:
    return f" {norm(phrase)} " in f" {norm(text)} "         # whole words only


def source_matches(chunk_source: str, wanted: str) -> bool:
    a = PurePosixPath(chunk_source.replace("\\", "/")).name
    b = PurePosixPath(wanted.replace("\\", "/")).name
    return a == b


def chunk_matches(chunk: dict, evidence: dict) -> bool:
    if not source_matches(chunk["source"], evidence["source"]):
        return False
    phrase = evidence.get("contains")
    return not phrase or has_phrase(phrase, chunk["text"])