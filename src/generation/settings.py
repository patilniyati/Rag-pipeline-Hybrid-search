import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GenerationSettings:
    provider: str = "gemini"                 # "gemini" or "ollama"
    model: str = "gemini-3.8-flash"          # for ollama e.g. "llama3.1:8b"
    api_key_env: str = "GEMINI_API_KEY"
    ollama_url: str = "http://localhost:11434"
    temperature: float = 0.0
    timeout_s: int = 120
    context_chunks: int = 5                  # chunks placed in the prompt
    min_retrieval_confidence: float = 0.10   # below this, answer "I don't know"
    judge_delay_s: float = 0.0               # raise (e.g. 5) if the free tier rate-limits you
    w_retrieval: float = 0.4
    w_coverage: float = 0.4
    w_completeness: float = 0.2
    reasoning_effort: str = ""        # "low" | "medium" | "high" (gpt-oss models on Groq)


def load_generation_settings(path: str = "generation_config.json") -> GenerationSettings:
    s = GenerationSettings()
    p = Path(path)
    if p.exists():
        for key, value in json.loads(p.read_text()).items():
            if hasattr(s, key):
                setattr(s, key, value)
    return s